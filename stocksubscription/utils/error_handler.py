"""
Production-ready error handling utilities for Django backend

Features:
- Centralized error categorization and logging
- Custom exception classes for different error types
- Security-focused error responses (no sensitive data leakage)
- Performance monitoring and request tracking
- Integration ready for monitoring services
- Rate limiting and abuse detection utilities
- Input validation and sanitization helpers
- Comprehensive error context collection
"""

import logging
import time
import json
import traceback
from typing import Any, Dict, Optional, Union
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, DatabaseError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import (
    AuthenticationFailed, 
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
    NotFound,
    APIException
)

# Configure error logger
error_logger = logging.getLogger('error_handler')

class ErrorTypes:
    """Centralized error type constants"""
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR'
    PERMISSION_ERROR = 'PERMISSION_ERROR'
    NOT_FOUND_ERROR = 'NOT_FOUND_ERROR'
    DATABASE_ERROR = 'DATABASE_ERROR'
    RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR'
    SERVER_ERROR = 'SERVER_ERROR'
    NETWORK_ERROR = 'NETWORK_ERROR'
    BUSINESS_LOGIC_ERROR = 'BUSINESS_LOGIC_ERROR'
    UNKNOWN_ERROR = 'UNKNOWN_ERROR'

class ProductionError(Exception):
    """Base exception class for production errors"""
    
    def __init__(
        self, 
        message: str, 
        error_type: str = ErrorTypes.UNKNOWN_ERROR,
        status_code: int = 500,
        details: Optional[Dict] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or self.get_default_user_message()
        super().__init__(self.message)
    
    def get_default_user_message(self) -> str:
        """Get user-friendly error message"""
        messages = {
            ErrorTypes.VALIDATION_ERROR: "Please check your input and try again.",
            ErrorTypes.AUTHENTICATION_ERROR: "Authentication required. Please log in.",
            ErrorTypes.PERMISSION_ERROR: "You don't have permission to perform this action.",
            ErrorTypes.NOT_FOUND_ERROR: "The requested resource was not found.",
            ErrorTypes.DATABASE_ERROR: "A database error occurred. Please try again.",
            ErrorTypes.RATE_LIMIT_ERROR: "Too many requests. Please wait and try again.",
            ErrorTypes.SERVER_ERROR: "A server error occurred. Please try again later.",
            ErrorTypes.BUSINESS_LOGIC_ERROR: "Unable to complete the requested operation.",
        }
        return messages.get(self.error_type, "An unexpected error occurred.")

class ValidationError(ProductionError):
    """Validation error with field-specific details"""
    def __init__(self, message: str, field_errors: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_type=ErrorTypes.VALIDATION_ERROR,
            status_code=400,
            details={'field_errors': field_errors or {}}
        )

class AuthenticationError(ProductionError):
    """Authentication-related errors"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_type=ErrorTypes.AUTHENTICATION_ERROR,
            status_code=401
        )

class PermissionError(ProductionError):
    """Permission-related errors"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            error_type=ErrorTypes.PERMISSION_ERROR,
            status_code=403
        )

class NotFoundError(ProductionError):
    """Resource not found errors"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            error_type=ErrorTypes.NOT_FOUND_ERROR,
            status_code=404
        )

class RateLimitError(ProductionError):
    """Rate limiting errors"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_type=ErrorTypes.RATE_LIMIT_ERROR,
            status_code=429
        )

class BusinessLogicError(ProductionError):
    """Business logic validation errors"""
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message=message,
            error_type=ErrorTypes.BUSINESS_LOGIC_ERROR,
            status_code=422,
            user_message=user_message
        )

def categorize_exception(exception: Exception) -> str:
    """Categorize exception for consistent handling"""
    if isinstance(exception, (ValidationError, DRFValidationError)):
        return ErrorTypes.VALIDATION_ERROR
    elif isinstance(exception, (AuthenticationFailed, AuthenticationError)):
        return ErrorTypes.AUTHENTICATION_ERROR
    elif isinstance(exception, (PermissionDenied, DRFPermissionDenied, PermissionError)):
        return ErrorTypes.PERMISSION_ERROR
    elif isinstance(exception, (NotFound, NotFoundError)):
        return ErrorTypes.NOT_FOUND_ERROR
    elif isinstance(exception, (DatabaseError, IntegrityError)):
        return ErrorTypes.DATABASE_ERROR
    elif isinstance(exception, (Throttled, RateLimitError)):
        return ErrorTypes.RATE_LIMIT_ERROR
    elif isinstance(exception, ProductionError):
        return exception.error_type
    else:
        return ErrorTypes.UNKNOWN_ERROR

def collect_error_context(request, exception: Exception) -> Dict[str, Any]:
    """Collect comprehensive error context"""
    return {
        'timestamp': time.time(),
        'path': getattr(request, 'path', 'Unknown'),
        'method': getattr(request, 'method', 'Unknown'),
        'user': str(getattr(request, 'user', 'Anonymous')),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
        'ip_address': get_client_ip(request),
        'query_params': dict(getattr(request, 'GET', {})),
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'error_category': categorize_exception(exception),
        'stack_trace': traceback.format_exc() if settings.DEBUG else None,
    }

