# Job Search Agent

## Repository purpose

This repository is a Codex-native job-search workflow. Repository skills fetch listings through MCP, apply candidate-specific criteria, organize matches, and optionally send an AgentMail summary. Keep semantic interpretation in skills and deterministic file operations in the `job-search-agent` Python CLI.

## Working agreements

- Use `uv sync --dev` for setup and `uv run pytest` for verification.
- Run `uv run job-search-agent <command> --help` before changing a CLI contract.
- Keep repository skills in `.agents/skills/`; validate every skill with Codex's `quick_validate.py` after edits.
- Keep `SKILL.md` concise and imperative. Put triggering details in its frontmatter description.
- Treat `jobListings-Raw/` as the canonical record. Country match folders are generated views and may be rebuilt.
- Never commit `.env`, `context/resume.md`, `context/trello_cards.csv`, fetched listings, or generated matches.
- Never print credentials or include them in command arguments, fixtures, logs, or skill text.
- Do not send email during tests. Use `job-search-agent notify --dry-run` unless the user explicitly invokes the notification or full-pipeline skill.

## Verification

After changing runtime behavior, run `uv run pytest`. After changing Codex configuration or skills, also parse `.codex/config.toml`, validate all skill folders, and verify skill/MCP discovery from a fresh Codex session.
