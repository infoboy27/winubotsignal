"""Rate limiting middleware for FastAPI."""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        # Store: {ip: [(timestamp, minute_bucket), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for forwarded IP (when behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self, client_ip: str, current_time: float):
        """Remove requests older than 1 hour."""
        hour_ago = current_time - 3600
        self.request_history[client_ip] = [
            (ts, bucket) for ts, bucket in self.request_history[client_ip]
            if ts > hour_ago
        ]
    
    def _check_rate_limit(self, client_ip: str, current_time: float) -> Tuple[bool, str]:
        """
        Check if request should be rate limited.
        Returns (is_allowed, error_message)
        """
        # Clean up old requests
        self._cleanup_old_requests(client_ip, current_time)
        
        # Get requests in the last minute
        minute_ago = current_time - 60
        minute_requests = sum(1 for ts, _ in self.request_history[client_ip] if ts > minute_ago)
        
        # Check minute limit
        if minute_requests >= self.requests_per_minute:
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Get requests in the last hour
        hour_requests = len(self.request_history[client_ip])
        
        # Check hour limit
        if hour_requests >= self.requests_per_hour:
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        return True, ""
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and apply rate limiting."""
        
        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        current_minute = int(current_time / 60)
        
        # Check rate limit
        is_allowed, error_message = self._check_rate_limit(client_ip, current_time)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_message,
                headers={"Retry-After": "60"}
            )
        
        # Record this request
        self.request_history[client_ip].append((current_time, current_minute))
        
        # Add rate limit headers to response
        response: Response = await call_next(request)
        
        minute_ago = current_time - 60
        minute_requests = sum(1 for ts, _ in self.request_history[client_ip] if ts > minute_ago)
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, self.requests_per_minute - minute_requests))
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, self.requests_per_hour - len(self.request_history[client_ip])))
        
        return response



