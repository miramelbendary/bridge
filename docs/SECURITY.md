# Security and privacy

## Controls in place
| Area | Implementation |
|---|---|
| Passwords | Argon2id; constant-work verification for unknown emails |
| Tokens | HS256 local JWT (iss/aud/exp/iat/jti required, 60 min) or Supabase JWT (HS256 secret or JWKS RS256/ES256); `alg: none` rejected |
| Authorization | Code-defined role permissions on every route; **ownership** (students only see their own sessions/assessments, others get 404); **course membership** limits professors; admins see all. Professors can view a student's workplace read-only but never act in it |
| Privilege escalation | Roles only from the database; registration creates students; unknown request fields rejected; admins cannot demote/deactivate themselves or remove the last admin |
| Authoritative state | Only the deterministic engine writes scenario state; AI output is validated (allowed intents, confidence, leak check); optimistic locking and idempotency keys prevent double application |
| Prompt injection | Student text delimited as data in prompts; never interpreted as instructions by code; injection-like text flags the assessment for professor review; assessment numbers are computed by code from validated levels and real evidence |
| Scenario content | YAML parsed with `safe_load`; conditions are a validated JSON language (no `eval`); Markdown rendered without raw HTML |
| Uploads | `.txt`/`.md` only, UTF-8, no NUL bytes, 2 MB limit, stored as text (no files on disk); professor-only visibility never reaches students |
| Rate limiting | Per-IP sliding window on register/login; AI usage limits per session/user/cost |
| Secrets | Environment variables only; API keys never in the database or API responses; `.env` git-ignored; production refuses default/short secrets and SQLite |
| Browser | Token in httpOnly SameSite=Lax cookie (Secure in production), used only by the Next.js server; security headers on API and frontend; CORS allow-list |
| Audit | Sign-ins (success/failure), denied access, role/activation changes, reviews, uploads, scenario saves/publication, settings |
| Privacy | Only email and display name collected; AI prompts contain no names/emails/ids; AI logs contain no prompts or student text |

## Known limitations (must be addressed before a real pilot)
- In-memory rate limiter (per process). Use a shared store for multi-instance deployments.
- No token revocation/refresh; deactivation takes effect immediately, but a copied token is valid ≤ 60 min.
- No email verification or password reset in local mode (use Supabase/university SSO for pilots).
- Registration reveals whether an email exists (409).
- No account-deletion/data-export endpoints yet; data retention policy not implemented.
- Frontend has no Content-Security-Policy header yet.
- Prompt-injection detection is pattern-based; it flags, it does not prove intent. The real protection
  is structural (AI cannot change state or compute scores).
- The Claude provider path is tested with stubs, not with a real key.
- No independent penetration test has been performed.
