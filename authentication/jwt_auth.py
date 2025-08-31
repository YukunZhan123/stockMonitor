from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User
from django.conf import settings
import jwt
import logging

logger = logging.getLogger('authentication')


class JWTCookieAuthentication(BaseAuthentication):
    """
    Custom authentication backend using JWT tokens from httpOnly cookies.
    
    High-level purpose:
    - Extract JWT access token from httpOnly cookies (secure)
    - Validate JWT signature and expiration
    - Return authenticated user for API requests
    - pure stateless JWT authentication
    """
    
    def authenticate(self, request):
        """
        Authenticate user from JWT token in httpOnly cookie.
        
        Returns:
        - (user, token) tuple if authentication successful
        - None if no token or invalid token (allows other auth backends)
        """
        access_token = request.COOKIES.get('access_token')
        
        if not access_token:
            # No JWT token found - not an error, just not JWT auth
            return None
        
        try:
            # Decode and validate JWT token
            payload = jwt.decode(
                access_token, 
                settings.SECRET_KEY, 
                algorithms=['HS256']
            )
            
            # Validate token type
            if payload.get('type') != 'access':
                logger.warning(f"Invalid JWT token type: {payload.get('type')}")
                raise AuthenticationFailed('Invalid token type')
            
            # Get user from database
            try:
                user = User.objects.get(id=payload['user_id'])
            except User.DoesNotExist:
                logger.warning(f"JWT token references non-existent user: {payload['user_id']}")
                raise AuthenticationFailed('User not found')
            
            # Check if user is still active
            if not user.is_active:
                logger.warning(f"JWT token for inactive user: {user.id}")
                raise AuthenticationFailed('User account disabled')
            
            logger.debug(f"JWT authentication successful for user: {user.id}")
            return (user, access_token)
            
        except jwt.ExpiredSignatureError:
            logger.info("JWT token expired")
            raise AuthenticationFailed('Token expired')
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise AuthenticationFailed('Invalid token')
        
        except Exception as e:
            logger.error(f"Unexpected error in JWT authentication: {str(e)}")
            raise AuthenticationFailed('Authentication failed')
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'JWT'


class JWTCookieAuthenticationMiddleware:
    """
    Middleware to handle JWT authentication for Django admin and non-DRF views.
    
    This allows the Django admin panel to work with JWT tokens instead of sessions.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTCookieAuthentication()
    
    def __call__(self, request):
        # Skip if user is already authenticated by other means
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            try:
                auth_result = self.jwt_auth.authenticate(request)
                if auth_result:
                    user, token = auth_result
                    request.user = user
                    # Mark as JWT authenticated for potential future use
                    
                    logger.debug(f"Middleware JWT auth successful for user: {user.id}")
            except AuthenticationFailed:
                # Let the view handle authentication failure
                pass
            except Exception as e:
                logger.error(f"JWT middleware error: {str(e)}")
        
        return self.get_response(request)