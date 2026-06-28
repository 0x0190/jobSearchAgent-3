---
name: notify-email
description: "Send an AgentMail summary of the current Canadian and US job matches using repository environment variables. Use only when the user explicitly asks to send the match email or as the final stage of an explicitly invoked full job-search pipeline."
---

# Notify by email

Invocation of this skill authorizes one summary email for the current match folders.

1. Confirm `.env` provides `AGENTMAIL_API_KEY`, `AGENTMAIL_INBOX_ID`, and `NOTIFY_MAIL_DESTINATION` without printing their values.
2. Run `uv run job-search-agent notify --json`.
3. Report the Canadian and US counts and the returned message identifier.

If the user asks to preview rather than send, use `uv run job-search-agent notify --dry-run` and present the subject and rendered body. The CLI sorts matches by score, escapes HTML, includes a plain-text alternative, sends a zero-match message when appropriate, and returns a nonzero status for API failures.
