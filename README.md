# BRIDGE

**BRIDGE: An AI-Powered Adaptive Workplace Simulation and Competency Assessment Platform for
University Students.**

BRIDGE lets students enter simulated workplaces (International Trade, Translation, INFOCOM),
interact with AI-powered colleagues and clients, make decisions with real consequences, and receive
rubric-based, evidence-backed formative feedback.

> **Status: Phase 1 (foundations) complete.** Authentication, authorization, database, migrations,
> CI and documentation are in place. There are **no simulations, AI features or assessments yet**;
> see [ROADMAP.md](ROADMAP.md).

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI API, SQLAlchemy models, Alembic migrations, pytest suite |
| `backend/app/{api,models,schemas,services,security}` | Implemented in Phase 1 |
| `backend/app/{simulation,ai,assessment,recommendations,knowledge}` | Reserved for later phases |
| `frontend/` | Next.js 16 (App Router, TypeScript, Tailwind CSS 4) |
| `scenarios/` | Versioned scenario configurations (from Phase 3) |
| `infrastructure/` | Docker Compose for local PostgreSQL + API |
| `scripts/` | Developer helper scripts |
| `docs/` | Architecture, database, API, security, testing, limitations, deployment |

## Quick start

Requirements: Python 3.12+ (3.14 verified), Node.js 20.9+ (24 verified), PostgreSQL 17 (or Docker).

### 1. Database

With Docker:

```bash
cp .env.example .env    # edit the secrets
docker compose -f infrastructure/docker-compose.yml --env-file .env up --build
```

This starts PostgreSQL and the API on <http://localhost:8000> (migrations run automatically).
Without Docker, point `DATABASE_URL` at any PostgreSQL 17 instance.

### 2. Backend (without Docker)

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.lock
pip install --no-deps -e .
cp .env.example .env            # set DATABASE_URL and LOCAL_JWT_SECRET
alembic upgrade head
python -m app.cli create-user --email admin@bridge.example.org --display-name "Admin" --role admin
uvicorn app.main:create_app --factory --reload
```

API docs (development only): <http://localhost:8000/docs>

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open <http://localhost:3000>, create a student account, and you will land on the dashboard, which
loads your profile and the specializations from the API.

### Checks

```bash
scripts/check.sh
```

> **Windows note:** keep the repository at a short path (for example `C:\dev\bridge`). Very long
> paths exceed the Windows 260-character limit and break loading compiled Python/Node extensions.

## Documentation

- [ROADMAP.md](ROADMAP.md) · [CHANGELOG.md](CHANGELOG.md) · [CLAUDE.md](CLAUDE.md) (AI agent guide)
- [Architecture](docs/ARCHITECTURE.md) · [Requirements](docs/REQUIREMENTS.md) ·
  [Database](docs/DATABASE.md) · [API](docs/API.md) · [AI design](docs/AI_DESIGN.md)
- [Security](docs/SECURITY.md) · [Testing](docs/TESTING.md) · [Limitations](docs/LIMITATIONS.md) ·
  [Deployment](docs/DEPLOYMENT.md)
