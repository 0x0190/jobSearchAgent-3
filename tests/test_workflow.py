from __future__ import annotations

import io
import json
import urllib.error
from datetime import date
from pathlib import Path

import pytest

from job_search_agent.listings import (
    ListingDocument,
    atomic_write_listing,
    collision_safe_move,
    read_listing,
    slugify,
)
from job_search_agent.workflow import (
    WorkflowError,
    archive_duplicates,
    ingest,
    notify,
    preflight,
    render_notification,
    set_match,
    sort_matches,
    token_overlap,
)


def make_root(tmp_path: Path) -> Path:
    for directory in (
        "context",
        ".codex",
        "jobListings-Raw",
        "jobListings-Archived",
        "jobMatches-Can",
        "jobMatches-US",
    ):
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    (tmp_path / "context" / "resume.md").write_text("Embedded engineer\n", encoding="utf-8")
    (tmp_path / "context" / "matchCriteria.md").write_text("Score rules\n", encoding="utf-8")
    (tmp_path / "context" / "searchTerms.md").write_text("# terms\nstaff engineer\n", encoding="utf-8")
    (tmp_path / "context" / "trello_cards.csv").write_text(
        "Date,Company,Position\n", encoding="utf-8"
    )
    (tmp_path / ".codex" / "config.toml").write_text(
        "[mcp_servers.Dice]\nurl='https://dice.test'\n"
        "[mcp_servers.LinkedIn]\ncommand='uvx'\n",
        encoding="utf-8",
    )
    return tmp_path


def metadata(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "date_fetched": "2026-06-28",
        "site": "dice",
        "company": "Acme Corp",
        "title": "Senior Embedded Software Engineer",
        "location": "Toronto, ON",
        "location_type": "hybrid",
        "country": "CA",
        "url": "https://example.test/jobs/1",
        "salary": "$150,000",
        "sponsorship": "not required",
        "security_clearance": "none",
        "match_score": None,
        "match_rationale": None,
        "archived_reason": None,
    }
    values.update(overrides)
    return values


def write_listing(path: Path, **overrides: object) -> Path:
    atomic_write_listing(
        path,
        ListingDocument(metadata(**overrides), "# Role\n\nA description with --- inside.\n"),
    )
    return path


def test_frontmatter_round_trip_preserves_types_and_body(tmp_path: Path) -> None:
    path = tmp_path / "listing.md"
    write_listing(path, match_score=8, match_rationale="C++: strong overlap")

    document = read_listing(path)

    assert document.metadata["date_fetched"] == "2026-06-28"
    assert document.metadata["match_score"] == 8
    assert document.metadata["match_rationale"] == "C++: strong overlap"
    assert "A description with --- inside." in document.body


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Acme Corp & Partners", "acme-corp-partners"),
        ("Senior Embedded S/W Engineer (C++)", "senior-embedded-sw-engineer-c"),
        ("  Déjà  Vu  ", "deja-vu"),
    ],
)
def test_slugify(value: str, expected: str) -> None:
    assert slugify(value) == expected


def test_ingest_normalizes_and_skips_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    payload = {
        "site": "Dice",
        "company": "Acme Corp & Partners",
        "title": "Senior Embedded Engineer",
        "location": "Toronto",
        "location_type": "Hybrid",
        "country": "CA",
        "url": "https://example.test/1",
        "description": "Build safe software.",
    }
    input_path = root / "input.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr("job_search_agent.workflow.date", type("D", (), {"today": staticmethod(lambda: date(2026, 6, 28))}))

    first = ingest(root, str(input_path))
    second = ingest(root, str(input_path))

    assert first["written_count"] == 1
    assert first["written"] == ["2026-06-28-dice-acme-corp-partners-senior-embedded-engineer.md"]
    assert second["skipped_count"] == 1


