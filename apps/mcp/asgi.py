"""ASGI composition: Django + FastMCP under /mcp with rate limiting."""

from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount

from apps.mcp.rate_limit import RateLimiter, get_client_ip
from apps.mcp.server import mcp

# Default: 60 requests / minute per IP
_rate_limiter = RateLimiter(capacity=60, refill_rate=1.0)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = get_client_ip(request.scope)
        allowed, reset = _rate_limiter.check(ip)
        if not allowed:
            return JSONResponse(
                {"error": "rate_limit_exceeded"},
                status_code=429,
                headers={"Retry-After": str(max(1, int(reset - __import__("time").time())))},
            )
        response = await call_next(request)
        return response


def get_mcp_asgi_app():
    """Return the FastMCP ASGI app, adapting to FastMCP API variants."""
    if hasattr(mcp, "http_app"):
        return mcp.http_app()
    if hasattr(mcp, "get_asgi_app"):
        return mcp.get_asgi_app()
    # Fallback: streamable HTTP app attribute
    return getattr(mcp, "app", mcp)


def build_asgi_application(django_asgi):
    """Mount MCP under /mcp alongside the Django ASGI app."""
    mcp_app = get_mcp_asgi_app()
    app = Starlette(
        routes=[
            Mount("/mcp", app=mcp_app),
            Mount("/", app=django_asgi),
        ]
    )
    app.add_middleware(RateLimitMiddleware)
    return app
