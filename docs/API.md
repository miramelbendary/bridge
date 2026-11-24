# API

Base path `/api/v1`. Interactive OpenAPI docs at `http://localhost:8000/docs` (development only).
Authenticated routes need `Authorization: Bearer <token>`. Errors: `{"detail": ...}`; engine errors
return `{"detail": {"code": "...", "message": "..."}}` (409 for unavailable/finished, 422 otherwise).
State-changing session routes accept an `Idempotency-Key` header.

## Auth & users
| Method | Path | Notes |
|---|---|---|
| GET | `/auth/config` | Provider in use |
| POST | `/auth/register` · `/auth/login` | Local provider; rate limited; registration can be closed by admins |
| GET | `/users/me` · PATCH `/users/me/profile` | Profile and specialization |
| GET | `/specializations` | Active specializations |

## Simulation (any signed-in user)
| Method | Path | Notes |
|---|---|---|
| GET | `/scenarios?specialization=` | Published (authors also see drafts) |
| GET | `/scenarios/{slug}` | Introduction details |
| POST | `/sessions` | `{scenario_slug, mode, difficulty, assignment_id?}`; an assignment fixes mode/difficulty |
| GET | `/sessions` | My attempts |
| GET | `/sessions/{id}` | Workplace view (owner; authorized professors/admins read-only) |
| POST | `/sessions/{id}/actions` | `{action_id, justification}` |
| POST | `/sessions/{id}/messages` | `{character_id, text}` → AI reply; may perform a validated action |
| POST | `/sessions/{id}/submissions` | `{submission_id, text}` (revisions allowed) |
| POST | `/sessions/{id}/hint` | Training mode only |
| POST | `/sessions/{id}/finish` | Completes and assesses (idempotent) |
| POST | `/sessions/{id}/abandon` | |
| GET | `/sessions/{id}/timeline` · `/sessions/{id}/assessment` | Event log · assessment + report + reviews |

## Progress
`GET /me/competencies`, `GET /me/recommendations`, `GET /me/assignments`, `GET /me/resources/search?q=`

## Teaching (professors, admins)
| Method | Path |
|---|---|
| GET/POST | `/teach/courses` |
| GET | `/teach/courses/{id}` · `/teach/courses/{id}/progress` · `/teach/courses/{id}/export.csv` |
| POST/DELETE | `/teach/courses/{id}/members[/{student_id}]` · `/teach/courses/{id}/assignments[/{id}]` |
| GET | `/teach/students/{id}/sessions` · `/teach/review-queue` · `/teach/assessments/{id}` |
| POST | `/teach/assessments/{id}/reviews` `{criterion_id?, new_score?, justification}` |
| GET | `/teach/scenarios/{slug}/definition` |
| POST | `/teach/scenarios/validate` · `/teach/scenarios` (new version) |
| PUT | `/teach/scenarios/{slug}/rubric` |
| GET/POST/DELETE | `/teach/resources[/{id}]` (`{title, filename, content, visibility, specialization_code}`) |

## Administration
| Method | Path |
|---|---|
| GET | `/admin/users` · `/admin/audit-logs` · `/admin/usage?days=` · `/admin/scenarios` · `/admin/specializations` |
| PATCH | `/admin/users/{id}/role` · `/admin/users/{id}/active` · `/admin/settings` · `/admin/specializations/{id}` |
| POST | `/admin/specializations` · `/admin/scenarios/{slug}/status` |

## Health
`GET /health`, `GET /health/ready` (database check).
