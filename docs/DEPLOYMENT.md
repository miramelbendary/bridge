# Deployment

> Local runs are verified (`start.ps1`). Docker and cloud hosting below are prepared but were not
> executed during development.

## Local
See README / SHARING.md: `start.cmd` (Windows) or `./start.sh`.

## Docker Compose (single machine)
`cp .env.example .env` → set secrets → `docker compose up --build`. Services: `db` (PostgreSQL 17,
pgvector image), `backend` (runs migrations, scenario sync and — outside production — demo data),
`frontend`. Ports are bound to 127.0.0.1; put a TLS reverse proxy in front for any non-local use.

## Production topology
| Component | Suggested host | Settings |
|---|---|---|
| Frontend | Vercel (root `frontend/`) | `BRIDGE_API_URL=https://api.example.edu` (server-only). Do not set `BRIDGE_DEMO_MODE`. |
| Backend | Container host (Render, Fly.io, Railway, university VM) using `backend/Dockerfile` with the repo root as build context | see below |
| Database | Managed PostgreSQL 17 with automated backups / point-in-time recovery | |
| Auth | Supabase Auth or university SSO | `AUTH_PROVIDER=supabase`, `SUPABASE_URL` |

Backend environment for production:
```
ENVIRONMENT=production            # HSTS on, API docs off, demo seeding refused, strict checks
DATABASE_URL=postgresql+psycopg://...
LOCAL_JWT_SECRET=<48+ random chars>   # only if AUTH_PROVIDER=local
CORS_ORIGINS=https://bridge.example.edu
AI_PROVIDER=anthropic              # optional
ANTHROPIC_API_KEY=<from the host's secret manager>
FORWARDED_ALLOW_IPS=<reverse proxy address>
```
Create the first administrator: `python -m app.cli create-user --role admin --email ... --display-name ...`
(password read from `BRIDGE_NEW_USER_PASSWORD` or prompted).

## Release checklist
1. CI green (backend on PostgreSQL, frontend build, e2e).
2. Backup the database; run `alembic upgrade head` against a staging copy first.
3. Deploy backend; check `/health/ready`. Deploy frontend; smoke-test sign-in and one scenario.
4. `python -m app.cli sync-scenarios` after changing scenario files (also run at container start).
5. Review `/admin` usage and audit log after launch.