def test_ingest_rejects_unsafe_date(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    payload = {
        "date_fetched": "../../escape",
        "site": "dice",
        "company": "Acme",
        "title": "Senior Engineer",
        "location": "Toronto",
        "location_type": "hybrid",
        "country": "ca",
        "url": "https://example.test/1",
    }
    input_path = root / "input.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="date_fetched"):
        ingest(root, str(input_path))

    assert not list((root / "jobListings-Raw").glob("*.md"))


def test_token_overlap_uses_whole_tokens() -> None:
    assert token_overlap("General Motors LLC", "General Motors")
    assert not token_overlap("AMD", "TAMD")


def test_archive_duplicates_applies_all_precedence_rules(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    raw = root / "jobListings-Raw"
    archive = root / "jobListings-Archived"
    write_listing(raw / "a.md", url="https://same.test", company="Alpha", title="Principal Embedded Engineer")
    write_listing(raw / "b.md", url="https://same.test", company="Beta", title="Principal Embedded Engineer")
    write_listing(raw / "c.md", url="https://applied.test", company="General Motors LLC", title="Senior Functional Safety Systems Engineer")
    write_listing(raw / "d.md", url="https://old.test", company="Old", title="Senior Embedded Software Engineer")
    write_listing(archive / "d.md", url="https://older.test", company="Old", title="Senior Embedded Software Engineer")
    (root / "context" / "trello_cards.csv").write_text(
        "Date,Company,Position\n2026-01-01,General Motors,Senior Functional Safety Systems Engineer\n",
        encoding="utf-8",
    )

    result = archive_duplicates(root)

    assert result["duplicate_count"] == 2
    assert result["already_applied_count"] == 1
    assert [path.name for path in raw.glob("*.md")] == ["a.md"]
    assert read_listing(archive / "b.md").metadata["archived_reason"] == "duplicate"
    assert read_listing(archive / "c.md").metadata["archived_reason"] == "already-applied"
    assert (archive / "d-2.md").exists()


def test_archive_dry_run_does_not_mutate(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    raw = root / "jobListings-Raw"
    write_listing(raw / "a.md", url="https://same.test")
    write_listing(raw / "b.md", url="https://same.test")

    result = archive_duplicates(root, dry_run=True)

    assert result["duplicate_count"] == 1
    assert sorted(path.name for path in raw.glob("*.md")) == ["a.md", "b.md"]


def test_collision_safe_move_preserves_both_files(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "destination"
    source_dir.mkdir()
    destination_dir.mkdir()
    (source_dir / "same.md").write_text("new", encoding="utf-8")
    (destination_dir / "same.md").write_text("old", encoding="utf-8")

    destination = collision_safe_move(source_dir / "same.md", destination_dir)

    assert destination.name == "same-2.md"
    assert (destination_dir / "same.md").read_text(encoding="utf-8") == "old"
    assert destination.read_text(encoding="utf-8") == "new"


def test_set_match_persists_score_and_archives_low_match(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    path = write_listing(root / "jobListings-Raw" / "role.md")

    result = set_match(root, path.name, score=5, rationale="Domain mismatch")

    archived = root / result["location"]
    assert result["archived_reason"] == "low-match"
    assert read_listing(archived).metadata["match_score"] == 5
    assert not path.exists()


@pytest.mark.parametrize("reason", ["no-sponsorship", "clearance-required", "us-person-required"])
def test_set_match_supports_hard_exclusions(tmp_path: Path, reason: str) -> None:
    root = make_root(tmp_path)
    path = write_listing(root / "jobListings-Raw" / "role.md", country="US")

    result = set_match(root, path.name, score=None, rationale="Not eligible", archive_reason=reason)

    assert result["archived_reason"] == reason
    assert read_listing(root / result["location"]).metadata["match_score"] is None


def test_sort_matches_rebuilds_outputs_and_routes_country(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_listing(root / "jobMatches-Can" / "stale.md", match_score=9)
    write_listing(root / "jobListings-Raw" / "ca.md", match_score=8, country="CA")
    write_listing(root / "jobListings-Raw" / "us.md", match_score=7, country="US", url="https://us.test")
    write_listing(root / "jobListings-Raw" / "low.md", match_score=4, url="https://low.test")

    result = sort_matches(root)

    assert result["canada"] == ["ca.md"]
    assert result["us"] == ["us.md"]
    assert not (root / "jobMatches-Can" / "stale.md").exists()
    assert (root / "jobListings-Raw" / "ca.md").exists()


def test_render_notification_sorts_and_escapes_html(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_listing(
        root / "jobMatches-Can" / "second.md",
        company="A & B",
        title="Second <Lead>",
        match_score=7,
        match_rationale="Good & useful",
        url='https://example.test/?x="bad"',
    )
    write_listing(
        root / "jobMatches-Can" / "first.md",
        company="Top",
        title="First",
        match_score=9,
        url="https://top.test",
    )

    message = render_notification(root, today=date(2026, 6, 28))

    assert message["text"].index("First — Top") < message["text"].index("Second <Lead> — A & B")
    assert "Second &lt;Lead&gt; — A &amp; B" in message["html"]
    assert '&quot;bad&quot;' in message["html"]
    assert "<Lead>" not in message["html"]


def test_empty_notification(tmp_path: Path) -> None:
    root = make_root(tmp_path)

    message = render_notification(root, today=date(2026, 6, 28))

    assert message["subject"].endswith("(0 matches)")
    assert message["total"] == 0


class FakeResponse:
    status = 200

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"message_id":"m1","thread_id":"t1"}'


def test_notify_sends_to_encoded_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    (root / ".env").write_text(
        "AGENTMAIL_API_KEY=secret\n"
        "AGENTMAIL_INBOX_ID=sender@agentmail.to\n"
        "NOTIFY_MAIL_DESTINATION=recipient@example.com\n",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = notify(root)

    assert result["message_id"] == "m1"
    assert "sender%40agentmail.to" in captured["request"].full_url  # type: ignore[union-attr]
    assert captured["timeout"] == 30


def test_notify_reports_http_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    (root / ".env").write_text(
        "AGENTMAIL_API_KEY=secret\n"
        "AGENTMAIL_INBOX_ID=sender\n"
        "NOTIFY_MAIL_DESTINATION=recipient@example.com\n",
        encoding="utf-8",
    )

    def fail(*args: object, **kwargs: object) -> object:
        raise urllib.error.HTTPError(
            "https://example.test", 403, "forbidden", {}, io.BytesIO(b"rejected")
        )

    monkeypatch.setattr("urllib.request.urlopen", fail)

    with pytest.raises(WorkflowError, match="HTTP 403: rejected"):
        notify(root)


def test_preflight_reports_missing_and_accepts_complete_setup(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    with pytest.raises(WorkflowError, match="AGENTMAIL_API_KEY"):
        preflight(root)

    (root / ".env").write_text(
        "AGENTMAIL_API_KEY=secret\n"
        "AGENTMAIL_INBOX_ID=sender\n"
        "NOTIFY_MAIL_DESTINATION=recipient@example.com\n",
        encoding="utf-8",
    )
    assert preflight(root)["status"] == "ok"


def test_fixture_dry_pipeline(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    payload = {
        "date_fetched": "2026-06-28",
        "site": "dice",
        "company": "Fixture Corp",
        "title": "Senior Embedded Engineer",
        "location": "Toronto",
        "location_type": "remote",
        "country": "CA",
        "url": "https://fixture.test/job",
        "description": "Embedded systems role",
    }
    input_path = root / "fixture.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    ingested = ingest(root, str(input_path))
    archive_duplicates(root)
    set_match(root, ingested["written"][0], score=8, rationale="Strong embedded overlap")
    sorted_result = sort_matches(root)
    notification = notify(root, dry_run=True)

    assert sorted_result["canada_count"] == 1
    assert notification["total"] == 1
    assert notification["dry_run"] is True
