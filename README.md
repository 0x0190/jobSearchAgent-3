# JobSearchAgent

A Codex-native workflow for fetching job listings, removing duplicates, scoring roles against a private resume, organizing Canadian and US matches, and sending an optional AgentMail summary.

The semantic steps run as repository skills. A tested Python CLI handles deterministic operations such as YAML serialization, deduplication, file moves, output rebuilding, and email rendering.

## Pipeline

```text
context/searchTerms.md
        │
        ▼
   $fetch-jobs ───────────────────────────► jobListings-Raw/
                                                   │
                                                   ▼
                                      $archive-duplicates ──► jobListings-Archived/
                                                   │
                                                   ▼
                                            $match-jobs ─────► jobListings-Archived/
                                                   │
                                                   ▼
                                         $sort-by-location
                                           ┌───────┴───────┐
                                           ▼               ▼
                                  jobMatches-Can/  jobMatches-US/
                                           └───────┬───────┘
                                                   ▼
                                             $notify-email
```

Invoke `$run-job-search` to run the complete sequence.

## Prerequisites

- Codex CLI, IDE extension, or app with repository skill support
- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- An [AgentMail](https://agentmail.to) account for email notifications
- A one-time LinkedIn MCP login

Project-scoped MCP configuration is loaded from `.codex/config.toml` only after the repository is trusted in Codex. The configured sources are Dice and LinkedIn; Indeed is not configured.

## Setup

```bash
git clone <repo-url>
cd jobSearchAgent-3
uv sync --dev

cp .env.example .env
cp context/resume.example.md context/resume.md
cp context/trello_cards.example.csv context/trello_cards.csv

uvx linkedin-scraper-mcp@latest --login
```

Then:

1. Mark the repository as trusted in Codex so its MCP servers can load.
2. Fill in `context/resume.md` with the candidate profile.
3. Add prior applications to `context/trello_cards.csv` using `Date,Company,Position` columns.
4. Adjust `context/searchTerms.md` and `context/matchCriteria.md`.
5. Fill in `.env`:

| Variable | Purpose |
|---|---|
| `AGENTMAIL_API_KEY` | Bearer token for AgentMail |
| `AGENTMAIL_INBOX_ID` | Inbox used to send the summary |
| `NOTIFY_MAIL_DESTINATION` | Recipient email address |

Candidate inputs, credentials, fetched listings, and generated matches are ignored by Git.

Verify setup without modifying listings:

```bash
uv run job-search-agent preflight
```

## Codex skills

Type `$` in Codex to select a repository skill.

| Skill | Behavior |
|---|---|
| `$run-job-search` | Run fetch, deduplicate, match, sort, and notify in order |
| `$fetch-jobs` | Search Dice and LinkedIn and ingest normalized listings |
| `$archive-duplicates` | Archive applied jobs and duplicate listings |
| `$match-jobs` | Apply hard eligibility rules and score remaining jobs from 0–10 |
| `$sort-by-location` | Rebuild Canadian and US match folders from scores of 6+ |
| `$notify-email` | Send the current match summary through AgentMail |

The full-pipeline and email skills require explicit invocation because they send external email. The two Trello skills are explicit-only placeholders and make no changes.

## Deterministic CLI

Skills call the same utility that can be audited independently:

```bash
uv run job-search-agent --help
uv run job-search-agent archive-duplicates --dry-run
uv run job-search-agent sort-matches --dry-run
uv run job-search-agent notify --dry-run
```

Every command accepts `--json` for machine-readable orchestration. Mutating listing operations use atomic writes, and archive name collisions preserve both files.

### Ingest schema

`ingest --input` accepts one JSON object or an array. Required fields are `site`, `company`, `title`, `location`, `country`, and `url`; `date_fetched` defaults to today. The CLI writes this Markdown contract:

```yaml
---
date_fetched: 2026-06-28
site: dice
company: Acme Corp
title: Senior Embedded Software Engineer
location: Toronto, ON, Canada
location_type: hybrid
country: CA
url: https://example.com/job
salary: $150,000–$170,000
sponsorship: not required
security_clearance: none
match_score: 8
match_rationale: Strong embedded C++ and safety-critical domain overlap.
archived_reason:
---
```

`jobListings-Raw/` is canonical. The country match folders contain generated copies and are rebuilt by `sort-matches`.

## Development and validation

```bash
uv run pytest
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/fetch-jobs
```

Tests use temporary repositories, dry-run notification, and a mocked AgentMail endpoint. They never call live MCP servers or send live email.

## Troubleshooting

- **Skills are missing:** Start a fresh Codex session from the repository root. Codex discovers repository skills from `.agents/skills/`.
- **MCP servers are missing:** Confirm the repository is trusted, inspect `codex mcp list`, and restart the session after configuration changes.
- **LinkedIn fails to start:** Repeat `uvx linkedin-scraper-mcp@latest --login` and confirm `uvx` is on `PATH`.
- **Preflight fails:** Create the private context files from their examples and populate all three AgentMail variables.
- **Email preview is needed:** Run `uv run job-search-agent notify --dry-run`; this never performs an HTTP request.
