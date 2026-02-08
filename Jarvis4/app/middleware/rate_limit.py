import os
import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    import redis  # type: ignore
except Exception:
    redis = None

# NOTE:
# - In-memory limiter is OK for single instance (dev).
# - For production / multiple replicas: use gateway rate limiting OR Redis backend below.

RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "120"))      # sustained req/min
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "30"))   # extra within window
WINDOW_SEC = 60

BACKEND = os.getenv("RATE_LIMIT_BACKEND", "memory").lower()   # memory | redis
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._buckets = defaultdict(deque)  # memory backend
        self._redis = None
        if BACKEND == "redis":
            if redis is None:
                raise RuntimeError("redis backend requested but 'redis' package is not installed")
            self._redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    def _key(self, request: Request) -> str:
        actor = getattr(request.state, "actor", None)
        if actor and getattr(actor, "subject", None):
            return f"sub:{actor.subject}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    def _deny(self, request: Request):
        request_id = getattr(request.state, "request_id", None)
        trace_id = getattr(request.state, "trace_id", None)
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "rate_limited",
                "message": "Too many requests",
                "details": {"limit_per_minute": RATE_LIMIT_RPM, "burst": RATE_LIMIT_BURST, "backend": BACKEND},
                "request_id": request_id,
                "trace_id": trace_id,
            },
            headers={"Retry-After": "10"},
        )

    async def dispatch(self, request: Request, call_next):
        key = self._key(request)
        now = time.time()
        limit = RATE_LIMIT_RPM + RATE_LIMIT_BURST

        if BACKEND == "redis":
            # Fixed window counter keyed by minute bucket.
            # Key example: rl:<key>:<epoch_minute>
            epoch_minute = int(now // WINDOW_SEC)
            rk = f"rl:{key}:{epoch_minute}"
            try:
                # INCR + EXPIRE (atomic-ish enough for this MVP)
                cnt = self._redis.incr(rk)  # type: ignore[union-attr]
                if cnt == 1:
                    self._redis.expire(rk, WINDOW_SEC + 2)  # type: ignore[union-attr]
                if cnt > limit:
                    return self._deny(request)
            except Exception:
                # Fail-open or fail-closed? Enterprise usually prefers fail-open for availability.
                # Here we fail-open but you can switch to deny.
                pass
            return await call_next(request)

        # Memory backend
        q = self._buckets[key]
        while q and (now - q[0]) > WINDOW_SEC:
            q.popleft()
        if len(q) >= limit:
            return self._deny(request)
        q.append(now)
        return await call_next(request)
