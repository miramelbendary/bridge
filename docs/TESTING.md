# Testing

## How to run
```bash
cd backend && pytest                       # SQLite; set TEST_DATABASE_URL for PostgreSQL
cd frontend && npm run lint && npm run typecheck && npm run build
cd frontend && npm run test:e2e            # needs BRIDGE_PYTHON (python with backend deps);
                                           # PW_CHANNEL=msedge to use installed Edge on Windows
cd backend && python -m app.cli check-scenarios
```

## Backend suite (121 tests)
| File | Covers |
|---|---|
| `test_health_and_config.py` | Health/readiness, headers, CORS, settings validation incl. `.env` parsing |
| `test_auth_local.py`, `test_auth_supabase.py` | Registration/login, hashing, enumeration safety, token tampering, `alg: none`, Supabase HS256/JWKS, account-takeover prevention, rate limiting |
| `test_rbac_and_profile.py` | Permission matrix, specializations, profile, admin role management |
| `test_migrations.py` | Zero model/migration drift, downgrade/upgrade round trip |
| `test_engine.py` | Consequences and branching (best/late/over-budget outcomes), justification rule, exclusive decisions, preconditions, clamping, hints only in training, hidden variables, difficulty effects, time limit, finality, word minimums, determinism, event ordering, restricted facts withheld until unlocked, **random branch exploration of every scenario at every difficulty and mode** (bounds and valid outcome invariants) |
| `test_scenario_schema.py` | Rejection of bad weights, unknown references, malformed conditions, extra fields, unknown competencies, missing default outcome; no code execution in conditions |
| `test_ai_and_assessment.py` | Intent → action via engine; AI cannot trigger unlisted/unavailable actions; low-confidence ignored; restricted-fact leak blocked; provider failure → labelled fallback; message limit; Claude provider refusal/invalid-output mapping (stubbed); injection detector; evidence-based deterministic weighting; insufficient evidence ≠ failure; invented evidence rejected; invalid levels rejected; assessor failure → mock; injection flagged for review; one assessment per session; strengths consistent with scores |
| `test_platform_api.py` | Students cannot access others' sessions; professors only via course membership, read-only; teaching/admin endpoints denied to students; idempotency; stale-write conflict; recovery after reload; engine error codes; finished sessions read-only; versioning keeps old sessions on old versions; scenario/rubric editing; only admins publish; assignments fix mode/difficulty; review audit trail; progress & CSV; recommendations; resource visibility and validation; admin settings, registration closing, deactivation, specializations; demo seed idempotent |
| `test_evaluation.py` | Evaluation report uses only recorded data; consistency re-runs persist nothing |

## End-to-end (Playwright, 6 tests)
Real backend (fresh DB + demo data, mock AI) and production frontend build:
1. Register → choose specialization → start scenario → free-text message becomes an action → justified decision → deliverable → finish → report → competency profile.
2. Translation deliverables render right-to-left (`dir="rtl" lang="ar"`).
3. Assessment mode has no hints; students get "Not found" on teaching/admin pages.
4. Professor corrects a criterion with justification; status becomes "Reviewed by professor".
5. Administrator console renders settings, usage and audit log.
6. axe-core WCAG 2 A/AA scan of 6 pages: no serious or critical violations.

## Results recorded on 2026-11-25 (Windows 11, Python 3.14.7, Node 24.19)
| Check | Result |
|---|---|
| Backend `pytest` (SQLite) | **121 passed** |
| Fresh venv from lock files + `pip check` + pytest | Clean; 118 passed at that point (3 tests added afterwards, then 121 passed) |
| `ruff check`, `ruff format --check` | Clean |
| `check-scenarios` | 6/6 valid |
| Frontend lint, typecheck, production build | Pass (20 routes) |
| Playwright e2e (Edge channel) | **6 passed** |
| Manual browser run (student, professor, admin journeys) | Pass; found and fixed: overstated strengths, double full stops, 4 px overflow on the upload form |
| Clean-copy run of `start.ps1` (no venv/node_modules/.env/db) | Pass after fixing a `.env` CORS parsing bug the run exposed |
| Backend tests on PostgreSQL | **Not run locally** (no PostgreSQL); configured in CI |
| Docker images / Compose | **Not run** (no Docker on the build machine) |
| Claude provider against the real API | **Not run** (no key); covered by stubbed tests |
| `start.sh` on macOS/Linux | **Not run** (Windows machine) |
