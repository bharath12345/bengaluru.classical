from datetime import datetime, timedelta

from django.core.cache import cache


def check_rate_limit(request) -> bool:
    """
    Simple IP-based rate limiter: max 3 submissions per hour.
    Returns True if allowed, False if rate-limited.
    """
    ip = _get_client_ip(request)
    cache_key = f"submit_rate:{ip}"
    submissions = cache.get(cache_key, [])
    now = datetime.now()
    recent = [ts for ts in submissions if now - ts < timedelta(hours=1)]
    if len(recent) >= 3:
        return False
    recent.append(now)
    cache.set(cache_key, recent, timeout=3600)
    return True


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
