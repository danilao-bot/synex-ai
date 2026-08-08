"""In-memory token bucket rate limiter middleware for public endpoints."""

import time
import logging
from typing import Dict, Tuple
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenBucketLimiter:
    """A thread-safe in-memory token bucket rate limiter."""

    def __init__(self, rate: int, capacity: int):
        self.rate = rate  # Tokens refilled per minute
        self.capacity = capacity  # Maximum bucket capacity
        # ip -> (tokens, last_update_time)
        self.buckets: Dict[str, Tuple[float, float]] = {}

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        """Check if request from client_ip is allowed under rate limits.
        
        Returns:
            (is_allowed, retry_after_seconds)
        """
        now = time.time()
        if client_ip not in self.buckets:
            self.buckets[client_ip] = (float(self.capacity), now)
            return True, 0

        tokens, last_update = self.buckets[client_ip]
        # Calculate tokens refilled since last request
        elapsed = now - last_update
        refill = elapsed * (self.rate / 60.0)
        
        new_tokens = min(tokens + refill, float(self.capacity))
        
        if new_tokens >= 1.0:
            self.buckets[client_ip] = (new_tokens - 1.0, now)
            return True, 0
        else:
            self.buckets[client_ip] = (new_tokens, now)
            # Calculate remaining time until at least 1.0 token is available
            needed = 1.0 - new_tokens
            retry_after = int(needed / (self.rate / 60.0))
            return False, max(retry_after, 1)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI rate limiting middleware enforcing IP-based requests limits."""

    def __init__(self, app, rate: int = None, capacity: int = None):
        super().__init__(app)
        self.rate = rate or settings.RATE_LIMIT_RPM
        self.capacity = capacity or settings.RATE_LIMIT_RPM
        self.limiter = TokenBucketLimiter(self.rate, self.capacity)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exclude health check from rate limiting to prevent dashboard check alerts
        if request.url.path in ("/health", "/api/v1/health"):
            return await call_next(request)

        # Retrieve client IP
        client_host = request.client.host if request.client else "unknown"
        # Support common cloud forward headers
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else client_host

        allowed, retry_after = self.limiter.is_allowed(client_ip)
        if not allowed:
            logger.warning("Rate limit exceeded for IP '%s' on path '%s'", client_ip, request.url.path)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
