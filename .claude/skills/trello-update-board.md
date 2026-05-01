---
name: trello-update-board
description: FUTURE SKILL — Update the Trello job search board based on application status changes (interview scheduled, rejected, offer received). Moves Trello cards to the appropriate list.
---

## Status

This skill is a placeholder for future implementation. Do not invoke it yet.

## Planned Behavior (when implemented)

Given: company name, position title, and new status (e.g. `interview`, `rejected`, `offer`).

1. Authenticate with the Trello API using `TRELLO_API_KEY` and `TRELLO_TOKEN` from `.env`.
2. Search the board for a card matching the company + position.
3. Move the card to the appropriate Trello list based on the new status.
4. Optionally add a comment to the card with the date and status change.

## Dependencies

- Trello API key and token (to be added to `.env`)
- Board list ID mapping (to be documented in `context/trello_config.md` when created)
