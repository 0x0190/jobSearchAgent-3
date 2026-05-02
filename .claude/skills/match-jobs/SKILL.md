---
name: match-jobs
description: Score each job listing in jobListings-Raw/ against the candidate's resume (context/resume.md) and match criteria (context/matchCriteria.md). Write a match_score (0–10) into each file's YAML frontmatter. Move listings scoring below 6 to jobListings-Archived/ with archived_reason of low-match. Also hard-archives US jobs that require security clearance, a US person, or explicitly deny sponsorship — regardless of score.
---

## Goal

Evaluate every remaining file in `jobListings-Raw/` against the candidate's profile and filter criteria. Keep strong matches in place; archive weak ones.

## Inputs

- `context/resume.md` — candidate's skills, experience, industries, and work authorization
- `context/matchCriteria.md` — salary floor, target seniority levels, preferred industries

## Step 1: Hard Exclusions (check before scoring)

For every file, read the job description and check these conditions first. If any match, write the corresponding `archived_reason` into the YAML frontmatter, move the file to `jobListings-Archived/`, and **skip scoring entirely** for that listing.

| Condition | `archived_reason` |
|---|---|
| US job that explicitly states sponsorship is NOT provided | `no-sponsorship` |
| US job that requires security clearance | `clearance-required` |
| US job that requires the applicant to be a US person (citizen, permanent resident, or protected person) | `us-person-required` |

Canadian jobs are never hard-excluded on these grounds — only apply these checks to US listings (`country: US`).

## Step 2: Scoring Rubric (0–10)

Score each remaining (non-excluded) job on these four dimensions, then sum:

### 1. Skills & Domain Match (0–4 points)
- 4: Strong overlap with resume skills (embedded C/C++, safety-critical systems, RTOS, railway/aerospace/automotive domains, safety standards like EN 50657, DO-178b, ISO 26262)
- 3: Good overlap — most key skills present but missing one or two
- 2: Partial overlap — some relevant skills but significant gaps
- 1: Minimal overlap — only surface-level match
- 0: No meaningful overlap

### 2. Seniority Match (0–2 points)
Per `context/matchCriteria.md` target levels (Staff, Lead, Principal, Senior):
- 2: Title explicitly matches target seniority
- 1: Seniority is unclear from the posting
- 0: Title is Junior, Mid-level, Associate, Intern, or Entry-level

### 3. Industry / Domain Match (0–2 points)
Per `context/matchCriteria.md`:
- 2: Strongly preferred industry (aerospace, railway/transit, automotive FuSA, autonomous vehicles, space/satellite, embedded safety-critical, hydrogen fuel cell, energy systems, battery storage, clean energy)
- 1: Acceptable industry (robotics, industrial controls/SCADA, medical devices, defence/security)
- 0: Deprioritized (general software, cloud, web, fintech, consumer electronics)

### 4. Salary (0–2 points)
Per `context/matchCriteria.md` floor ($140k CAD / $160k USD):
- 2: Salary listed and meets or exceeds floor
- 1: Salary not listed (do not penalize — flag as "salary unknown")
- 0: Salary listed and maximum is below the floor

## Step 3: After Scoring

1. Write the numeric `match_score` and a one-sentence `match_rationale` into the file's YAML frontmatter:
   ```yaml
   match_score: 7
   match_rationale: "Strong embedded C/C++ and ISO 26262 overlap, senior title, automotive domain, salary not listed."
   ```

2. If `match_score < 6`: set `archived_reason: low-match` and move the file to `jobListings-Archived/`.

3. If `match_score >= 6`: leave the file in `jobListings-Raw/` for the next skill.

## Step 4: Report

- Total files evaluated
- Hard-excluded (broken down by reason: `no-sponsorship`, `clearance-required`, `us-person-required`)
- Score distribution for scored files (how many scored 0–5, 6–7, 8–10)
- Low-match archived (`match_score < 6`)
- Files remaining in `jobListings-Raw/`
