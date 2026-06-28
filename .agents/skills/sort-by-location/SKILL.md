---
name: sort-by-location
description: "Rebuild jobMatches-Can and jobMatches-US from scored canonical listings in jobListings-Raw, routing eligible scores by country. Use after matching or when the user asks to refresh country-specific match folders."
---

# Sort matches by location

1. Run `uv run job-search-agent sort-matches --json`.
2. Report the stale generated files removed, Canadian listings copied, US listings copied, and skipped listings.

Use `--dry-run` for a preview. The CLI removes stale generated `.md` copies instead of archiving them, keeps `jobListings-Raw/` unchanged, copies only scores of 6 or higher, and skips unknown countries.
