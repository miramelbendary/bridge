import "server-only";

import { cookies } from "next/headers";

/**
 * The backend access token is kept in an httpOnly cookie on the frontend's own domain.
 * Browser JavaScript can never read it (XSS cannot steal it), and it is only ever sent to the
 * BRIDGE API from the Next.js server.
 */
const COOKIE_NAME = "bridge_session";

export async function getSessionToken(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE_NAME)?.value;
}

export async function setSessionToken(token: string, maxAgeSeconds: number): Promise<void> {
  (await cookies()).set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: maxAgeSeconds,
  });
}

export async function clearSessionToken(): Promise<void> {
  (await cookies()).delete(COOKIE_NAME);
}
