# Testing

## Backend (pytest)

```bash
cd backend
pytest                                                     # SQLite temp DB
TEST_DATABASE_URL=postgresql+psycopg://bridge:bridge@localhost:5432/bridge_test pytest
```

The fixture runs `alembic downgrade base` then `upgrade head`, so **the real migrations build the
test schema**. Each test gets a fresh `create_app(settings)` and tables are emptied afterwards
(seeded specializations are kept). Use a dedicated test database: it is wiped.

| File | Covers |
|---|---|
| `test_health_and_config.py` | Liveness/readiness (incl. DB down → 503), security headers, CORS allow-list, settings validation (short/default secrets, SQLite and docs in production, wildcard CORS) |
| `test_auth_local.py` | Register/login, email normalisation, Argon2 hashing, role cannot be self-assigned, duplicates, weak input, enumeration-safe errors, audit without secrets, inactive users, token tampering (signature, expiry, audience, issuer, subject, `alg: none`), ignored role claims, rate limiting, local endpoints off in Supabase mode |
| `test_auth_supabase.py` | HS256 and ES256/JWKS verification with minted tokens, JIT provisioning as student, metadata role ignored, wrong secret/audience/issuer, local tokens rejected, no takeover of local accounts |
| `test_rbac_and_profile.py` | Permission matrix, seeded specializations, profile/specialization update, unknown specialization, students/professors denied admin routes (and audited), admin role changes take effect immediately, self/last-admin protection, 404/422 cases |
| `test_migrations.py` | ORM models and migrations have zero drift; full downgrade/upgrade round trip |

## Frontend

```bash
cd frontend
npm run lint && npm run typecheck && npm run build
```

No automated frontend tests yet: Playwright end-to-end tests are planned for Phase 2, once the
interface stabilises. The Phase 1 user journey was verified manually in a browser (see below).

## Continuous integration
`.github/workflows/ci.yml` on every push to `main` and every pull request:
- Backend: ruff lint + format check, PostgreSQL DDL render, pytest on **PostgreSQL 17** (service
  container), pytest on SQLite.
- Frontend: `npm ci`, lint, typecheck, production build.

## Phase 1 results (actual)
Recorded on 2026-11-25, Windows 11, Python 3.14.7, Node 24.19:

| Check | Result |
|---|---|
| `pytest` (SQLite) | **42 passed** |
| `pytest` from a clean venv using only the lock files | 42 passed, `pip check` clean |
| `ruff check` / `ruff format --check` | Clean |
| `alembic upgrade head` (SQLite, CLI) / `--sql` for PostgreSQL | Succeeds / renders valid DDL |
| Live API smoke test (uvicorn): readiness, login, `/me`, specializations, audit log | Pass |
| `npm run lint`, `npm run typecheck`, `npm run build` | Pass |
| Manual browser journey (production build): password-mismatch error → register → dashboard with live API data → session cookie not readable by page JS → sign out → `/dashboard` redirects to sign-in → wrong password error → sign in → API stopped shows the dashboard error state | Pass |
| pytest on PostgreSQL | **Not run locally** (no PostgreSQL available); runs in CI |
| Docker image build / Compose stack | **Not run** (Docker not available) |

Remaining warning: Starlette deprecates using `httpx` with its TestClient in favour of `httpx2`.
Harmless for now; revisit when upgrading test tooling.
