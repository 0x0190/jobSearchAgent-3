# Job Match Criteria

Used by the `03-match-jobs` skill to score and filter job listings.

## Salary

Minimum acceptable salary for Canada based jobs is: **$140,000 CAD**
Minimum acceptable salary for US based jobs is: **$160,000 USD**

- Exclude listings where the stated maximum salary is below this floor.
- If no salary is listed, do not exclude — flag as `"salary unknown"` and assign 1 point.

## Seniority

**Target levels:** Staff, Lead, Principal, Senior

**Exclude:** Junior, Mid-level, Associate, Intern, Entry-level

- If seniority is unclear from the posting, include but flag as `"seniority unclear"`.

## Industry / Domain

**Strongly preferred (full points):**
- Aerospace / avionics (DO-178b, FAA certification)
- Railway / transit signalling (EN 50657, EN 50128, SIL3/SIL4)
- Automotive functional safety (ISO 26262, FuSA)
- Embedded safety-critical systems
- Fuel cell / hydrogen / energy systems / battery storage / clean energy

**Acceptable (partial points):**
- Robotics / autonomous vehicles
- Space / satellite systems
- Industrial controls / SCADA
- Medical devices (IEC 62304)
- Defence / security

**Deprioritized (low score, not excluded):**
- General software (web, cloud, SaaS, fintech)
- Consumer electronics (unless embedded/firmware)
- Data engineering / ML infrastructure

## Work Authorization

The candidate is authorized to work in Canada without sponsorship. US positions require visa sponsorship.

- If a US job explicitely mentions sponsorship is NOT provided, please archive it. Candidate requires visa sponsorship. 
- All other US jobs should go to `jobMatches-US/` for the candidate to evaluate.
- Note in match rationale if sponsorship is required for a US role.

## Security Clearance

Candidate can get security clearance in Canada. However US positions that require security clearance also require the applicant to be a US person. A US person includes a US citizen, permanent resident, or protected person. Candidate is not a US person so he is not eligible to apply.

- If a US job requires security clearence please archive it. Candidate is not eligible to apply.
- If a US job requires a US person, please archive it. Candidate is NOT a US person.
- All other US jobs should go to `jobMatches-US/` for the candidate to evaluate.