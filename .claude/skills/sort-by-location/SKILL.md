---
name: sort-by-location
description: Copy matched job listings from jobListings-Raw/ into jobMatches-Can/ (country=CA) or jobMatches-US/ (country=US) based on the country field in each file's YAML frontmatter. Files are copied, not moved — jobListings-Raw/ remains the canonical record.
---

## Goal

Distribute matched listings (those with `match_score >= 6` still in `jobListings-Raw/`) into the appropriate country folder. Copy rather than move so `jobListings-Raw/` stays complete.

## Steps

1. For each `.md` file in `jobListings-Raw/` that has a `match_score` value set (not empty):

   a. Parse the `country` field from YAML frontmatter.

   b. If `country: CA` → copy to `jobMatches-Can/`

   c. If `country: US` → copy to `jobMatches-US/`

   d. If `country` is `other` or unrecognized → log a warning and skip (do not copy).

   e. If a file with the same name already exists in the destination folder, overwrite it (the Raw copy is always the freshest version).

2. Report:
   - Files copied to `jobMatches-Can/`
   - Files copied to `jobMatches-US/`
   - Files skipped (unknown country)
