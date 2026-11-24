# BRIDGE

**An AI-Powered Adaptive Workplace Simulation and Competency Assessment Platform for University
Students.**

Students step into simulated workplaces, talk to AI-backed colleagues and clients, read real-looking
documents, make decisions with consequences, write professional deliverables, and receive a
rubric-based report whose every score points to evidence from their own work. Professors review and
correct assessments; administrators manage the platform.

| Specialization | Scenarios |
|---|---|
| International Trade | *Delayed International Shipment* · *Unexpected Freight Cost Increase* |
| Translation (English → Arabic, right-to-left) | *Demanding International Client* · *Conflicting Translation Requirements* |
| INFOCOM — Information and Communication | *Corporate Media Crisis* · *Misinformation and Public Response* |

All organisations, people and events are fictional. BRIDGE is a **formative** learning tool, not a
high-stakes exam system.

## Run it in one step

You need **Python 3.12+** and **Node.js 20.9+**. No database server and no API key are needed.

**Windows:** double-click `start.cmd` (or run `powershell -ExecutionPolicy Bypass -File start.ps1`).

**macOS / Linux:**

```bash
./start.sh
```

The first run takes a few minutes (it installs dependencies, creates a local database with demo
data and builds the web app). Then open <http://localhost:3000> and sign in with a demo account
(password **`bridge-demo-2026`**):

| Role | Email |
|---|---|
| Student | `demo.student@example.com` |
| Professor | `demo.professor@example.com` |
| Administrator | `demo.admin@example.com` |

Press **Ctrl+C** to stop. Next starts take a few seconds.

> **Windows:** keep the folder at a short path such as `C:\bridge`. Very long paths break some
> Python/Node components on Windows.

**With Docker instead:** `cp .env.example .env`, edit the two secrets, then `docker compose up --build`
(PostgreSQL + API + web app). See [docs/SHARING.md](docs/SHARING.md).

## AI: offline by default, Claude optional

Out of the box BRIDGE uses a **deterministic mock AI** — free, offline, and clearly labelled in the
interface. Characters answer from scenario-authored lines, free-text messages are matched to
workplace actions by keywords, and assessments use a transparent keyword-and-evidence evaluator.

To use the real Claude API, set in `backend/.env`:

```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
```

then restart, and choose the provider in **Admin → AI and platform settings**. Usage limits and
cost budgets are enforced; if the API fails, BRIDGE falls back to labelled scripted replies.

## What's inside

- **Simulation engine** — deterministic state machine: variables, events, timed and conditional
  triggers, mutually exclusive decisions, difficulty levels, training vs assessment mode, an
  append-only event log, optimistic concurrency and idempotent requests.
- **AI characters** — isolated per-character contexts; restricted facts never reach the model until
  unlocked; AI can only *propose* an action, which the engine validates.
- **Assessment** — rubric criteria with performance levels; scores blend validated qualitative
  judgement with rule-based signals; evidence must reference real student actions; insufficient
  evidence is never counted as failure; weighted totals are computed by code.
- **Adaptive learning** — competency profile with confidence levels, explainable recommendations,
  approved course materials cited in feedback.
- **Professors** — courses, assignments, progress and common weaknesses, assessment review with
  audited corrections, scenario and rubric editors (versioned), resource uploads, CSV export.
- **Administrators** — users and roles, AI provider and limits, usage and cost, scenario
  publication, specializations, audit log.

## Documentation

| | |
|---|---|
| [docs/SHARING.md](docs/SHARING.md) | How to run it and send it to friends |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Guide for students, professors and administrators |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and decisions |
| [docs/API.md](docs/API.md) · [docs/DATABASE.md](docs/DATABASE.md) | API reference · schema and ERD |
| [docs/AI_DESIGN.md](docs/AI_DESIGN.md) | AI safety, validation and fallbacks |
| [docs/SECURITY.md](docs/SECURITY.md) | Security and privacy controls and limits |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy and actual results |
| [docs/EVALUATION.md](docs/EVALUATION.md) | Academic validation plan and measurement tools |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) | What is not done or not verified |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production hosting |
| [ROADMAP.md](ROADMAP.md) · [CHANGELOG.md](CHANGELOG.md) · [CLAUDE.md](CLAUDE.md) | Status · history · contributor/agent guide |

## Developing

```bash
# backend (from backend/)
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.lock && pip install --no-deps -e .
python -m app.cli setup                              # migrate + scenarios + demo data
uvicorn app.main:create_app --factory --reload       # http://localhost:8000/docs
pytest && ruff check . && ruff format --check .

# frontend (from frontend/)
npm ci && npm run dev                                # http://localhost:3000
npm run lint && npm run typecheck && npm run build
npm run test:e2e                                     # Playwright, starts its own servers
```
