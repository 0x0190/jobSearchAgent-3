# JobSearchAgent

Automated job search pipeline using Claude Code skills, MCP servers, and the agentmail API.

## Pipeline Overview

```
searchTerms.md
     │
     ▼
/fetch-jobs ──────────────────────────► jobListings-Raw/
                                               │
                                               ▼
                                   /archive-duplicates ──► jobListings-Archived/
                                         (trello_cards.csv)       │
                                                                   ▼
                                                           /match-jobs ──► jobListings-Archived/
                                                            (resume.md)      (low-match)
                                                        (matchCriteria.md)
                                                                   │
                                                                   ▼
                                                       /sort-by-location
                                                        ┌────────┴────────┐
                                                        ▼                 ▼
                                               jobMatches-Can/    jobMatches-US/
                                                        └────────┬────────┘
                                                                 ▼
                                                         /notify-email
                                                    (wasabi.buff@gmail.com)
```

Run the full pipeline with: `/run-job-search`

## Skills

| Skill | Command | Description |
|---|---|---|
| Fetch Jobs | `/fetch-jobs` | Fetch listings from all MCP job search servers |
| Archive Duplicates | `/archive-duplicates` | Move already-applied and duplicate listings to archive |
| Match Jobs | `/match-jobs` | Score listings against resume and match criteria |
| Sort by Location | `/sort-by-location` | Copy matches to `jobMatches-Can/` or `jobMatches-US/` |
| Notify Email | `/notify-email` | Send summary email via agentmail |
| Run Full Search | `/run-job-search` | Run skills 01–05 in sequence |
| Trello Sync CSV | `/trello-sync-csv` | **Future** — Sync `trello_cards.csv` from Trello board |
| Trello Update Board | `/trello-update-board` | **Future** — Move Trello cards by application status |

## Folder Structure

```
.claude/
  settings.json          # MCP server configs + tool permissions
  skills/                # All skill definitions
context/
  resume.md              # Candidate profile (skills, experience, work authorization)
  searchTerms.md         # Search queries, one per line
  trello_cards.csv       # Applied jobs tracker (Date,Company,Position)
  matchCriteria.md       # Salary floor, seniority targets, preferred industries
jobListings-Raw/         # All fetched listings (canonical record)
jobListings-Archived/    # Filtered out: already-applied, duplicates, low-match
jobMatches-Can/          # Matched Canadian jobs (copied from Raw)
jobMatches-US/           # Matched US jobs — sponsorship required (copied from Raw)
```

## Job Listing File Format

**Filename:** `{YYYY-MM-DD}-{site}-{company-slug}-{title-slug}.md`
Example: `2026-04-30-dice-acme-corp-senior-embedded-software-engineer.md`

```markdown
---
date_fetched: 2026-04-30
site: dice               # dice | indeed | linkedin
company: Acme Corp
title: Senior Embedded Software Engineer
location: Toronto, ON, Canada
location_type: hybrid    # remote | hybrid | on-site | unknown
country: CA              # CA | US | other
url: https://...
salary: "$130,000–$150,000"   # or "not listed"
sponsorship: not required     # provided | not provided | not required | not listed
security_clearance: none      # required | preferred | none | not listed
match_score: 8
match_rationale: "Strong embedded C/C++ and EN 50128 overlap, senior title, railway domain."
archived_reason:
---

# Job Description

[full job description text]
```

## MCP Servers

| Site | MCP Tool | Status |
|---|---|---|
| Dice | `mcp__claude_ai_Dice_Job_Search__search_jobs` | Configured |
| Indeed | TBD | Add to settings.json |
| LinkedIn | TBD | Add to settings.json |

## Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `AGENTMAIL_API_KEY` | agentmail API authentication |
| `AGENTMAIL_INBOX_ID` | agentmail inbox ID for sending |
| `TRELLO_API_KEY` | Trello API key (future) |
| `TRELLO_TOKEN` | Trello user token (future) |

## Deduplication Logic

A listing is archived by `02-archive-duplicates` if:
- `company` + `title` fuzzy-matches any row in `context/trello_cards.csv` → `archived_reason: already-applied`
- A file with the same name already exists in `jobListings-Archived/` → `archived_reason: duplicate`

A listing is archived by `03-match-jobs` if:
- `match_score < 6` → `archived_reason: low-match`

## Adding a New Job Search Site

1. Install or configure the MCP server for the new site.
2. Add the MCP server entry to `.claude/settings.json`.
3. Update the `01-fetch-jobs.md` skill to include a call to the new MCP tool.
4. Update the MCP Servers table in this file.
