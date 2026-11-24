"""Small in-memory sliding-window rate limiter.

Limitation (documented in SECURITY.md): state is per process. With several backend instances,
replace this with a shared store (e.g. Redis or a PostgreSQL table) behind the same interface.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> tuple[bool, int]:
        """Record an attempt. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_attempts:
                return False, max(1, int(self.window_seconds - (now - hits[0])) + 1)
            hits.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request) -> str:
    # Behind a reverse proxy, configure uvicorn --proxy-headers / --forwarded-allow-ips so that
    # request.client reflects the real client. Never trust X-Forwarded-For directly here.
    return request.client.host if request.client else "unknown"


def auth_rate_limit(request: Request) -> None:
    limiter: SlidingWindowRateLimiter = request.app.state.auth_rate_limiter
    allowed, retry_after = limiter.hit(f"{request.url.path}:{client_ip(request)}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
