# Guide for AI coding agents (and humans) working on BRIDGE

Read `README.md`, `docs/ARCHITECTURE.md` and `docs/LIMITATIONS.md` first.

## Non-negotiable rules
- **AI proposes, code decides.** Only `app/simulation/engine.py` changes scenario state. AI output is
  validated in `app/ai/service.py` / `app/services/assessment.py` and never computes final scores.
- Authorization lives in the backend: `app/security/permissions.py`, `require_permission`, and the
  ownership/course rules in `app/services/access.py`. Return 404 (not 403) for other users' data.
- Schema changes ship as Alembic migrations; `tests/test_migrations.py` fails on drift.
- Request schemas extend `StrictModel` (unknown fields rejected).
- Scenario files must pass `python -m app.cli check-scenarios`; all content fictional; set
  `review_status` honestly. In YAML flow maps, quote strings containing commas or colons.
- Never log or store prompts, passwords, tokens or API keys in the database or AI usage logs.
- Never claim something works without running it; record results in `docs/TESTING.md` and gaps in
  `docs/LIMITATIONS.md`. Never invent research or effectiveness results.

## Commands
Backend (`backend/`): `pytest` · `ruff check . && ruff format --check .` ·
`python -m app.cli setup | sync-scenarios | check-scenarios | seed-demo | evaluation-report` ·
`uvicorn app.main:create_app --factory --reload`

Frontend (`frontend/`): `npm run lint` · `npm run typecheck` · `npm run build` · `npm run test:e2e`
(needs `BRIDGE_PYTHON`; `PW_CHANNEL=msedge` uses installed Edge).

## Next.js version warning
Next.js 16 with Cache Components: read `frontend/node_modules/next/dist/docs/` before writing
frontend code. Anything that reads cookies or params must render inside a `<Suspense>` boundary (the
`(app)` layout provides one). Server Actions live in `src/app/actions/`; data access through
`src/lib/auth.ts` (`api()`), which keeps the token server-side.

## Where things go
| What | Where |
|---|---|
| Routes (thin) | `backend/app/api/` |
| Business logic | `backend/app/services/` |
| Rules / scenario schema | `backend/app/simulation/` |
| AI providers and policy | `backend/app/ai/` |
| Scenario content | `scenarios/<specialization>/*.yaml` |
| Pages | `frontend/src/app/(app)/…` |
| Workplace UI | `frontend/src/components/workplace/` |
