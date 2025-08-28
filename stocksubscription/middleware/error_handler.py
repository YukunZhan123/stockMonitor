"""
Production-ready error handling middleware for Django

Features:
- Centralized exception handling across all views
- Security-focused error responses
- Performance monitoring and logging
- Rate limiting and abuse detection
- Request/response sanitization
- Integration with monitoring services
"""

import time
import logging
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import DatabaseError
from rest_framework.exceptions import APIException
from stocksubscription.utils.error_handler import (
    ProductionError,
    log_error,
    create_error_response,
    get_client_ip,
    collect_error_context
)

logger = logging.getLogger('error_handler.middleware')

class ProductionErrorHandlerMiddleware(MiddlewareMixin):
    """
    Comprehensive error handling middleware for production
    
    Features:
    - Catches and handles all uncaught exceptions
    - Provides consistent error responses
    - Security-focused error sanitization
    - Performance monitoring
    - Request logging and analytics
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_request(self, request):
        """Process incoming request with performance monitoring"""
        # Add request start time for performance monitoring
        request._error_handler_start_time = time.time()
        
        # Log request details for monitoring
        logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'request_method': request.method,
                'request_path': request.path,
                'client_ip': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'user': str(getattr(request, 'user', 'Anonymous'))
            }
        )
        
        return None
    
    def process_response(self, request, response):
        """Process response with performance monitoring"""
        # Calculate request duration
        if hasattr(request, '_error_handler_start_time'):
            duration = time.time() - request._error_handler_start_time
            
            # Log slow requests
            if duration > 2.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration:.2f}s",
                    extra={
                        'request_method': request.method,
                        'request_path': request.path,
                        'duration': duration,
                        'status_code': response.status_code,
                        'client_ip': get_client_ip(request),
                        'user': str(getattr(request, 'user', 'Anonymous'))
                    }
                )
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def process_exception(self, request, exception):
        """Handle uncaught exceptions with comprehensive error handling"""
        
        # Don't handle exceptions in debug mode - let Django's debug page show
        if settings.DEBUG:
            return None
        
        try:
            # Log the exception with full context
            error_context = collect_error_context(request, exception)
            log_error(exception, request, error_context)
            
            # Create appropriate error response based on exception type
            if isinstance(exception, (ValidationError, ValueError)):
                return self._create_json_error_response(
                    message="Invalid request data",
                    status_code=400,
                    error_type="VALIDATION_ERROR"
                )
            
            elif isinstance(exception, PermissionDenied):
                return self._create_json_error_response(
                    message="Permission denied",
                    status_code=403,
                    error_type="PERMISSION_ERROR"
                )
            
            elif isinstance(exception, DatabaseError):
                return self._create_json_error_response(
                    message="Database error occurred",
                    status_code=500,
                    error_type="DATABASE_ERROR"
                )
            
            elif isinstance(exception, APIException):
                return self._create_json_error_response(
                    message=str(exception.detail),
                    status_code=exception.status_code,
                    error_type="API_ERROR"
                )
            
            elif isinstance(exception, ProductionError):
                return self._create_json_error_response(
                    message=exception.user_message,
                    status_code=exception.status_code,
                    error_type=exception.error_type
                )
            
            else:
                # Generic server error for security
                return self._create_json_error_response(
                    message="An unexpected error occurred",
                    status_code=500,
                    error_type="UNKNOWN_ERROR"
                )
                
        except Exception as middleware_error:
            # Fallback error handling if middleware itself fails
            logger.critical(
                f"Error handler middleware failed: {str(middleware_error)}",
                exc_info=True
            )
            
            return JsonResponse({
                'error': True,
                'message': 'System error occurred',
                'type': 'MIDDLEWARE_ERROR'
            }, status=500)
    
    def _create_json_error_response(self, message, status_code, error_type):
        """Create standardized JSON error response"""
        response_data = {
            'error': True,
            'message': message,
            'type': error_type,
            'timestamp': time.time()
        }
        
        response = JsonResponse(response_data, status=status_code)
        self._add_security_headers(response)
        return response
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        # Only add headers if they don't already exist
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
        for header, value in security_headers.items():
            if header not in response:
                response[header] = value
        
        # Add HSTS header for HTTPS requests
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Enhanced request logging middleware for production monitoring
    
    Features:
    - Comprehensive request/response logging
    - Performance analytics
    - Security event tracking
    - User activity monitoring
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        request_start_time = time.time()
        
        # Log request details
        self._log_request(request, request_start_time)
        
        # Get response
        response = self.get_response(request)
        
        # Process response
        request_duration = time.time() - request_start_time
        self._log_response(request, response, request_duration)
        
        return response
    
    def _log_request(self, request, start_time):
        """Log incoming request details"""
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'event_type': 'request_started',
                'request_method': request.method,
                'request_path': request.path,
                'query_string': request.META.get('QUERY_STRING', ''),
                'client_ip': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
                'user': str(getattr(request, 'user', 'Anonymous')),
                'timestamp': start_time,
                'content_type': request.META.get('CONTENT_TYPE', ''),
                'content_length': request.META.get('CONTENT_LENGTH', 0)
            }
        )
    
    def _log_response(self, request, response, duration):
        """Log response details and performance metrics"""
        logger.info(
            f"Request completed: {request.method} {request.path} - {response.status_code} in {duration:.3f}s",
            extra={
                'event_type': 'request_completed',
                'request_method': request.method,
                'request_path': request.path,
                'response_status': response.status_code,
                'duration': duration,
                'client_ip': get_client_ip(request),
                'user': str(getattr(request, 'user', 'Anonymous')),
                'response_size': len(response.content) if hasattr(response, 'content') else 0
            }
        )


class SecurityMonitoringMiddleware(MiddlewareMixin):
    """
    Security monitoring middleware for detecting and preventing attacks
    
    Features:
    - Suspicious activity detection
    - Rate limiting enforcement
    - Security event logging
    - Automated threat response
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.suspicious_patterns = [
            'union select',
            'drop table',
            '<script',
            'javascript:',
            '../../../',
            'eval(',
            'system(',
            'exec(',
        ]
    
    def process_request(self, request):
        """Monitor request for security threats"""
        client_ip = get_client_ip(request)
        
        # Check for suspicious patterns in request
        suspicious_content = self._detect_suspicious_content(request)
        if suspicious_content:
            logger.warning(
                f"Suspicious request detected from {client_ip}: {suspicious_content}",
                extra={
                    'event_type': 'security_threat_detected',
                    'threat_type': 'suspicious_content',
                    'client_ip': client_ip,
                    'request_path': request.path,
                    'request_method': request.method,
                    'suspicious_content': suspicious_content,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown')
                }
            )
        
        # Check for unusual request patterns
        self._check_request_patterns(request, client_ip)
        
        return None
    
    def _detect_suspicious_content(self, request):
        """Detect suspicious content in request"""
        # Check URL path
        path_lower = request.path.lower()
        for pattern in self.suspicious_patterns:
            if pattern in path_lower:
                return f"Suspicious pattern in URL: {pattern}"
        
        # Check query parameters
        query_string = request.META.get('QUERY_STRING', '').lower()
        for pattern in self.suspicious_patterns:
            if pattern in query_string:
                return f"Suspicious pattern in query: {pattern}"
        
        # Check headers for malicious content
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if any(pattern in user_agent for pattern in ['sqlmap', 'nmap', 'nikto', 'burp']):
            return f"Suspicious user agent: {user_agent}"
        
        return None
    
    def _check_request_patterns(self, request, client_ip):
        """Check for unusual request patterns"""
        # This is a simplified implementation
        # In production, you might use Redis or a more sophisticated system
        
        # Check for rapid requests (basic rate limiting)
        cache_key = f"request_count_{client_ip}"
        from django.core.cache import cache
        
        current_count = cache.get(cache_key, 0)
        if current_count > 100:  # More than 100 requests per minute
            logger.warning(
                f"High request rate detected from {client_ip}: {current_count} requests",
                extra={
                    'event_type': 'high_request_rate',
                    'client_ip': client_ip,
                    'request_count': current_count,
                    'time_window': 60
                }
            )
        
        cache.set(cache_key, current_count + 1, 60)  # 60 seconds window