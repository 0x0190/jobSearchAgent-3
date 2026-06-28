from __future__ import annotations

import os
import re
import shutil
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import yaml


class ListingError(ValueError):
    """Raised when a job-listing document is malformed."""


class _NoDatesSafeLoader(yaml.SafeLoader):
    pass


_NoDatesSafeLoader.yaml_implicit_resolvers = {
    key: list(value) for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
for first_character, resolvers in list(_NoDatesSafeLoader.yaml_implicit_resolvers.items()):
    _NoDatesSafeLoader.yaml_implicit_resolvers[first_character] = [
        resolver for resolver in resolvers if resolver[0] != "tag:yaml.org,2002:timestamp"
    ]


@dataclass(slots=True)
class ListingDocument:
    metadata: dict[str, Any]
    body: str


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = re.sub(r"\s+", "-", normalized.lower())
    normalized = re.sub(r"[^a-z0-9-]", "", normalized)
    return re.sub(r"-+", "-", normalized).strip("-")


def read_listing(path: Path) -> ListingDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ListingError(f"cannot read {path}: {exc}") from exc

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ListingError(f"{path} does not start with YAML frontmatter")

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        raise ListingError(f"{path} has unterminated YAML frontmatter")

    try:
        metadata = yaml.load("".join(lines[1:closing_index]), Loader=_NoDatesSafeLoader) or {}
    except yaml.YAMLError as exc:
        raise ListingError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(metadata, dict):
        raise ListingError(f"frontmatter in {path} must be a mapping")

    return ListingDocument(dict(metadata), "".join(lines[closing_index + 1 :]).lstrip("\n"))


def validate_listing(metadata: Mapping[str, Any], *, require_match: bool = False) -> None:
    required = (
        "date_fetched",
        "site",
        "company",
        "title",
        "location",
        "location_type",
        "country",
        "url",
        "salary",
        "sponsorship",
        "security_clearance",
    )
    missing = [key for key in required if not str(metadata.get(key) or "").strip()]
    if missing:
        raise ListingError(f"listing is missing required fields: {', '.join(missing)}")

    fetched = str(metadata["date_fetched"])
    try:
        parsed_date = date.fromisoformat(fetched)
    except ValueError as exc:
        raise ListingError("date_fetched must use YYYY-MM-DD format") from exc
    if parsed_date.isoformat() != fetched:
        raise ListingError("date_fetched must use YYYY-MM-DD format")

    if metadata.get("country") not in {"CA", "US", "other"}:
        raise ListingError("country must be CA, US, or other")
    if metadata.get("location_type") not in {"remote", "hybrid", "on-site", "unknown"}:
        raise ListingError("location_type must be remote, hybrid, on-site, or unknown")
    if require_match:
        try:
            score = int(metadata.get("match_score"))
        except (TypeError, ValueError) as exc:
            raise ListingError("match_score must be an integer") from exc
        if not 0 <= score <= 10:
            raise ListingError("match_score must be between 0 and 10")


def atomic_write_listing(path: Path, document: ListingDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.safe_dump(
        document.metadata,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip()
    body = document.body.rstrip() + "\n" if document.body else ""
    payload = f"---\n{frontmatter}\n---\n\n{body}"

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", dir=destination.parent, prefix=f".{destination.name}.", delete=False
        ) as temporary:
            temporary_name = temporary.name
            with source.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def collision_safe_move(source: Path, destination_directory: Path) -> Path:
    destination_directory.mkdir(parents=True, exist_ok=True)
    destination = destination_directory / source.name
    if destination.exists():
        if source.read_bytes() == destination.read_bytes():
            source.unlink()
            return destination
        suffix = source.suffix
        stem = source.stem
        counter = 2
        while destination.exists():
            destination = destination_directory / f"{stem}-{counter}{suffix}"
            counter += 1
    return Path(shutil.move(str(source), str(destination)))


def score_from(metadata: Mapping[str, Any]) -> int | None:
    value = metadata.get("match_score")
    if value in (None, ""):
        return None
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return score if 0 <= score <= 10 else None
