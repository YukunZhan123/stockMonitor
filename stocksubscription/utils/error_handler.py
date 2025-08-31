"""
Simple error handling utilities for Django backend
"""

import logging
from functools import wraps
from django.conf import settings
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """Extract client IP address with proxy support"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'Unknown')
    return ip


def handle_view_errors(view_func):
    """Simple decorator for view error handling"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in view {view_func.__name__}: {str(e)}")
            
            # Return user-friendly error response
            if settings.DEBUG:
                error_message = str(e)
            else:
                error_message = "An error occurred. Please try again."
            
            return Response({
                'error': error_message
            }, status=500)
    
    return wrapper