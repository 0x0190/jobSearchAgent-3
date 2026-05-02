---
name: fetch-jobs
description: Fetch raw job listings from all configured MCP job search servers (Dice, Indeed, LinkedIn) using search terms defined in context/searchTerms.md. Save each listing as a markdown file with YAML frontmatter in jobListings-Raw/. Skip listings that already exist (filename-based dedup).
---

## Goal

Search all configured job sites for every search term in `context/searchTerms.md` and save new listings to `jobListings-Raw/`. Use a Haiku subagent for the actual fetching and file-writing to keep costs low.

## Steps

1. Read `/home/wasabi/Repository/JobSearchAgent-3/context/searchTerms.md`. Collect every non-empty line as a search term.

2. Note today's date in `YYYY-MM-DD` format.

3. Spawn a subagent using the Agent tool with these parameters:
   - **description:** `"fetch job listings"`
   - **model:** `"haiku"`
   - **prompt:** The self-contained prompt below, with `{search_terms}` replaced by the actual list of search terms and `{today}` replaced by today's date.

---

### Subagent prompt (fill in `{search_terms}` and `{today}` before passing)

You are a job-listing fetcher working in `/home/wasabi/Repository/JobSearchAgent-3/`.

Today's date: `{today}`

Search terms to process (one per line):
```
{search_terms}
```

#### A — Load MCP tool schemas

Before calling any MCP tools, use the `ToolSearch` tool to load their schemas:

- Query: `"select:mcp__Dice__search_jobs"`

This is required — calling MCP tools without first fetching their schema will fail with an `InputValidationError`.

#### B — Call MCP tools

For each search term, call every configured job search MCP tool:

- **Dice:** `mcp__Dice__search_jobs`
  - Args: `keyword=<search term>`, `jobs_per_page=5`, `page_number=1`
  - Optionally add `posted_date="SEVEN"` if results look stale
- **Indeed MCP** — skip if not available; note it in the final report
- **LinkedIn MCP** — skip if not available; note it in the final report

If a call fails, log it and continue — do not abort.

#### C — Extract fields from each result

For each listing extract:
- `site`: `dice`, `indeed`, or `linkedin`
- `company`: company name
- `title`: job title
- `location`: full location string
- `location_type`: `remote`, `hybrid`, `on-site`, or `unknown`
- `country`: `CA` (Canada), `US` (United States), or `other`
- `url`: direct link to the posting
- `salary`: salary range if present, otherwise `"not listed"`
- `sponsorship`: `provided` / `not provided` / `not required` / `not listed` — infer from phrases like "sponsorship available", "must be authorized to work", "visa sponsorship not available"
- `security_clearance`: `required` / `preferred` / `none` / `not listed` — infer from phrases like "security clearance required", "clearance preferred"

#### D — Generate the filename

Format: `{YYYY-MM-DD}-{site}-{company-slug}-{title-slug}.md`

**Slug rules:** lowercase → replace spaces with hyphens → strip all non-alphanumeric, non-hyphen characters → collapse consecutive hyphens → trim leading/trailing hyphens.

Examples:
- `"Acme Corp & Partners"` → `acme-corp-partners`
- `"Senior Embedded S/W Engineer (C++)"` → `senior-embedded-sw-engineer-c`

#### E — Skip duplicates

If a file with that name already exists in `/home/wasabi/Repository/JobSearchAgent-3/jobListings-Raw/`, skip it.

#### F — Write the file

Save to `/home/wasabi/Repository/JobSearchAgent-3/jobListings-Raw/<filename>` with this exact structure:

```
---
date_fetched: {YYYY-MM-DD}
site: {site}
company: {company}
title: {title}
location: {location}
location_type: {location_type}
country: {country}
url: {url}
salary: "{salary}"
sponsorship: {sponsorship}
security_clearance: {security_clearance}
match_score:
match_rationale:
archived_reason:
---

# {title} — {company}

{full job description text}
```

#### G — Return a report

When finished, return a concise summary:
- Search terms processed
- Sites called (and any skipped or errored)
- Total listings fetched
- Total new files written
- Total skipped (already existed)

---

4. After the subagent completes, display its report to the user.
