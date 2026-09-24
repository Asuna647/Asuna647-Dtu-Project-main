from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.security_validator import SecurityValidator

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, validator: SecurityValidator):
        super().__init__(app)
        self.validator = validator

    async def dispatch(self, request: Request, call_next):
        # Skip health check or other public endpoints if necessary
        if request.url.path == "/":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, msg = self.validator.rate_limit_check(client_ip)
        if not allowed:
            return HTTPException(status_code=429, detail=msg)

        response = await call_next(request)
        return response
