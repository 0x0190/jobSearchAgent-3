---
name: fetch-jobs
description: "Fetch job listings from the repository's configured Dice and LinkedIn MCP servers, normalize the results, and ingest new Markdown records into jobListings-Raw. Use when the user asks to search for or refresh job listings without running the entire pipeline."
---

# Fetch jobs

1. Read `context/searchTerms.md`. Ignore blank lines and Markdown comments. Stop with an actionable error if no terms remain.
2. Confirm the Dice and LinkedIn MCP search tools are available. Report an unavailable source, but continue with any source that works.
3. For each search term, query every available source for up to 15 recent results. Fetch full job details when a result lacks enough description to assess sponsorship, clearance, or suitability.
4. Continue after individual source or query failures and retain an error for the final report.
5. Normalize each result to a JSON object with:
   - `site`, `company`, `title`, `location`, `url`, and the full `description`
   - `location_type`: `remote`, `hybrid`, `on-site`, or `unknown`
   - `country`: `CA`, `US`, or `other`
   - `salary`: the stated range or `not listed`
   - `sponsorship`: `provided`, `not provided`, `not required`, or `not listed`
   - `security_clearance`: `required`, `preferred`, `none`, or `not listed`
6. Pass the normalized JSON array to `uv run job-search-agent ingest --input <path-or-stdin> --json`. Use a temporary file outside the repository when standard input is impractical, then remove it.
7. Report search terms processed, sources called, source errors, results received, files written, and existing files skipped. Do not claim unavailable sources were searched.

Do not delegate this workflow to a model-specific subagent. Let the CLI own filename generation, YAML serialization, and filename-based deduplication.
