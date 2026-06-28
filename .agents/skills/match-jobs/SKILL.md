---
name: match-jobs
description: "Evaluate raw job listings against context/resume.md and context/matchCriteria.md, record 0-10 semantic match scores, and archive low-scoring or ineligible US roles. Use when the user asks to score, filter, or match fetched jobs."
---

# Match jobs

Read `context/resume.md` and `context/matchCriteria.md`, then evaluate every `.md` file in `jobListings-Raw/` whose `archived_reason` is empty.

## Apply hard exclusions first

For US listings only, archive without scoring when the description explicitly:

- denies visa sponsorship: `--archive-reason no-sponsorship`
- requires security clearance: `--archive-reason clearance-required`
- requires a US person, citizen, permanent resident, or protected person: `--archive-reason us-person-required`

Record each exclusion with:

```text
uv run job-search-agent set-match <file> --rationale <concise-evidence> --archive-reason <reason> --json
```

Do not infer a hard exclusion from silence. Canadian listings are not excluded by these rules.

## Score eligible listings

Score each listing from 0 to 10 using the repository criteria:

- Skills and domain overlap: 0-4
- Target seniority: 0-2
- Industry/domain preference: 0-2
- Salary relative to the country floor: 0-2; award 1 when salary is not listed

Use the candidate resume as the source of truth for experience and `context/matchCriteria.md` for current preferences and thresholds. Write one evidence-based sentence that explains the total. Record the result with:

```text
uv run job-search-agent set-match <file> --score <0-10> --rationale <sentence> --json
```

The CLI archives scores below 6 as `low-match` and leaves scores of 6 or higher in the raw canonical directory.

## Report

Report hard exclusions by reason, score distribution (`0-5`, `6-7`, `8-10`), low matches archived, and files remaining. List any malformed listing as an error rather than silently skipping it.
