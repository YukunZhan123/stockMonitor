"""
Custom CSRF protection for JWT-only authentication with cross-origin support.

This module provides lightweight CSRF protection that works with:
- Cross-origin deployments (frontend and backend on different domains)
- SameSite=None cookies (required for cross-origin)
- No Django CSRF middleware dependency

How it works:
1. Custom header verification (X-Requested-With)
2. Origin header validation  
3. Referer header validation as fallback
"""

import logging
from django.conf import settings
from django.http import JsonResponse
from urllib.parse import urlparse

logger = logging.getLogger('authentication')


def validate_csrf_headers(request):
    """
    Lightweight CSRF protection using HTTP headers.
    
    Returns:
        True if request passes CSRF checks
        False if request fails CSRF checks
    """
    # Skip CSRF for GET, HEAD, OPTIONS, TRACE (safe methods)
    if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
        return True
    
    # Check 1: Custom header (prevents simple form CSRF)
    custom_header = request.headers.get('X-Requested-With')
    if custom_header != 'XMLHttpRequest':
        logger.warning(f"CSRF: Missing X-Requested-With header from {request.META.get('REMOTE_ADDR')}")
        return False
    
    # Check 2: Origin header validation
    origin = request.headers.get('Origin')
    if origin:
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        if settings.DEBUG:
            # Allow localhost in development
            allowed_origins.extend([
                'http://localhost:3000',
                'http://localhost:5176',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:5176'
            ])
        
        if origin not in allowed_origins:
            logger.warning(f"CSRF: Invalid origin {origin} from {request.META.get('REMOTE_ADDR')}")
            return False
    
    # Check 3: Referer validation as fallback
    elif request.headers.get('Referer'):
        referer = request.headers.get('Referer')
        referer_domain = urlparse(referer).netloc
        
        allowed_domains = []
        for origin in getattr(settings, 'CORS_ALLOWED_ORIGINS', []):
            allowed_domains.append(urlparse(origin).netloc)
        
        if settings.DEBUG:
            allowed_domains.extend(['localhost:3000', 'localhost:5173', '127.0.0.1:3000'])
        
        if referer_domain not in allowed_domains:
            logger.warning(f"CSRF: Invalid referer {referer} from {request.META.get('REMOTE_ADDR')}")
            return False
    
    return True


class CSRFProtectionMiddleware:
    """
    Lightweight CSRF protection middleware for JWT-only authentication.
    
    This replaces Django's CSRF middleware with a simpler approach
    suitable for API-only applications with cross-origin requirements.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip CSRF for specific GET endpoints that don't need protection
        skip_paths = [
            '/api/auth/verify/',  # GET endpoint for checking auth status
            '/api/auth/refresh/', # POST but uses existing auth cookie
        ]
        
        # Only skip CSRF check for specific safe endpoints
        should_skip = any(request.path.startswith(path) for path in skip_paths)
        
        if not should_skip:
            if not validate_csrf_headers(request):
                return JsonResponse(
                    {'error': 'CSRF validation failed'}, 
                    status=403
                )
        
        response = self.get_response(request)
        return response