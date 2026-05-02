---
name: archive-duplicates
description: Check all files in jobListings-Raw/ against context/trello_cards.csv (already-applied jobs), against other files in jobListings-Raw/ (within-run duplicates), and against jobListings-Archived/ (previous-run duplicates). Move any matches to jobListings-Archived/ with an archived_reason in the YAML frontmatter.
---

## Goal

Remove from `jobListings-Raw/` any listing that the candidate has already applied to, is a duplicate of another listing in the same run, or has been seen in a previous run. Move those files to `jobListings-Archived/` and record why.

## Pre-flight

- If `jobListings-Archived/` does not exist, create it.
- Skip any `.md` file in `jobListings-Raw/` whose `archived_reason` frontmatter field is already set to a non-empty value — it has already been processed by an earlier step. Count it as "skipped (pre-archived)" in the final summary and do not move or modify it.

## Step 1 — Load the already-applied set

Read `context/trello_cards.csv`. It has columns: `Date`, `Company`, `Position`.

For each row, apply this validity filter to the `Position` value before adding it to the lookup set:

- Skip any row where `Position` starts with `http` (it is a URL, not a job title).
- Skip any row where `Position` has 30 characters or fewer after trimming whitespace (it is boilerplate or a greeting, not a real title).

Build a list of valid `{Company, Position}` pairs. Keep all valid rows (including apparent duplicates).

## Step 2 — Build a within-run duplicate index

Scan all `.md` files in `jobListings-Raw/` that have not been skipped in the pre-flight step. Build two maps:

**URL map:** `url → [list of filenames sharing that url]`
**Company+title map:** `"{company} | {title}"` (normalized to lowercase, whitespace trimmed) → `[list of filenames]`

For each group that contains more than one file:
- Designate the **alphabetically-first filename** as the keeper.
- For all other files in that group, set `archived_reason: duplicate` in their YAML frontmatter and move them to `jobListings-Archived/`.
- In the summary, tag each as `[within-run url match]` or `[within-run company+title match]` depending on which map flagged it.
- If a file is flagged by both maps, one move and one tag is sufficient.

Do not process these duplicates further in Steps 3–4.

## Step 3 — Already-applied check

For each remaining `.md` file in `jobListings-Raw/`, parse the YAML frontmatter to extract `company` and `title`.

Check against every valid row from Step 1. A match requires **both** of the following to be true at the same time:

- **Company match:** CSV `Company` and file `company` pass the token-overlap test below.
- **Position match:** CSV `Position` and file `title` pass the token-overlap test below.

**Token-overlap test:**
1. Lowercase both strings and split on whitespace and punctuation into tokens.
2. Discard any token that is 2 characters or fewer.
3. A match is TRUE if 50% or more of the shorter string's tokens appear in the longer string's token set.

*Why this rule:* pure substring matching creates false positives ("AMD" inside "TAMD"), but token overlap handles common real-world variations like "General Motors" vs "General motors" and company names with suffixes like ", LLC" or "Inc."

If matched: set `archived_reason: already-applied` in the YAML frontmatter, move the file to `jobListings-Archived/`, continue to the next file.

## Step 4 — Previous-run duplicate check

For each remaining `.md` file in `jobListings-Raw/`, check whether a file with the **same filename** already exists in `jobListings-Archived/`.

If it does:
- Set `archived_reason: duplicate` in the YAML frontmatter.
- Move the file to `jobListings-Archived/`, overwriting the older archived copy.
- Tag as `[previous-run filename match]` in the summary.
- Continue to the next file.

## Step 5 — Report

Print a structured summary:

```
=== archive-duplicates — {YYYY-MM-DD} ===

Files checked:           {n}
Skipped (pre-archived):  {n}

Archived — already-applied ({n}):
  - {company} | {title}
  ...

Archived — duplicate ({n}):
  - {filename}  [{match reason}]
  ...

Remaining in jobListings-Raw/: {n}
```

List every archived file so the user can audit the decisions. If nothing was archived in a category, omit that category's block.
