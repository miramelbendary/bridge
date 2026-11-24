# Roadmap

Phases run in order. A phase is only marked complete when its acceptance criteria are verified.
The next phase does not start until the current one has been reviewed.

| # | Phase | Status |
|---|---|---|
| 1 | Project foundations | **Complete, awaiting review** (PostgreSQL path verified in CI only, see below) |
| 2 | Application interface | Not started |
| 3 | Core simulation engine | Not started |
| 4 | AI integration | Not started |
| 5 | Assessment engine | Not started |
| 6 | International Trade MVP | Not started |
| 7 | Translation and INFOCOM | Not started |
| 8 | Adaptive learning (+ RAG) | Not started |
| 9 | Professor and administrator dashboards | Not started |
| 10 | Testing, security and optimization | Not started |
| 11 | Deployment and final delivery | Not started |

## Phase 1 — Project foundations

**Objective:** a running, tested skeleton that every later phase builds on: frontend and backend
structure, PostgreSQL schema under migrations, authentication, role-based authorization, CI, docs.

### Plan and outcome

| Task | Outcome |
|---|---|
| Inspect repository | Empty workspace: built from scratch |
| Requirements and boundaries | `docs/REQUIREMENTS.md` |
| Backend structure (FastAPI modular monolith) | Done |
| PostgreSQL configuration | Done: Docker Compose (`pgvector/pgvector:pg17`) and CI service |
| Initial migrations | `0001_foundations`: users, user_profiles, specializations, audit_logs, seed data |
| Authentication | Local JWT provider (working end to end) + Supabase token verification (tested with synthetic tokens) |
| Authorization | Code-defined role → permission map, enforced by backend dependencies |
| Environment variables | `.env.example` files, validated settings, unsafe production configs rejected |
| Automated testing and CI | 42 pytest tests; GitHub Actions: backend on PostgreSQL + SQLite, frontend lint/typecheck/build |
| Frontend structure | Next.js 16: landing, sign in, register, dashboard (live API data), httpOnly session cookie |
| Documentation | README, ROADMAP, CHANGELOG, CLAUDE.md, docs/* |

### Acceptance criteria

| Criterion | Status |
|---|---|
| Frontend starts | Verified locally (`next build` + `next start`) |
| Backend starts | Verified locally (uvicorn) |
| Database connects | Verified locally on SQLite; PostgreSQL connection **verified only once CI runs** |
| Migrations execute | Verified on SQLite (tests + CLI); PostgreSQL DDL rendered offline; executed on PostgreSQL in CI |
| Authentication works | Verified: tests + live register/login/dashboard in a browser |
| Initial automated tests pass | 42/42 locally on SQLite |

**Blockers recorded:** no Docker or PostgreSQL on the development machine used for Phase 1, and no
Supabase project credentials. Independent work continued; see `docs/LIMITATIONS.md`.

## Phase 2 — Application interface (next)

Design system (tokens, shadcn/ui components, dark mode), navigation shell, polished auth pages,
student dashboard, specialization selection (the API already supports it), scenario library and the
virtual workplace layout (inbox, messages, documents, tasks), with loading/empty/error states.
Also: Supabase login on the frontend (if a project is available) and Playwright end-to-end tests.
