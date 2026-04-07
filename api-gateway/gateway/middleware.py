import re
import time
import logging
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger('gateway')

AUTH_SERVICE_URL = "http://auth-service:8000"

# Paths that don't require authentication
PUBLIC_PATHS = [
    '/',
    '/auth/login/',
    '/auth/register/',
    '/auth/logout/',
    '/health/',
]

# Role-based access control: maps (resource, action) to allowed roles
# Actions: 'list', 'create', 'edit', 'delete'
# If a path is not matched, any authenticated user is allowed
ROLE_PERMISSIONS = {
    # Books
    ('books', 'create'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('books', 'edit'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('books', 'delete'): ['STAFF', 'MANAGER', 'ADMIN'],
    # Customers
    ('customers', 'list'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('customers', 'register'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('customers', 'edit'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('customers', 'delete'): ['MANAGER', 'ADMIN'],
    # Staff
    ('staff', 'list'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('staff', 'create'): ['MANAGER', 'ADMIN'],
    ('staff', 'edit'): ['MANAGER', 'ADMIN'],
    ('staff', 'delete'): ['ADMIN'],
    # Managers
    ('managers', 'list'): ['MANAGER', 'ADMIN'],
    ('managers', 'create'): ['ADMIN'],
    ('managers', 'edit'): ['ADMIN'],
    ('managers', 'delete'): ['ADMIN'],
    # Categories
    ('categories', 'create'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('categories', 'edit'): ['STAFF', 'MANAGER', 'ADMIN'],
    ('categories', 'delete'): ['MANAGER', 'ADMIN'],
}

# Regex patterns to extract resource and action from URL paths
# Matches: /resource/create/, /resource/<id>/edit/, /resource/<id>/delete/,
#          /resource/register/, /resource/
PATH_PATTERNS = [
    re.compile(r'^/(?P<resource>\w+)/(?P<action>create|register)/$'),
    re.compile(r'^/(?P<resource>\w+)/\d+/(?P<action>edit|delete)/$'),
    re.compile(r'^/(?P<resource>\w+)/$'),
]


def _get_permission_key(path):
    """Extract (resource, action) from a URL path for permission checking."""
    for pattern in PATH_PATTERNS:
        match = pattern.match(path)
        if match:
            resource = match.group('resource')
            action = match.groupdict().get('action', 'list')
            return (resource, action)
    return None


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
    """Redis-backed rate limiter: max 60 requests per minute per IP."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = 60
        self.window = 60  # seconds

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        cache_key = f'ratelimit:{ip}'
        now = time.time()

        try:
            request_log = cache.get(cache_key, [])
            request_log = [t for t in request_log if now - t < self.window]

            if len(request_log) >= self.limit:
                logger.warning("Rate limit exceeded for %s", ip)
                return JsonResponse({'error': 'Rate limit exceeded. Try again later.'}, status=429)

            request_log.append(now)
            cache.set(cache_key, request_log, self.window)
        except Exception:
            # If Redis is unavailable, allow request through
            logger.warning("Redis unavailable for rate limiting, allowing request")

        return self.get_response(request)


class JWTAuthMiddleware:
    """Validates JWT token from session and enforces role-based access control.
    Caches verified tokens in Redis to reduce auth-service load."""

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

        # Check Redis cache for verified token
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        cache_key = f'jwt:{token_hash}'

        try:
            cached_user = cache.get(cache_key)
            if cached_user:
                request.user_data = cached_user
                # Skip to RBAC check
                return self._check_rbac(request)
        except Exception:
            pass

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
                # Cache verified token in Redis (TTL 5 minutes)
                try:
                    cache.set(cache_key, request.user_data, 300)
                except Exception:
                    pass
            else:
                request.session.flush()
                from django.shortcuts import redirect
                return redirect('/auth/login/')
        except Exception:
            # If auth service is unavailable, allow request with warning
            request.user_data = request.session.get('user_data', {})
            logger.warning("Auth service unavailable, using cached user data")

        return self._check_rbac(request)

    def _check_rbac(self, request):
        """Role-based access control check."""
        user_role = getattr(request, 'user_data', {}).get('role', '')
        perm_key = _get_permission_key(request.path)
        if perm_key and perm_key in ROLE_PERMISSIONS:
            allowed_roles = ROLE_PERMISSIONS[perm_key]
            if user_role not in allowed_roles:
                from django.shortcuts import render
                return render(request, 'forbidden.html', status=403)

        return self.get_response(request)
