import time
import logging
from collections import defaultdict
from django.http import JsonResponse

logger = logging.getLogger('gateway')

AUTH_SERVICE_URL = "http://auth-service:8000"

# Paths that don't require authentication
PUBLIC_PATHS = [
    '/',
    '/auth/login/',
    '/auth/register/',
    '/health/',
]


class LoggingMiddleware:
    """Logs all requests with method, path, status code, and duration."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start
        logger.info(
            "%s %s %s %.3fs [%s]",
            request.method,
            request.path,
            response.status_code,
            duration,
            request.META.get('REMOTE_ADDR', '-'),
        )
        return response


class RateLimitMiddleware:
    """Simple in-memory rate limiter: max 60 requests per minute per IP."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.requests = defaultdict(list)
        self.limit = 60
        self.window = 60  # seconds

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        now = time.time()
        self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window]

        if len(self.requests[ip]) >= self.limit:
            logger.warning("Rate limit exceeded for %s", ip)
            return JsonResponse({'error': 'Rate limit exceeded. Try again later.'}, status=429)

        self.requests[ip].append(now)
        return self.get_response(request)


class JWTAuthMiddleware:
    """Validates JWT token from session for protected routes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip auth for public paths and static files
        if any(request.path == p for p in PUBLIC_PATHS) or request.path.startswith('/static/'):
            return self.get_response(request)

        # Check session for token
        token = request.session.get('jwt_token')
        if not token:
            from django.shortcuts import redirect
            return redirect('/auth/login/')

        # Verify token via auth-service
        try:
            import requests as http_requests
            r = http_requests.post(
                f"{AUTH_SERVICE_URL}/auth/verify/",
                json={'token': token},
                timeout=3,
            )
            if r.status_code == 200:
                request.user_data = r.json().get('user', {})
            else:
                request.session.flush()
                from django.shortcuts import redirect
                return redirect('/auth/login/')
        except Exception:
            # If auth service is unavailable, allow request with warning
            request.user_data = request.session.get('user_data', {})
            logger.warning("Auth service unavailable, using cached user data")

        return self.get_response(request)
