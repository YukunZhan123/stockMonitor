from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.cache import never_cache
from django.middleware.csrf import get_token
import jwt
import logging
from django.conf import settings
from datetime import datetime, timedelta
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer
from django.contrib.auth.models import User
from django.core.cache import cache
import hashlib

# Import production error handling utilities
from stocksubscription.utils.error_handler import (
    handle_view_errors,
    log_error,
    create_error_response,
    SecurityValidator,
    RateLimitMonitor,
    monitor_performance,
    AuthenticationError,
    ValidationError as CustomValidationError,
    RateLimitError,
    get_client_ip
)

# Set up logging
logger = logging.getLogger('authentication')


# get_client_ip function now imported from shared error handler utility


def generate_jwt_tokens(user):
    """
    High-level purpose: Create JWT access and refresh tokens
    - Access token: Short-lived (1 hour) for API requests
    - Refresh token: Long-lived (7 days) for getting new access tokens
    """
    access_payload = {
        'user_id': user.id,
        'email': user.email,
        'is_staff': user.is_staff,  # Using Django's built-in admin flag
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(),
        'type': 'access'
    }
    
    refresh_payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
    
    return access_token, refresh_token


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
@csrf_exempt
@never_cache
@handle_view_errors
def register_view(request):
    """
    High-level purpose: Handle user registration with secure cookies and rate limiting
    - Validate registration data with enhanced security
    - Create new user account
    - Set JWT tokens as httpOnly cookies
    - Log registration attempts for security monitoring
    """
    client_ip = get_client_ip(request)
    logger.info(f"Registration attempt from IP: {client_ip}")
    
    # Check for too many failed attempts
    attempt_key = f"register_attempts_{client_ip}"
    attempts = cache.get(attempt_key, 0)
    
    if attempts >= 5:  # Max 5 registration attempts per IP per hour
        logger.warning(f"Registration rate limit exceeded for IP: {client_ip}")
        return Response({
            'error': 'Too many registration attempts. Please try again later.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            user = serializer.save()
            access_token, refresh_token = generate_jwt_tokens(user)
            
            logger.info(f"User registered successfully: {user.email}")
            
            response = Response({
                'message': 'Registration successful',
                'user': UserSerializer(user).data,
            }, status=status.HTTP_201_CREATED)
            
            # Set tokens as secure httpOnly cookies
            set_auth_cookies(response, access_token, refresh_token)
            
            # Reset attempt counter on success
            cache.delete(attempt_key)
            
            return response
            
        except Exception as e:
            logger.error(f"Registration error for {request.data.get('email', 'unknown')}: {str(e)}")
            return Response({
                'error': 'Registration failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Increment failed attempts
    cache.set(attempt_key, attempts + 1, 3600)  # Cache for 1 hour
    
    logger.warning(f"Registration failed for IP {client_ip}: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
@csrf_exempt
@never_cache
@handle_view_errors
def login_view(request):
    """
    High-level purpose: Handle user login with enhanced security
    - Rate limiting and brute force protection
    - Secure logging of login attempts
    - Generate JWT tokens with httpOnly cookies
    - Account lockout after failed attempts
    """
    client_ip = get_client_ip(request)
    email = request.data.get('email', 'unknown')
    
    # Check for brute force attempts
    login_key = f"login_attempts_{client_ip}"
    email_key = f"login_attempts_email_{email.lower()}"
    
    ip_attempts = cache.get(login_key, 0)
    email_attempts = cache.get(email_key, 0)
    
    # Rate limiting: 5 attempts per IP per 15 minutes, 3 attempts per email per hour
    if ip_attempts >= 5:
        logger.warning(f"Login brute force detected from IP: {client_ip}")
        return Response({
            'error': 'Too many login attempts from this IP. Please try again later.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    if email_attempts >= 3:
        logger.warning(f"Multiple failed login attempts for email: {email}")
        return Response({
            'error': 'Account temporarily locked due to failed attempts. Please try again later.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            user = serializer.validated_data['user']
            access_token, refresh_token = generate_jwt_tokens(user)
            
            logger.info(f"User login successful: {user.email} from IP: {client_ip}")
            
            response = Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
            }, status=status.HTTP_200_OK)
            
            # Set tokens as secure httpOnly cookies
            set_auth_cookies(response, access_token, refresh_token)
            
            # Clear failed attempt counters on successful login
            cache.delete(login_key)
            cache.delete(email_key)
            
            return response
            
        except Exception as e:
            logger.error(f"Login error for {email}: {str(e)}")
            return Response({
                'error': 'Login failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Increment failed attempt counters
    cache.set(login_key, ip_attempts + 1, 900)  # 15 minutes
    cache.set(email_key, email_attempts + 1, 3600)  # 1 hour
    
    logger.warning(f"Login failed for {email} from IP {client_ip}")
    
    return Response({
        'error': 'Invalid email or password.'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
@handle_view_errors
def refresh_token_view(request):
    """
    High-level purpose: Generate new access token from refresh token
    - Validate refresh token from httpOnly cookie
    - Create new access token
    - Extend user session without re-login
    """
    refresh_token = request.COOKIES.get('refresh_token')
    
    if not refresh_token:
        return Response({'error': 'Refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        
        if payload['type'] != 'refresh':
            return Response({'error': 'Invalid token type'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.get(id=payload['user_id'])
        access_token, new_refresh_token = generate_jwt_tokens(user)
        
        response = Response({
            'message': 'Token refreshed successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
        # Set new tokens as httpOnly cookies
        set_auth_cookies(response, access_token, new_refresh_token)
        return response
        
    except jwt.ExpiredSignatureError:
        return Response({'error': 'Refresh token expired'}, status=status.HTTP_401_UNAUTHORIZED)
    except (jwt.InvalidTokenError, User.DoesNotExist):
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
@handle_view_errors
def verify_auth_view(request):
    """
    High-level purpose: Verify authentication status using httpOnly cookies
    - Check access token from cookies
    - Return user data if valid
    - Handle token refresh if needed
    """
    # Debug logging for cookies
    logger.info(f"All cookies received: {dict(request.COOKIES)}")
    
    access_token = request.COOKIES.get('access_token')
    
    if not access_token:
        logger.warning("No access token found in cookies")
        return Response({'error': 'No access token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=['HS256'])
        
        if payload['type'] != 'access':
            return Response({'error': 'Invalid token type'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = User.objects.get(id=payload['user_id'])
        
        return Response({
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
    except jwt.ExpiredSignatureError:
        # Try to refresh token
        return refresh_token_view(request)
        
    except (jwt.InvalidTokenError, User.DoesNotExist):
        return Response({'error': 'Invalid access token'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
@handle_view_errors
def logout_view(request):
    """
    High-level purpose: Logout user and clear httpOnly cookies
    - Clear authentication cookies
    - Invalidate session
    """
    response = Response({
        'message': 'Logout successful'
    }, status=status.HTTP_200_OK)
    
    # Clear authentication cookies with the same parameters used when setting them
    samesite_setting = 'None' if not settings.DEBUG else 'Lax'
    
    response.delete_cookie(
        'access_token',
        path='/',
        domain=None,
        samesite=samesite_setting
    )
    response.delete_cookie(
        'refresh_token',
        path='/',
        domain=None,
        samesite=samesite_setting
    )
    
    return response


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_token_view(request):
    """
    Get CSRF token for frontend API calls
    """
    csrf_token = get_token(request)
    return Response({
        'csrfToken': csrf_token
    }, status=status.HTTP_200_OK)


def set_auth_cookies(response, access_token, refresh_token):
    """
    High-level purpose: Set secure httpOnly cookies for authentication
    - httpOnly prevents XSS access to tokens
    - Secure flag for HTTPS only in production
    - SameSite=None for cross-origin production, Lax for development
    """
    # Determine SameSite setting based on environment
    samesite_setting = 'None' if not settings.DEBUG else 'Lax'
    
    # Set access token cookie (1 hour expiration)
    response.set_cookie(
        'access_token',
        access_token,
        max_age=3600,  # 1 hour
        httponly=True,
        secure=not settings.DEBUG,  # HTTPS only in production
        samesite=samesite_setting,  # None for production cross-origin, Lax for dev
        path='/',  # Ensure cookie is available for all paths
        domain=None  # Let browser set domain automatically
    )
    
    # Set refresh token cookie (7 days expiration)
    response.set_cookie(
        'refresh_token', 
        refresh_token,
        max_age=7 * 24 * 3600,  # 7 days
        httponly=True,
        secure=not settings.DEBUG,
        samesite=samesite_setting,  # None for production cross-origin, Lax for dev
        path='/',  # Ensure cookie is available for all paths
        domain=None  # Let browser set domain automatically
    )
