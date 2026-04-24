from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import re
from typing import Dict
from collections import defaultdict


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for input sanitization and attack prevention"""

    def __init__(self, app, rate_limit_requests: int = 100, rate_limit_window: int = 60):
        super().__init__(app)
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        self.request_counts: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Rate limiting
        client_ip = self._get_client_ip(request)
        current_time = time.time()

        # Clean old requests
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if current_time - timestamp < self.rate_limit_window
        ]

        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please try again later."}
            )

        self.request_counts[client_ip].append(current_time)

        # Input validation for common attack patterns
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_body(request)

        # Add security headers
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client
        client_host = request.client.host if request.client else "unknown"
        return client_host

    async def _validate_request_body(self, request: Request):
        """Validate request body for malicious content"""
        try:
            # Read body without consuming it
            body = await request.body()

            if not body:
                return

            body_str = body.decode("utf-8", errors="ignore")

            # Check for common attack patterns
            dangerous_patterns = [
                r'<script[^>]*>.*?</script>',  # Script injection
                r'javascript:',                 # JavaScript URLs
                r'vbscript:',                   # VBScript
                r'data:text/html',             # Data URLs
                r'on\w+\s*=',                   # Event handlers
                r'union\s+select',             # SQL injection
                r';\s*drop\s+table',           # SQL injection
                r'--',                         # SQL comments
                r'/\*\*/',                     # SQL comments
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, body_str, re.IGNORECASE | re.DOTALL):
                    raise HTTPException(
                        status_code=400,
                        detail="Request contains potentially malicious content"
                    )

            # Check for excessive nesting (potential DoS)
            if body_str.count("{") > 50 or body_str.count("[") > 50:
                raise HTTPException(
                    status_code=400,
                    detail="Request payload too complex"
                )

        except UnicodeDecodeError:
            # Binary data, skip validation
            pass
        except HTTPException:
            raise
        except Exception:
            # If validation fails for any reason, allow request to proceed
            # (fail-open for legitimate requests)
            pass