def get_client_ip(request) -> str:
    """Extract client IP address with proxy support"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', 'Unknown')
    return ip

def log_error(
    exception: Exception, 
    request=None, 
    context: Optional[Dict] = None,
    level: str = 'error'
) -> Dict[str, Any]:
    """Enhanced error logging with structured data"""
    
    error_context = {
        'timestamp': time.time(),
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'error_category': categorize_exception(exception),
        'context': context or {}
    }
    
    if request:
        error_context.update(collect_error_context(request, exception))
    
    # Log based on severity
    log_method = getattr(error_logger, level, error_logger.error)
    log_method(
        f"[{error_context['error_category']}] {error_context['exception_message']}", 
        extra={'error_context': error_context}
    )
    
    # In production, send to monitoring service
    if not settings.DEBUG:
        # TODO: Integrate with monitoring services
        # sentry_sdk.capture_exception(exception, contexts={'error_context': error_context})
        pass
    
    return error_context

def create_error_response(
    exception: Exception, 
    request=None, 
    context: Optional[Dict] = None
) -> Response:
    """Create standardized error response"""
    
    # Log the error
    error_context = log_error(exception, request, context)
    
    # Determine status code and user message
    if isinstance(exception, ProductionError):
        status_code = exception.status_code
        user_message = exception.user_message
        details = exception.details
    elif isinstance(exception, APIException):
        status_code = exception.status_code
        user_message = str(exception.detail)
        details = {}
    else:
        status_code = 500
        user_message = "An unexpected error occurred. Please try again later."
        details = {}
    
    # Prepare response data
    response_data = {
        'error': True,
        'message': user_message,
        'type': error_context['error_category'],
        'timestamp': error_context['timestamp']
    }
    
    # Add field errors for validation errors
    if error_context['error_category'] == ErrorTypes.VALIDATION_ERROR and details.get('field_errors'):
        response_data['field_errors'] = details['field_errors']
    
    # Add debug info in development
    if settings.DEBUG:
        response_data['debug'] = {
            'exception_type': error_context['exception_type'],
            'exception_message': error_context['exception_message'],
            'stack_trace': error_context.get('stack_trace')
        }
    
    return Response(response_data, status=status_code)

def handle_view_errors(view_func):
    """Decorator for comprehensive function-based view error handling"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        
        try:
            # Execute the view
            response = view_func(request, *args, **kwargs)
            
            # Log slow requests
            duration = time.time() - start_time
            if duration > 2.0:  # Log requests taking more than 2 seconds
                error_logger.warning(
                    f"Slow request detected: {request.path} took {duration:.2f}s",
                    extra={
                        'request_path': request.path,
                        'request_method': request.method,
                        'duration': duration,
                        'user': str(getattr(request, 'user', 'Anonymous'))
                    }
                )
            
            return response
            
        except Exception as e:
            return create_error_response(e, request, {
                'view_name': view_func.__name__,
                'duration': time.time() - start_time
            })
    
    return wrapper

class SecurityValidator:
    """Security-focused input validation"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValidationError("Input must be a string")
        
        # Remove potential XSS vectors
        dangerous_patterns = ['<script', 'javascript:', 'on\w+="', '<iframe', '<object']
        for pattern in dangerous_patterns:
            if pattern.lower() in value.lower():
                raise ValidationError("Input contains potentially dangerous content")
        
        # Limit length
        if len(value) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)")
        
        return value.strip()
    
    @staticmethod
    def validate_email_domain(email: str) -> str:
        """Validate email domain against disposable email list"""
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', 'temp-mail.org'
        ]
        
        domain = email.split('@')[1].lower() if '@' in email else ''
        if domain in disposable_domains:
            raise ValidationError("Disposable email addresses are not allowed")
        
        return email
    
    @staticmethod
    def validate_password_strength(password: str) -> str:
        """Validate password strength"""
        import re
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one digit")
        
        # Check against common passwords
        common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein']
        if password.lower() in common_passwords:
            raise ValidationError("This password is too common")
        
        return password

class RateLimitMonitor:
    """Rate limiting and abuse detection"""
    
    @staticmethod
    def check_request_rate(request, key: str, max_requests: int, window_seconds: int):
        """Check if request rate exceeds limits"""
        # This is a simplified implementation
        # In production, use Redis or similar for distributed rate limiting
        from django.core.cache import cache
        
        cache_key = f"rate_limit:{key}:{request.META.get('REMOTE_ADDR')}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= max_requests:
            raise RateLimitError(f"Rate limit exceeded. Max {max_requests} requests per {window_seconds} seconds.")
        
        cache.set(cache_key, current_requests + 1, window_seconds)
    
    @staticmethod
    def detect_suspicious_activity(request, user=None):
        """Detect potentially suspicious activity"""
        # Check for rapid successive requests
        # Check for unusual user agent patterns
        # Check for suspicious IP addresses
        # This is a placeholder for more sophisticated detection
        pass

def monitor_performance(operation_name: str):
    """Decorator for monitoring operation performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log slow operations
                if duration > 1.0:
                    error_logger.warning(
                        f"Slow operation: {operation_name} took {duration:.2f}s"
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                log_error(e, context={
                    'operation': operation_name,
                    'duration': duration
                })
                raise
        
        return wrapper
    return decorator

# Utility functions for common operations
def safe_json_loads(data: str, default=None):
    """Safely parse JSON with error handling"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        log_error(e, context={'data_type': type(data).__name__})
        return default

def validate_required_fields(data: Dict, required_fields: list):
    """Validate that required fields are present"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] in [None, '', []]:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            field_errors={field: "This field is required" for field in missing_fields}
        )

# Health check utilities
def get_system_health() -> Dict[str, Any]:
    """Get system health information"""
    from django.db import connection
    
    health_data = {
        'timestamp': time.time(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_data['checks']['database'] = 'ok'
    except Exception as e:
        health_data['checks']['database'] = 'error'
        health_data['status'] = 'unhealthy'
        log_error(e, context={'health_check': 'database'})
    
    # Add more health checks as needed
    return health_data