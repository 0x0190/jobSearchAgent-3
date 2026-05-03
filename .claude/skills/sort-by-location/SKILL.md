---
name: sort-by-location
description: Copy matched job listings from jobListings-Raw/ into jobMatches-Can/ (country=CA) or jobMatches-US/ (country=US) based on the country field in each file's YAML frontmatter. Files are copied, not moved — jobListings-Raw/ remains the canonical record. Run this after /match-jobs and before /notify-email.
---

## Goal

Distribute matched listings into the appropriate country folder so the email notifier can find them. Only copy listings with `match_score >= 6` — anything lower should already be archived, but filter defensively. Copy rather than move so `jobListings-Raw/` stays complete and idempotent.

## Steps

1. Ensure `jobMatches-Can/`, `jobMatches-US/`, and `jobListings-Archived/` exist (create if missing).

2. Move any existing `.md` files in `jobMatches-Can/` and `jobMatches-US/` to `jobListings-Archived/` with `archived_reason: stale-match` in their YAML frontmatter. This ensures the output reflects only the current run.

3. For each `.md` file in `jobListings-Raw/`:

   a. Parse `match_score` and `country` from YAML frontmatter.

   b. Skip if `match_score` is missing, empty, or less than 6.

   c. If `country: CA` → copy to `jobMatches-Can/`

   d. If `country: US` → copy to `jobMatches-US/`

   e. If `country` is `other` or unrecognized → log a warning and skip.

4. Report:
   - Files copied to `jobMatches-Can/` — list each filename and its match score
   - Files copied to `jobMatches-US/` — list each filename and its match score
   - Files skipped (low score or unknown country) — count only
