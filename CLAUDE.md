# Guide for AI coding agents (and humans) working on BRIDGE

Read `README.md`, `ROADMAP.md` and `docs/ARCHITECTURE.md` first.

## Non-negotiable rules
- The AI model never modifies authoritative state (scenario state, resources, scores, roles).
  Backend code applies all changes after validating them.
- Authorization lives in the backend (`app/security/permissions.py` + `require_permission`).
  Hiding UI is never access control. Roles are always read from the database, never from tokens.
- Every schema change ships as an Alembic migration; `tests/test_migrations.py` fails if models and
  migrations drift. Never use `Base.metadata.create_all` outside throwaway experiments.
- Request schemas extend `StrictModel` (unknown fields rejected).
- Never log or audit passwords, tokens or full student submissions.
- Do not mark anything complete in ROADMAP.md unless it was run and verified. Record limitations in
  `docs/LIMITATIONS.md`. Do not invent research results or effectiveness claims.
- Work one phase at a time; update ROADMAP.md and CHANGELOG.md at the end of each phase.

## Commands
Backend (from `backend/`):
- Tests: `pytest` (SQLite) or `TEST_DATABASE_URL=postgresql+psycopg://... pytest`
- Lint: `ruff check . && ruff format --check .`
- New migration: `alembic revision --autogenerate -m "..."`, then review it by hand
- Run: `uvicorn app.main:create_app --factory --reload`

Frontend (from `frontend/`): `npm run lint`, `npm run typecheck`, `npm run build`, `npm run dev`.

## Next.js version warning
The frontend uses Next.js 16 with Cache Components enabled. Its APIs differ from older versions:
read `frontend/node_modules/next/dist/docs/` before writing frontend code (see `frontend/AGENTS.md`).
Any component that reads cookies must sit inside a `<Suspense>` boundary.

## Where things go
- HTTP routes: `backend/app/api/` (thin; call services)
- Business logic: `backend/app/services/` (no FastAPI imports)
- Permissions: `backend/app/security/permissions.py`
- Frontend server-only data access: `frontend/src/lib/` (`server-only` imports)
