# Security and privacy

## Implemented in Phase 1
| Control | Implementation |
|---|---|
| Password storage | Argon2id (`argon2-cffi` defaults); constant-work verification even for unknown emails |
| Tokens | HS256 JWT (local) with `iss`, `aud`, `exp`, `iat`, `jti` required; 60 min default lifetime. Supabase tokens: HS256 secret or JWKS (RS256/ES256), audience and issuer checked; `alg: none` and unexpected algorithms rejected |
| Authorization | Code-defined role→permission map; `require_permission` dependency on every protected route; unknown roles get no permissions (fail closed) |
| Privilege escalation | Role never read from token claims; registration always creates students; extra request fields rejected (`extra="forbid"`); admins cannot demote themselves or the last admin |
| Account takeover | A Supabase identity is never auto-linked to an existing local account with the same email (403) |
| Enumeration | Login returns the same 401 for wrong password and unknown email |
| Brute force | Per-IP, per-endpoint sliding-window limit on register/login (10/min default) → 429 |
| Audit | Register, login success/failure, permission denials, role changes, CLI user creation. Passwords/tokens are stripped from `details`; failed-login emails are not recorded |
| Secrets | Environment variables only; `.env` git-ignored; production refuses the default JWT secret, short secrets and SQLite |
| Transport/browser | Security headers (nosniff, `X-Frame-Options: DENY`, `no-referrer`, restrictive CSP on API responses, `no-store`); HSTS in production; CORS allow-list (wildcard rejected) |
| Session in browser | Token in an httpOnly, `SameSite=Lax`, `Secure` (production) cookie, readable only by the Next.js server |
| Injection | SQLAlchemy parameterised queries only; React escapes output; no raw HTML rendering |
| Errors | Generic 500 body; details only in server logs. API docs disabled in production |
| Containers | Backend image runs as a non-root user; Compose binds ports to 127.0.0.1 |

## Known limitations / accepted risks (Phase 1)
- **Rate limiter is in-memory per process.** With several instances or restarts it is weaker.
  Replace with a shared store before multi-instance deployment.
- **No token revocation or refresh.** A stolen token stays valid until expiry (≤ 60 min default);
  deactivating a user does take effect immediately because each request reloads the user.
- **Registration reveals whether an email exists (409).** Accepted for usability; mitigated by
  rate limiting. Revisit when email verification is added.
- **No email verification or password reset** in local mode. Local mode is meant for development
  and demos; Supabase Auth provides these for real pilots.
- **Client IP** comes from the ASGI connection. Behind a proxy, configure `--proxy-headers` and
  `--forwarded-allow-ips` (the Dockerfile does) or all clients share one rate-limit bucket.
- **Server Actions CSRF** relies on Next.js's built-in Origin checks for Server Actions plus
  `SameSite=Lax` cookies. Not independently penetration-tested.
- **No CSP on the frontend yet** (security headers only). To add with the Phase 2 design system.
- **Supabase verification is tested only with locally minted tokens**; no real Supabase project
  was available.

## Privacy principles
- Collect only email and display name; no other personal data.
- Never send identifying student data to AI providers (from Phase 4).
- Students must never see other students' data; professors only their authorized students
  (ownership checks arrive with the resources they protect, Phase 3+).
- Data retention and deletion controls and a privacy review are required **before any real
  university pilot** (tracked in LIMITATIONS.md).

## Reporting
Report suspected vulnerabilities privately to the project maintainers; do not open public issues.
