---
name: trello-sync-csv
description: FUTURE SKILL — Sync context/trello_cards.csv from the Trello job search board. Overwrites the CSV with the current state of all cards on the board so the deduplication skill has an up-to-date list of applied jobs.
---

## Status

This skill is a placeholder for future implementation. Do not invoke it yet.

## Planned Behavior (when implemented)

1. Authenticate with the Trello API using `TRELLO_API_KEY` and `TRELLO_TOKEN` from `.env`.
2. Pull all cards from the job search Trello board.
3. For each card, extract: date created, company name, position title.
4. Overwrite `context/trello_cards.csv` with the current data in `Date,Company,Position` format.
5. Report: total cards synced, last updated date.

## Dependencies

- Trello API key and token (to be added to `.env`)
- Trello board ID and list structure (to be documented in `context/trello_config.md` when created)
