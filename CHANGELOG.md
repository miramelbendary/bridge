# Changelog

All notable changes to BRIDGE. Format based on [Keep a Changelog](https://keepachangelog.com/);
versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-11-25 — Phase 1: Project foundations

### Added
- FastAPI backend as a modular monolith with an application factory (`create_app`).
- Settings via environment variables with security validation (secret length, no default secret
  or SQLite in production, no wildcard CORS).
- SQLAlchemy 2 models: `users`, `user_profiles`, `specializations`, `audit_logs`.
- Alembic migration `0001_foundations`, seeding Translation, International Trade and INFOCOM.
- Authentication: local provider (Argon2id passwords, HS256 JWT) and Supabase JWT verification
  (HS256 legacy secret or JWKS for RS256/ES256), with just-in-time provisioning of Supabase users.
- Role-based access control (student, professor, admin) enforced server-side; denied attempts audited.
- Endpoints: health/readiness, auth config/register/login, current user, profile update,
  specializations, admin user list, admin role change, admin audit log.
- Per-IP rate limiting on authentication endpoints; security headers; generic 500 handler.
- `python -m app.cli create-user` for creating the first administrator.
- 42 pytest tests (auth, token tampering, RBAC, config validation, migrations ↔ models sync).
- Next.js 16 frontend: landing, sign in, register, dashboard backed by the API; token held in an
  httpOnly cookie and used only by the Next.js server.
- Docker Compose (PostgreSQL 17 + pgvector, API), backend Dockerfile, GitHub Actions CI.
- Documentation set in `docs/` plus README, ROADMAP, CLAUDE.md.
