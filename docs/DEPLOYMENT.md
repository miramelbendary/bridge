# Deployment

> Phase 1 provides local development and CI only. Production hosting is configured in Phase 11.
> Nothing below has been deployed yet.

## Local stack
See README → Quick start. Docker Compose (`infrastructure/docker-compose.yml`) runs PostgreSQL 17
(pgvector image) and the API; the frontend runs with `npm run dev`.

## Target production topology
| Component | Target | Notes |
|---|---|---|
| Frontend | Vercel | Set `BRIDGE_API_URL` (server-only) to the API's public URL |
| Backend | Any container host (e.g. Render, Fly.io, Railway, a university VM) | Image from `backend/Dockerfile`; runs `alembic upgrade head` at start |
| Database | Managed PostgreSQL 17 (e.g. Supabase Postgres) | Enable automated backups and point-in-time recovery |
| Auth | Supabase Auth | `AUTH_PROVIDER=supabase`, `SUPABASE_URL` (+ `SUPABASE_JWT_SECRET` for legacy HS256 projects) |

## Required production environment (backend)
| Variable | Notes |
|---|---|
| `ENVIRONMENT=production` | Enables HSTS, disables API docs, enforces strict validation |
| `DATABASE_URL` | `postgresql+psycopg://…` (SQLite is rejected) |
| `AUTH_PROVIDER` | `supabase` recommended for pilots |
| `LOCAL_JWT_SECRET` | Only for `local`; ≥ 32 random characters; default value is rejected |
| `CORS_ORIGINS` | Exact frontend origin(s); `*` is rejected |
| `FORWARDED_ALLOW_IPS` | Address of the reverse proxy, so client IPs (rate limiting, audit) are correct |

Store secrets in the host's secret manager, never in the repository or image.

## Release checklist (to be completed in Phase 11)
1. CI green on `main`.
2. Database backup taken; `alembic upgrade head` tested against a staging copy.
3. Deploy backend; check `/health/ready`.
4. Deploy frontend; smoke-test sign-in and dashboard.
5. Create administrator via `python -m app.cli create-user --role admin` (local auth) or promote a
   Supabase-provisioned user through the admin API.
