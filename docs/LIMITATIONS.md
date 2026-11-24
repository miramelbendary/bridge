# Limitations and open issues

Honest record of what BRIDGE does **not** do yet, and what has not been verified.

## Product scope (as of Phase 1)
- No simulations, scenarios, AI characters, assessments, reports, competency tracking or
  recommendations exist yet. The platform currently provides accounts, roles, specializations and
  the technical foundation only.
- Professors currently have the same permissions as students; their tools arrive in Phases 5 and 9.
- No educational-effectiveness claims can be made. The targets in the project brief (completion
  rate, satisfaction, grading error, latency) are development targets, not results. No pilot study
  has been run.

## Verification gaps
- **PostgreSQL was not available on the Phase 1 development machine.** Tests and migrations were
  run on SQLite locally; the PostgreSQL DDL was rendered offline. Execution on PostgreSQL happens in
  CI, which has not yet run because the repository has not been pushed to GitHub.
- **Docker was not available.** The Dockerfile and Compose file are written but have not been built
  or started.
- **No Supabase project credentials.** Backend verification of Supabase tokens is implemented and
  tested with locally minted tokens. The frontend supports only local email/password sign-in;
  Supabase sign-in on the frontend is planned for Phase 2.
- Frontend behaviour was verified manually; no automated end-to-end tests yet (Phase 2).

## Security limitations
See `SECURITY.md` → "Known limitations": in-memory rate limiting, no token revocation/refresh,
no email verification or password reset in local mode, registration reveals existing emails.

## Before any real university pilot
- Privacy impact assessment and approval (ethics/data protection) by the university.
- Data retention and deletion controls (account deletion, export) — not implemented yet.
- Use Supabase Auth (or the university's identity provider) instead of local accounts.
- Independent security review.
- Subject-specialist review of every scenario's professional facts and rubrics.

## Environment notes
- Windows: very long repository paths exceed the 260-character limit and break loading compiled
  Python/Node extensions. Keep the repository at a short path.
- The lock files were produced on Windows with Python 3.14. Linux-only optional extras (e.g.
  `uvloop` from `uvicorn[standard]`) are not pinned and are simply not installed.
