# JobSearchAgent

This is my first attempt to create an AI job search workflow - to reclaim my sanity from mindless scrolling of job postings 😅. It is built using [Claude Code](https://claude.ai/code). It fetches listings from Dice and LinkedIn, filters and scores them against a resume and match criteria, and sends a summary email — all triggered by a single slash command.

## How it works

```
searchTerms.md
     │
     ▼
/fetch-jobs ──────────────────────────► jobListings-Raw/
                                               │
                                               ▼
                                   /archive-duplicates ──► jobListings-Archived/
                                         (trello_cards.csv)
                                                   │
                                                   ▼
                                           /match-jobs ──► jobListings-Archived/
                                            (resume.md)      (low-match, clearance,
                                        (matchCriteria.md)    no sponsorship)
                                                   │
                                                   ▼
                                       /sort-by-location
                                        ┌────────┴────────┐
                                        ▼                 ▼
                               jobMatches-Can/    jobMatches-US/
                                        └────────┬────────┘
                                                 ▼
                                         /notify-email
```

Run the full pipeline with `/run-job-search`.

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI
- [uv](https://github.com/astral-sh/uv) (for running LinkedIn [MCP server](https://github.com/stickerdaniel/linkedin-mcp-server).)
- An [agentmail](https://agentmail.to) account (for email notifications)

## Setup

**1. Clone the repo**

```bash
git clone <repo-url>
cd jobSearchAgent-3
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Purpose |
|---|---|
| `AGENTMAIL_API_KEY` | agentmail API key |
| `AGENTMAIL_INBOX_ID` | agentmail inbox ID for the sending address |

The Dice MCP server requires no credentials. LinkedIn credentials are stored locally after a one-time login (see step 3).

**3. Log in to LinkedIn**

```bash
uvx linkedin-scraper-mcp@latest --login
```

Credentials are stored in `~/.linkedin-mcp/` and reused on subsequent runs.

**4. Customize your search**

- [context/searchTerms.md](context/searchTerms.md) — one search query per line
- [context/resume.md](context/resume.md) — your resume/profile used for match scoring
- [context/matchCriteria.md](context/matchCriteria.md) — salary floor, target seniority, preferred industries, work authorization rules

## Usage

Open the project in Claude Code and run:

```
/run-job-search
```

Or run individual pipeline steps:

| Command | What it does |
|---|---|
| `/fetch-jobs` | Fetch raw listings from Dice and LinkedIn |
| `/archive-duplicates` | Archive already-applied jobs (from `trello_cards.csv`) and within-run duplicates |
| `/match-jobs` | Score listings 0–10; archive anything below 6, no-sponsorship US jobs, and US clearance jobs |
| `/sort-by-location` | Copy matched listings to `jobMatches-Can/` or `jobMatches-US/` |
| `/notify-email` | Send a summary email with all matched jobs |

## Folder structure

```
.claude/
  settings.json          # MCP server configs and tool permissions
  skills/                # Skill definitions for each pipeline step
context/
  resume.md              # Candidate profile
  searchTerms.md         # Search queries
  matchCriteria.md       # Scoring rules and hard filters
  trello_cards.csv       # Applied jobs (Date, Company, Position)
jobListings-Raw/         # All fetched listings — canonical record
jobListings-Archived/    # Filtered out: duplicates, low-match, ineligible
jobMatches-Can/          # Matched Canadian jobs
jobMatches-US/           # Matched US jobs requiring sponsorship
```

## Job listing file format

Each listing is a markdown file with YAML frontmatter:

```
{YYYY-MM-DD}-{site}-{company-slug}-{title-slug}.md
```

```yaml
---
date_fetched: 2026-04-30
site: dice               # dice | indeed | linkedin
company: Acme Corp
title: Senior Embedded Software Engineer
location: Toronto, ON, Canada
location_type: hybrid    # remote | hybrid | on-site | unknown
country: CA              # CA | US | other
url: https://...
salary: "$130,000–$150,000"
sponsorship: not required
security_clearance: none
match_score: 8
match_rationale: "Strong embedded C/C++ and EN 50128 overlap, senior title, railway domain."
archived_reason:
---

# Job Description
...
```

## Adding a new job source

1. Install or configure an MCP server for the new site.
2. Add it to [.mcp.json](.mcp.json).
3. Update the `/fetch-jobs` skill at [.claude/skills/fetch-jobs/](.claude/skills/fetch-jobs/) to call the new MCP tool.
