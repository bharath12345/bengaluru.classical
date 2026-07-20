import time

from apps.mcp.rate_limit import RateLimiter, TokenBucket, get_client_ip


def test_token_bucket_allows_within_capacity():
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    assert bucket.consume(5) is True
    assert bucket.consume(5) is True
    assert bucket.consume(1) is False


def test_token_bucket_refills_over_time():
    bucket = TokenBucket(capacity=10, refill_rate=10.0)
    bucket.consume(10)
    time.sleep(0.5)
    assert bucket.consume(5) is True
    assert bucket.consume(1) is False


def test_token_bucket_reset_time():
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    bucket.consume(10)
    reset = bucket.reset_time()
    assert reset > time.time()


def test_get_client_ip_from_x_forwarded_for():
    scope = {"headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")]}
    ip = get_client_ip(scope)
    assert ip == "1.2.3.4"


def test_get_client_ip_from_client():
    scope = {"client": ("9.8.7.6", 12345)}
    ip = get_client_ip(scope)
    assert ip == "9.8.7.6"


def test_get_client_ip_unknown():
    scope = {}
    ip = get_client_ip(scope)
    assert ip == "unknown"


def test_rate_limiter_allows_within_limit():
    limiter = RateLimiter(capacity=10, refill_rate=1.0)
    allowed, _ = limiter.check("1.2.3.4")
    assert allowed is True


def test_rate_limiter_blocks_over_limit():
    limiter = RateLimiter(capacity=2, refill_rate=1.0)
    limiter.check("1.2.3.4")
    limiter.check("1.2.3.4")
    allowed, reset = limiter.check("1.2.3.4")
    assert allowed is False
    assert reset > time.time()


def test_rate_limiter_per_ip_isolation():
    limiter = RateLimiter(capacity=1, refill_rate=1.0)
    limiter.check("1.2.3.4")
    allowed, _ = limiter.check("5.6.7.8")
    assert allowed is True
