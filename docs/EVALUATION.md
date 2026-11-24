# Academic validation plan

> Proposed plan. Nothing below has been run; no results exist yet. The targets are development
> targets, not findings.

## Questions
1. Do AI assessments agree with independent human graders?
2. Are assessments consistent when repeated?
3. Do students complete the simulations, and do they find them useful?
4. Does practice with BRIDGE improve professional competencies compared with traditional learning?

## Built-in measurement tools
```bash
cd backend
python -m app.cli evaluation-report                     # platform-wide metrics (JSON)
python -m app.cli evaluation-report --session <id> --runs 5   # assessment consistency, not saved
```
`evaluation-report` uses only recorded data: completion rate; AI-vs-professor mean absolute error
(per corrected criterion, separately for mock and real AI); AI latency median/p90; blocked AI
outputs (rejected intents, leaks); AI calls and estimated cost; criteria that could not be observed.
Admins also see a 7-day usage summary in the admin console.

## Proposed targets
| Metric | Target |
|---|---|
| Scenario completion rate | ≥ 85% |
| Student satisfaction | ≥ 80% agree/strongly agree |
| AI vs human mean absolute error | ≤ 10 points / 100 |
| Typical AI response time | < 5 s where feasible |
| Critical scenario rule violations in the test suite | 0 |

## Pilot design (subject to university approval)
- ~30 consenting students from one specialization, randomly assigned to a BRIDGE group and a
  traditional-learning group with equal training time.
- Pre-test and post-test: a scenario-based task graded blind by two independent human graders
  using the same rubric; inter-rater reliability reported.
- BRIDGE group: 3 sessions (training mode), then one assessment-mode attempt.
- Grading agreement: humans grade a sample of BRIDGE assessment-mode attempts blind to the AI score;
  compute MAE and agreement per criterion.
- Satisfaction: short anonymous Likert questionnaire (usefulness, realism, clarity of feedback,
  workload) plus open questions.
- Ethics: informed consent, right to withdraw, pseudonymous data, no use of results in grades.
- Report all results, including negative ones. Do not claim improvement without this evidence.
