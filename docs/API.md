# API

Base URL: `http://localhost:8000`. Versioned routes live under `/api/v1`. Interactive OpenAPI docs
at `/docs` in development (disabled in production). Authenticated routes need
`Authorization: Bearer <access token>`.

Errors use FastAPI's shape: `{"detail": "..."}` (or a list of validation errors for 422).
Unknown request fields are rejected with 422.

## Health
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Liveness. `{"status":"ok","version":"0.1.0"}` |
| GET | `/health/ready` | — | Readiness incl. database. 200 or 503 |

## Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/auth/config` | — | `{"provider":"local"\|"supabase","supabase_url":...}` |
| POST | `/api/v1/auth/register` | — (rate limited) | Local only. Body `{email, password (10–128), display_name}`. 201 → token response. Always creates a **student**. 409 if the email exists |
| POST | `/api/v1/auth/login` | — (rate limited) | Local only. Body `{email, password}`. 200 → token response; 401 with identical message for wrong password or unknown email |

Token response: `{"access_token", "token_type": "bearer", "expires_in": <seconds>, "user": User}`.
With `AUTH_PROVIDER=supabase`, register/login return 404: users sign in with Supabase and send the
Supabase access token; BRIDGE provisions a student account on first use.

Rate limit exceeded → 429 with `Retry-After`.

## Users
| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | `profile:read_own` | Current user, profile and effective permissions |
| PATCH | `/api/v1/users/me/profile` | `profile:update_own` | Body `{display_name?, specialization_code?}`. 422 for unknown specialization |

## Specializations
| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/specializations` | `specializations:read` | Active specializations, by name |

## Admin
| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/admin/users?limit&offset` | `users:read_all` | Paginated users (limit ≤ 200) |
| PATCH | `/api/v1/admin/users/{id}/role` | `users:manage_roles` | Body `{role}`. 409 when demoting yourself or the last admin. Audited |
| GET | `/api/v1/admin/audit-logs?action&limit` | `audit:read` | Most recent first (limit ≤ 500) |

## Permission matrix (Phase 1)
| Permission | student | professor | admin |
|---|:-:|:-:|:-:|
| `profile:read_own`, `profile:update_own`, `specializations:read` | ✔ | ✔ | ✔ |
| `users:read_all`, `users:manage_roles`, `audit:read` | | | ✔ |

Denied requests return 403 and are recorded in `audit_logs` with outcome `denied`.
