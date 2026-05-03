---
name: run-job-search
description: Master orchestrator that runs the full job search pipeline end-to-end in order: fetch → deduplicate → match → sort → notify. Invoke this skill to run a complete job search session.
---

## Goal

Run all five job search skills in sequence and report a final summary. This is the primary entry point for a full job search session.

## Pre-flight Checks

Before running any skill, verify the following. If any check fails, stop immediately and tell the user what is missing — do not proceed.

**Required context files:**
- `context/resume.md`
- `context/matchCriteria.md`
- `context/searchTerms.md`
- `context/trello_cards.csv`

**Required environment variables (in `.env`):**
- `AGENTMAIL_API_KEY`
- `AGENTMAIL_SENDER`

If all checks pass, print:
```
Pre-flight checks passed. Starting pipeline...
```

## Pipeline

Run each skill in this exact order, waiting for each to complete before starting the next. After each skill completes, record the key numbers from its output (see "Tracking Numbers"), then print a progress line before moving on.

1. **`/fetch-jobs`** — Fetch raw listings from all MCP job search servers
2. **`/archive-duplicates`** — Archive already-applied and duplicate listings
3. **`/match-jobs`** — Score listings against resume and match criteria
4. **`/sort-by-location`** — Copy matches to country-specific folders
5. **`/notify-email`** — Send email summary to wasabi.buff@gmail.com

**Progress line format** (print after each step completes):
```
✓ Step {N}/5 — {skill-name} complete  ({one-line summary of key result})
```

Examples:
- `✓ Step 1/5 — fetch-jobs complete  (23 new listings fetched)`
- `✓ Step 2/5 — archive-duplicates complete  (5 archived: 2 already-applied, 3 duplicate)`
- `✓ Step 3/5 — match-jobs complete  (11 matched, 7 low-match archived)`
- `✓ Step 4/5 — sort-by-location complete  (8 CA, 3 US)`
- `✓ Step 5/5 — notify-email complete  (email sent)`

## Tracking Numbers

After each skill's report, extract and store these values for the final summary:

| Variable | Where to find it |
|---|---|
| `fetched_new` | fetch-jobs report: "Total new files written" |
| `archived_applied` | archive-duplicates report: count of already-applied |
| `archived_duplicate` | archive-duplicates report: count of duplicate |
| `archived_low_match` | match-jobs report: count of low-match archived |
| `matched_ca` | sort-by-location report: count copied to `jobMatches-Can/` |
| `matched_us` | sort-by-location report: count copied to `jobMatches-US/` |

If a number cannot be extracted from a sub-skill's output, record it as `?`.

## Error Handling

### Hard failure (skill crashed or threw an error)

Stop the pipeline immediately. Report which step failed and what the error was, then offer the user three options:

```
Step {N}/5 — {skill-name} failed: {error summary}

How would you like to proceed?
  [R] Retry this step
  [S] Skip this step and continue the pipeline
  [A] Abort the pipeline
```

Wait for the user's choice before doing anything.

### Soft failure (skill ran but produced no useful output)

- **fetch-jobs writes 0 new files AND `jobListings-Raw/` is empty:** Stop the pipeline. Tell the user: "No new listings were fetched and no existing listings are queued. Aborting." Do not continue to subsequent steps.
- **fetch-jobs writes 0 new files but `jobListings-Raw/` has existing files:** Continue — there are still listings to process from a previous run.
- **Any other step produces 0 output** (e.g., all listings archived, 0 matches): Continue the pipeline and note it in the final summary.

### Email step

Always invoke `/notify-email` as the final step, even when 0 listings matched. The skill handles the empty case itself by sending a "0 matches" email. Do not suppress the call.

## Final Summary

After all skills complete, print:

```
=== Job Search Complete — {YYYY-MM-DD} ===

Fetched:            {fetched_new} new listings
Archived:
  Already applied:  {archived_applied}
  Duplicate:        {archived_duplicate}
  Low match:        {archived_low_match}
Matched:
  Canada:           {matched_ca}
  United States:    {matched_us}

Email sent to wasabi.buff@gmail.com.
```
