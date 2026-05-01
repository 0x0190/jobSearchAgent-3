---
name: archive-duplicates
description: Check all files in jobListings-Raw/ against context/trello_cards.csv (already-applied jobs) and against jobListings-Archived/ (previously seen listings). Move duplicates and already-applied listings to jobListings-Archived/ with an archived_reason in the YAML frontmatter.
---

## Goal

Remove from `jobListings-Raw/` any listing that the candidate has already applied to or that has been seen in a previous run. Move those files to `jobListings-Archived/` and record why.

## Steps

1. Read `context/trello_cards.csv`. It has columns: `Date`, `Company`, `Position`. Build a lookup set of `{company} | {position}` pairs (case-insensitive).

2. For each `.md` file in `jobListings-Raw/`:

   a. Parse the YAML frontmatter to extract `company` and `title`.

   b. **Already-applied check**: Check if a `trello_cards.csv` entry exists where the CSV `Company` fuzzy-matches the file's `company` AND the CSV `Position` fuzzy-matches the file's `title`. Use case-insensitive substring matching — a match occurs if either value contains the other. If matched:
      - Set `archived_reason: already-applied` in the file's YAML frontmatter.
      - Move the file to `jobListings-Archived/`.
      - Continue to next file.

   c. **Previous-run duplicate check**: Check if a file with the same name already exists in `jobListings-Archived/`. If so:
      - Set `archived_reason: duplicate` in the file's YAML frontmatter.
      - Move the file to `jobListings-Archived/` (overwrite the archived copy with the newer one).
      - Continue to next file.

3. After processing all files, report:
   - Total files checked
   - Files archived as `already-applied`
   - Files archived as `duplicate`
   - Files remaining in `jobListings-Raw/`
