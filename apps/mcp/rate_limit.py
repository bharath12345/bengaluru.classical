import time


class TokenBucket:
    """Token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def reset_time(self) -> float:
        tokens_needed = self.capacity - self.tokens
        seconds_needed = tokens_needed / self.refill_rate if self.refill_rate else 0
        return time.time() + seconds_needed


class RateLimiter:
    """Per-IP rate limiter using token buckets."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, TokenBucket] = {}

    def check(self, ip: str) -> tuple[bool, float]:
        if ip not in self.buckets:
            self.buckets[ip] = TokenBucket(self.capacity, self.refill_rate)

        bucket = self.buckets[ip]
        allowed = bucket.consume(1)
        return allowed, bucket.reset_time()


def get_client_ip(scope: dict) -> str:
    headers = dict(scope.get("headers", []))
    forwarded_for = headers.get(b"x-forwarded-for", b"").decode("utf-8")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    client = scope.get("client")
    if client:
        return client[0]

    return "unknown"
