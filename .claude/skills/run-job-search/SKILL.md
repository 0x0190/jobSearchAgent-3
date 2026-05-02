---
name: run-job-search
description: Master orchestrator that runs the full job search pipeline end-to-end in order: fetch → deduplicate → match → sort → notify. Invoke this skill to run a complete job search session.
---

## Goal

Run all five job search skills in sequence and report a final summary. This is the primary entry point for a full job search session.

## Pipeline

Run each skill in this exact order, waiting for each to complete before starting the next:

1. **`/fetch-jobs`** — Fetch raw listings from all MCP job search servers
2. **`/archive-duplicates`** — Archive already-applied and duplicate listings
3. **`/match-jobs`** — Score listings against resume and match criteria
4. **`/sort-by-location`** — Copy matches to country-specific folders
5. **`/notify-email`** — Send email summary to wasabi.buff@gmail.com

## Final Summary

After all skills complete, report:

```
=== Job Search Complete — {YYYY-MM-DD} ===

Fetched:          {n} new listings
Archived:
  Already applied: {n}
  Duplicate:       {n}
  Low match:       {n}
Matched:
  Canada:          {n}
  United States:   {n}

Email sent to wasabi.buff@gmail.com.
```

## Error Handling

If any skill fails or reports zero results at the fetch step, pause and notify the user before continuing. Do not send a notification email if no matches were found.
