from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from dotenv import dotenv_values

from .listings import (
    ListingDocument,
    ListingError,
    atomic_copy,
    atomic_write_listing,
    collision_safe_move,
    read_listing,
    score_from,
    slugify,
    validate_listing,
)


class WorkflowError(RuntimeError):
    """Raised when a workflow command cannot complete safely."""


def _directories(root: Path) -> dict[str, Path]:
    return {
        "raw": root / "jobListings-Raw",
        "archived": root / "jobListings-Archived",
        "canada": root / "jobMatches-Can",
        "us": root / "jobMatches-US",
    }


def _environment(root: Path) -> dict[str, str]:
    values = {key: value or "" for key, value in dotenv_values(root / ".env").items()}
    for key in ("AGENTMAIL_API_KEY", "AGENTMAIL_INBOX_ID", "NOTIFY_MAIL_DESTINATION"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def preflight(root: Path) -> dict[str, Any]:
    required_files = [
        root / "context" / "resume.md",
        root / "context" / "matchCriteria.md",
        root / "context" / "searchTerms.md",
        root / "context" / "trello_cards.csv",
        root / ".codex" / "config.toml",
    ]
    missing_files = [str(path.relative_to(root)) for path in required_files if not path.is_file()]

    config_path = root / ".codex" / "config.toml"
    if config_path.is_file():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            missing_files.append(f".codex/config.toml (invalid TOML: {exc})")
        else:
            servers = config.get("mcp_servers", {})
            missing_servers = [name for name in ("Dice", "LinkedIn") if name not in servers]
            if missing_servers:
                missing_files.append(
                    ".codex/config.toml (missing MCP servers: " + ", ".join(missing_servers) + ")"
                )

    terms_path = root / "context" / "searchTerms.md"
    if terms_path.is_file():
        terms = [
            line.strip()
            for line in terms_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not terms:
            missing_files.append("context/searchTerms.md (no search terms)")

    csv_path = root / "context" / "trello_cards.csv"
    if csv_path.is_file():
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            headers = set(next(csv.reader(handle), []))
        if not {"Date", "Company", "Position"}.issubset(headers):
            missing_files.append("context/trello_cards.csv (expected Date,Company,Position headers)")

    environment = _environment(root)
    missing_environment = [
        key
        for key in ("AGENTMAIL_API_KEY", "AGENTMAIL_INBOX_ID", "NOTIFY_MAIL_DESTINATION")
        if not environment.get(key)
    ]
    if missing_files or missing_environment:
        details = []
        if missing_files:
            details.append("missing or invalid files: " + ", ".join(missing_files))
        if missing_environment:
            details.append("missing environment variables: " + ", ".join(missing_environment))
        raise WorkflowError("; ".join(details))

    return {"status": "ok", "files_checked": len(required_files), "environment_checked": 3}


def _load_json_input(source: str) -> Any:
    try:
        if source == "-":
            return json.load(sys.stdin)
        with Path(source).open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot load ingest input {source}: {exc}") from exc


def ingest(root: Path, source: str) -> dict[str, Any]:
    payload = _load_json_input(source)
    records = payload if isinstance(payload, list) else [payload]
    if not records or not all(isinstance(record, dict) for record in records):
        raise WorkflowError("ingest input must be a JSON object or non-empty array of objects")

    raw_directory = _directories(root)["raw"]
    raw_directory.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []

    for record in records:
        metadata = {
            "date_fetched": str(record.get("date_fetched") or date.today().isoformat()),
            "site": str(record.get("site") or "").strip().lower(),
            "company": str(record.get("company") or "").strip(),
            "title": str(record.get("title") or "").strip(),
            "location": str(record.get("location") or "").strip(),
            "location_type": str(record.get("location_type") or "unknown").strip().lower(),
            "country": (
                str(record.get("country") or "other").strip().upper()
                if str(record.get("country") or "other").strip().upper() in {"CA", "US"}
                else "other"
            ),
            "url": str(record.get("url") or "").strip(),
            "salary": str(record.get("salary") or "not listed").strip(),
            "sponsorship": str(record.get("sponsorship") or "not listed").strip(),
            "security_clearance": str(record.get("security_clearance") or "not listed").strip(),
            "match_score": None,
            "match_rationale": None,
            "archived_reason": None,
        }
        validate_listing(metadata)
        company_slug = slugify(metadata["company"])
        title_slug = slugify(metadata["title"])
        site_slug = slugify(metadata["site"])
        if not all((company_slug, title_slug, site_slug)):
            raise WorkflowError("site, company, and title must produce non-empty filename slugs")
        filename = f"{metadata['date_fetched']}-{site_slug}-{company_slug}-{title_slug}.md"
        destination = raw_directory / filename
        if destination.exists():
            skipped.append(filename)
            continue

        description = str(
            record.get("description") or record.get("job_description") or record.get("body") or ""
        ).strip()
        body = f"# {metadata['title']} — {metadata['company']}\n\n{description}\n"
        atomic_write_listing(destination, ListingDocument(metadata, body))
        written.append(filename)

    return {
        "received": len(records),
        "written": written,
        "written_count": len(written),
        "skipped": skipped,
        "skipped_count": len(skipped),
    }


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def token_overlap(left: str, right: str) -> bool:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return False
    shorter, longer = (
        (left_tokens, right_tokens)
        if len(left_tokens) <= len(right_tokens)
        else (right_tokens, left_tokens)
    )
    return len(shorter & longer) / len(shorter) >= 0.5


def _applied_jobs(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        raise WorkflowError(f"missing already-applied tracker: {path}")
    jobs: list[tuple[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not {"Date", "Company", "Position"}.issubset(reader.fieldnames or []):
            raise WorkflowError("trello_cards.csv must contain Date, Company, and Position columns")
        for row in reader:
            position = (row.get("Position") or "").strip()
            company = (row.get("Company") or "").strip()
            if position.lower().startswith("http") or len(position) <= 30:
                continue
            jobs.append((company, position))
    return jobs


def _archive_file(path: Path, archive_directory: Path, reason: str, dry_run: bool) -> str:
    if dry_run:
        return path.name
    document = read_listing(path)
    document.metadata["archived_reason"] = reason
    atomic_write_listing(path, document)
    return collision_safe_move(path, archive_directory).name


def archive_duplicates(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    directories = _directories(root)
    raw_directory = directories["raw"]
    archive_directory = directories["archived"]
    if not raw_directory.exists():
        raise WorkflowError(f"missing raw listings directory: {raw_directory}")
    if not dry_run:
        archive_directory.mkdir(parents=True, exist_ok=True)

    documents: dict[Path, ListingDocument] = {}
    prearchived: list[str] = []
    for path in sorted(raw_directory.glob("*.md")):
        document = read_listing(path)
        validate_listing(document.metadata)
        if document.metadata.get("archived_reason") not in (None, ""):
            prearchived.append(path.name)
        else:
            documents[path] = document

    duplicate_reasons: dict[Path, str] = {}
    url_groups: dict[str, list[Path]] = defaultdict(list)
    identity_groups: dict[str, list[Path]] = defaultdict(list)
    for path, document in documents.items():
        url = str(document.metadata.get("url") or "").strip()
        if url:
            url_groups[url].append(path)
        identity = " | ".join(
            re.sub(r"\s+", " ", str(document.metadata.get(field) or "").strip().lower())
            for field in ("company", "title")
        )
        identity_groups[identity].append(path)

    for groups, reason in (
        (url_groups, "within-run url match"),
        (identity_groups, "within-run company+title match"),
    ):
        for group in groups.values():
            if len(group) > 1:
                for duplicate in sorted(group)[1:]:
                    duplicate_reasons.setdefault(duplicate, reason)

    duplicate_results: list[dict[str, str]] = []
    for path in sorted(duplicate_reasons):
        moved_name = _archive_file(path, archive_directory, "duplicate", dry_run)
        duplicate_results.append(
            {"file": moved_name, "match_reason": duplicate_reasons[path]}
        )

    survivors = [path for path in sorted(documents) if path not in duplicate_reasons]
    applied_jobs = _applied_jobs(root / "context" / "trello_cards.csv")
    already_applied: list[dict[str, str]] = []
    previous_run: list[dict[str, str]] = []

    for path in survivors:
        document = documents[path]
        company = str(document.metadata.get("company") or "")
        title = str(document.metadata.get("title") or "")
        is_applied = any(
            token_overlap(company, applied_company) and token_overlap(title, applied_title)
            for applied_company, applied_title in applied_jobs
        )
        if is_applied:
            moved_name = _archive_file(path, archive_directory, "already-applied", dry_run)
            already_applied.append({"file": moved_name, "company": company, "title": title})
            continue
        if (archive_directory / path.name).exists():
            moved_name = _archive_file(path, archive_directory, "duplicate", dry_run)
            previous_run.append({"file": moved_name, "match_reason": "previous-run filename match"})

    remaining = (
        len(list(raw_directory.glob("*.md")))
        if not dry_run
        else len(prearchived)
        + len(documents)
        - len(duplicate_results)
        - len(already_applied)
        - len(previous_run)
    )
    return {
        "dry_run": dry_run,
        "files_checked": len(documents) + len(prearchived),
        "prearchived": prearchived,
        "already_applied": already_applied,
        "duplicates": duplicate_results + previous_run,
        "already_applied_count": len(already_applied),
        "duplicate_count": len(duplicate_results) + len(previous_run),
        "remaining": remaining,
    }


def _resolve_raw_listing(root: Path, value: str) -> Path:
    raw = _directories(root)["raw"].resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        direct = (root / candidate).resolve()
        candidate = direct if direct.exists() else (raw / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.parent != raw or not candidate.is_file():
        raise WorkflowError(f"listing must be an existing .md file in {raw}: {value}")
    return candidate


def set_match(
    root: Path,
    filename: str,
    *,
    score: int | None,
    rationale: str,
    archive_reason: str | None = None,
) -> dict[str, Any]:
    if score is None and not archive_reason:
        raise WorkflowError("--score is required unless --archive-reason is provided")
    if score is not None and not 0 <= score <= 10:
        raise WorkflowError("score must be between 0 and 10")
    if not rationale.strip():
        raise WorkflowError("rationale must not be empty")

    path = _resolve_raw_listing(root, filename)
    document = read_listing(path)
    validate_listing(document.metadata)
    document.metadata["match_score"] = score
    document.metadata["match_rationale"] = rationale.strip()
    effective_reason = archive_reason or ("low-match" if score is not None and score < 6 else None)
    document.metadata["archived_reason"] = effective_reason
    atomic_write_listing(path, document)

    destination = path
    if effective_reason:
        destination = collision_safe_move(path, _directories(root)["archived"])
    return {
        "file": destination.name,
        "score": score,
        "archived_reason": effective_reason,
        "location": str(destination.relative_to(root)),
    }


def sort_matches(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    directories = _directories(root)
    removed: list[str] = []
    for output_directory in (directories["canada"], directories["us"]):
        if not dry_run:
            output_directory.mkdir(parents=True, exist_ok=True)
        for path in sorted(output_directory.glob("*.md")):
            removed.append(str(path.relative_to(root)))
            if not dry_run:
                path.unlink()

    copied_ca: list[str] = []
    copied_us: list[str] = []
    skipped: list[str] = []
    for path in sorted(directories["raw"].glob("*.md")):
        document = read_listing(path)
        score = score_from(document.metadata)
        if document.metadata.get("archived_reason") not in (None, "") or score is None or score < 6:
            skipped.append(path.name)
            continue
        country = document.metadata.get("country")
        if country == "CA":
            destination = directories["canada"] / path.name
            copied_ca.append(path.name)
        elif country == "US":
            destination = directories["us"] / path.name
            copied_us.append(path.name)
        else:
            skipped.append(path.name)
            continue
        if not dry_run:
            atomic_copy(path, destination)

    return {
        "dry_run": dry_run,
        "removed": removed,
        "canada": copied_ca,
        "us": copied_us,
        "canada_count": len(copied_ca),
        "us_count": len(copied_us),
        "skipped": skipped,
        "skipped_count": len(skipped),
    }


def _load_matches(paths: Iterable[Path]) -> list[dict[str, Any]]:
    listings = []
    for path in paths:
        document = read_listing(path)
        validate_listing(document.metadata, require_match=True)
        listings.append(document.metadata)
    return sorted(
        listings,
        key=lambda item: (-int(item["match_score"]), str(item.get("title") or "").lower()),
    )


def render_notification(root: Path, *, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    directories = _directories(root)
    canada = _load_matches(sorted(directories["canada"].glob("*.md")))
    united_states = _load_matches(sorted(directories["us"].glob("*.md")))
    total = len(canada) + len(united_states)
    subject = f"Job Search Results — {today.isoformat()} ({total} matches)"
    if total == 0:
        text = "No job listings matched today's criteria."
        html_body = "<p>No job listings matched today&#x27;s criteria.</p>"
        return {
            "subject": subject,
            "text": text,
            "html": html_body,
            "canada_count": 0,
            "us_count": 0,
            "total": 0,
        }

    text_sections: list[str] = []
    html_sections: list[str] = []
    for heading, listings in (("Canadian Matches", canada), ("US Matches", united_states)):
        text_lines = [f"== {heading} ({len(listings)} jobs) ==", ""]
        html_items = []
        for index, item in enumerate(listings, start=1):
            text_lines.extend(
                [
                    f"{index}. {item['title']} — {item['company']}",
                    f"   Score: {item['match_score']}/10 | Location: {item['location']} ({item['location_type']})",
                    f"   Salary: {item['salary']} | Sponsorship: {item['sponsorship']} | Clearance: {item['security_clearance']}",
                    f"   {item['url']}",
                    "",
                    f"   {item['match_rationale']}",
                    "",
                ]
            )
            escaped = {key: html.escape(str(value or ""), quote=True) for key, value in item.items()}
            html_items.append(
                "<li>"
                f"<strong>{escaped['title']} — {escaped['company']}</strong><br>"
                f"Score: {escaped['match_score']}/10 | Location: {escaped['location']} ({escaped['location_type']})<br>"
                f"Salary: {escaped['salary']} | Sponsorship: {escaped['sponsorship']} | Clearance: {escaped['security_clearance']}<br>"
                f"<a href=\"{escaped['url']}\">{escaped['url']}</a><br>"
                f"<em>{escaped['match_rationale']}</em>"
                "</li>"
            )
        text_sections.append("\n".join(text_lines).rstrip())
        html_sections.append(f"<h2>{heading} ({len(listings)} jobs)</h2><ol>{''.join(html_items)}</ol>")

    footer = f"Generated by JobSearchAgent on {today.isoformat()}."
    return {
        "subject": subject,
        "text": "\n\n".join(text_sections) + f"\n\n---\n{footer}",
        "html": "".join(html_sections) + f"<hr><small>{footer}</small>",
        "canada_count": len(canada),
        "us_count": len(united_states),
        "total": total,
    }


def notify(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    message = render_notification(root)
    if dry_run:
        return {"dry_run": True, **message}

    environment = _environment(root)
    missing = [
        key
        for key in ("AGENTMAIL_API_KEY", "AGENTMAIL_INBOX_ID", "NOTIFY_MAIL_DESTINATION")
        if not environment.get(key)
    ]
    if missing:
        raise WorkflowError("missing environment variables: " + ", ".join(missing))

    inbox_id = urllib.parse.quote(environment["AGENTMAIL_INBOX_ID"], safe="")
    url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/messages/send"
    payload = json.dumps(
        {
            "to": [environment["NOTIFY_MAIL_DESTINATION"]],
            "subject": message["subject"],
            "text": message["text"],
            "html": message["html"],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {environment['AGENTMAIL_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise WorkflowError(f"AgentMail returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise WorkflowError(f"AgentMail request failed: {exc.reason}") from exc
    try:
        response_payload = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError:
        response_payload = {"raw_response": response_body}
    return {
        "dry_run": False,
        "status": status,
        "message_id": response_payload.get("message_id"),
        "thread_id": response_payload.get("thread_id"),
        "canada_count": message["canada_count"],
        "us_count": message["us_count"],
        "total": message["total"],
    }
