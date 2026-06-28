---
name: archive-duplicates
description: "Archive already-applied and duplicate Markdown listings from jobListings-Raw using context/trello_cards.csv, within-run URL and company-title matches, and previous archived filenames. Use when the user asks to deduplicate fetched jobs or run the archive stage."
---

# Archive duplicates

1. Confirm `context/trello_cards.csv` exists and has `Date,Company,Position` headers.
2. Run `uv run job-search-agent archive-duplicates --json`.
3. Report every archived listing, separating already-applied jobs from duplicates and preserving each duplicate match reason.
4. Report pre-archived files left untouched and the number remaining in `jobListings-Raw/`.

Use `--dry-run` when the user asks for an audit or preview. The CLI owns token-overlap matching, deterministic keeper selection, frontmatter updates, and collision-safe moves.
