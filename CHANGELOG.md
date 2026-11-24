# Changelog

## [1.0.0] — 2026-11-25 — Phases 2–11: complete platform

### Added
- **Simulation engine** (`app/simulation/`): validated scenario schema with cross-reference checks,
  a safe JSON condition language (no `eval`), deterministic state machine with variables, effects,
  clamping, timed/conditional/triggered events, mutually exclusive decisions, justification
  requirements, difficulty settings, simulated clock and time limits, training feedback and hints,
  outcomes, and a student view that hides hidden variables.
- **Sessions**: append-only `session_events` log, optimistic concurrency (`state_version`),
  `Idempotency-Key` support, recovery after reload, immutable scenario versions per attempt.
- **AI layer** (`app/ai/`): provider abstraction; deterministic mock provider; Claude provider using
  structured outputs (`messages.parse`); intent proposals validated against available actions;
  restricted facts withheld until unlocked plus leak blocking; labelled scripted fallbacks; per-
  session message limits, daily per-user limits, per-session cost budgets; usage and cost logging.
- **Assessment**: evidence collection, validation of AI judgements (known criteria, allowed levels,
  real and relevant evidence refs), rule-based objective signals, deterministic weighting,
  insufficient-evidence handling, prompt-injection flagging, personalised reports, professor review
  with retained originals and audit.
- **Adaptive learning**: competency profiles with confidence, explainable recommendations,
  educational resource upload/chunking/TF-IDF retrieval with citations, professor-only visibility.
- **Courses**: membership-based professor authorization, assignments that fix mode and difficulty,
  progress and common-weakness analytics, CSV export.
- **Administration**: platform/AI settings, usage dashboard, account activation, specializations,
  scenario publication.
- **Six scenarios** (2 per specialization), sample teaching notes, demo seed (`app.cli setup`).
- **Frontend**: app shell, dashboard, scenario library and intro, virtual workplace, printable
  report, history, competency chart, teaching pages (courses, review, students, rubric and scenario
  editors, resources), admin console, demo-mode sign-in panel.
- **Testing**: 121 backend tests (incl. random branch exploration of every scenario), 6 Playwright
  end-to-end journeys with an axe accessibility scan; CI runs both.
- **Packaging**: `start.cmd`/`start.ps1`/`start.sh` one-command start, root `docker-compose.yml`
  (PostgreSQL + API + web), frontend Dockerfile, `evaluation-report` CLI, full documentation.

### Fixed
- `CORS_ORIGINS` given as a comma-separated string in `.env` crashed startup (found by the
  clean-copy start test).
- Report strengths could contradict final scores when using the mock evaluator.

## [0.1.0] — 2026-11-25 — Phase 1: Project foundations
FastAPI backend, users/profiles/specializations/audit log, Alembic migrations, local and Supabase
token authentication, RBAC, rate limiting, security headers, Next.js frontend with httpOnly session
cookie, CI, documentation.
