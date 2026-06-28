from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from .listings import ListingError
from .workflow import (
    WorkflowError,
    archive_duplicates,
    ingest,
    notify,
    preflight,
    set_match,
    sort_matches,
)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="job-search-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight_parser = subparsers.add_parser("preflight", help="validate pipeline inputs")
    _add_common(preflight_parser)

    ingest_parser = subparsers.add_parser("ingest", help="write normalized fetched listings")
    _add_common(ingest_parser)
    ingest_parser.add_argument("--input", required=True, help="JSON file, or - for stdin")

    archive_parser = subparsers.add_parser("archive-duplicates", help="archive duplicate listings")
    _add_common(archive_parser)
    archive_parser.add_argument("--dry-run", action="store_true")

    match_parser = subparsers.add_parser("set-match", help="record a semantic match decision")
    _add_common(match_parser)
    match_parser.add_argument("file", help="raw listing filename or repository-relative path")
    match_parser.add_argument("--score", type=int)
    match_parser.add_argument("--rationale", required=True)
    match_parser.add_argument("--archive-reason")

    sort_parser = subparsers.add_parser("sort-matches", help="rebuild country match folders")
    _add_common(sort_parser)
    sort_parser.add_argument("--dry-run", action="store_true")

    notify_parser = subparsers.add_parser("notify", help="render or send the match email")
    _add_common(notify_parser)
    notify_parser.add_argument("--dry-run", action="store_true")
    return parser


def _humanize(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            label = key.replace("_", " ").capitalize()
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{label}:")
                lines.extend(_humanize(item, indent + 2))
            else:
                lines.append(f"{prefix}{label}: {item}")
        return lines
    if isinstance(value, list):
        return [f"{prefix}- {item}" for item in value] or [f"{prefix}(none)"]
    return [f"{prefix}{value}"]


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    actions: dict[str, Callable[[], dict[str, Any]]] = {
        "preflight": lambda: preflight(root),
        "ingest": lambda: ingest(root, args.input),
        "archive-duplicates": lambda: archive_duplicates(root, dry_run=args.dry_run),
        "set-match": lambda: set_match(
            root,
            args.file,
            score=args.score,
            rationale=args.rationale,
            archive_reason=args.archive_reason,
        ),
        "sort-matches": lambda: sort_matches(root, dry_run=args.dry_run),
        "notify": lambda: notify(root, dry_run=args.dry_run),
    }
    return actions[args.command]()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = _dispatch(args)
    except (ListingError, WorkflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n".join(_humanize(result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
