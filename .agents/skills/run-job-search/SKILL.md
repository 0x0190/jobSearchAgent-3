---
name: run-job-search
description: "Run the complete repository job-search pipeline in order: fetch, deduplicate, match, sort by location, and send the AgentMail summary. Use only when the user explicitly invokes the full end-to-end search."
---

# Run the full job search

Invocation of this skill authorizes the pipeline's filesystem changes, MCP searches, and one final summary email.

## Preflight

Run `uv run job-search-agent preflight --json` before any mutation. Stop if it reports missing context, MCP configuration, or email variables.

## Pipeline

Read and follow these sibling skills in order, waiting for each stage to finish:

1. `../fetch-jobs/SKILL.md`
2. `../archive-duplicates/SKILL.md`
3. `../match-jobs/SKILL.md`
4. `../sort-by-location/SKILL.md`
5. `../notify-email/SKILL.md`

Capture each CLI command's JSON summary and print a one-line progress result after every completed stage. The stages are idempotent: ingestion skips existing filenames, archiving processes only active raw files, match decisions overwrite their own frontmatter, sorting rebuilds generated folders, and notification sends only once at the end of this invocation.

If fetching produces no new files but raw files remain, continue. If fetching produces no new files and no raw files remain, stop before matching and email unless the user explicitly requests a zero-match email.

On a stage failure, stop immediately. Report the failed stage, error, completed stages, and exact skill or CLI command needed to resume. Do not skip a failed stage automatically.

## Final report

Report new files fetched, already-applied and duplicate archives, hard exclusions and low matches, Canadian and US match counts, and the email message identifier.
