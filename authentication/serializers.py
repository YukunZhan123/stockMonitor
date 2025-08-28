from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
import re
import logging

logger = logging.getLogger('authentication')


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    High-level purpose: Handle user registration with enhanced security validation
    - Validates email format, uniqueness, and domain
    - Ensures password meets strict security requirements
    - Validates username for security (no special chars, reasonable length)
    - Creates new user account with proper sanitization
    """
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True}
        }
    
    def validate_email(self, value):
        """Enhanced email validation"""
        if not value:
            raise serializers.ValidationError("Email is required")
        
        # Normalize email
        value = value.lower().strip()
        
        # Basic email validation
        email_validator = EmailValidator()
        email_validator(value)
        
        # Check for disposable email domains (basic list)
        disposable_domains = ['10minutemail.com', 'tempmail.org', 'guerrillamail.com']
        domain = value.split('@')[1] if '@' in value else ''
        if domain in disposable_domains:
            raise serializers.ValidationError("Disposable email addresses are not allowed")
        
        # Check uniqueness
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        
        return value
    
    def validate_username(self, value):
        """Enhanced username validation"""
        if not value:
            raise serializers.ValidationError("Username is required")
        
        # Sanitize username
        value = value.strip()
        
        # Length check
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        if len(value) > 30:
            raise serializers.ValidationError("Username must be less than 30 characters long")
        
        # Character validation (alphanumeric, underscores, hyphens only)
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        
        # Check uniqueness
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists")
        
        return value
    
    def validate_password(self, value):
        """Enhanced password validation"""
        if not value:
            raise serializers.ValidationError("Password is required")
        
        # Additional security checks beyond Django's validation
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Password must contain at least one digit")
        
        # Check for common weak passwords
        common_passwords = ['password', '123456', 'qwerty', 'admin', 'letmein']
        if value.lower() in common_passwords:
            raise serializers.ValidationError("This password is too common")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Password confirmation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Ensure password doesn't contain username or email
        username = attrs.get('username', '').lower()
        email_local = attrs.get('email', '').split('@')[0].lower()
        password_lower = attrs['password'].lower()
        
        if username and username in password_lower:
            raise serializers.ValidationError("Password cannot contain your username")
        
        if email_local and email_local in password_lower:
            raise serializers.ValidationError("Password cannot contain your email address")
        
        return attrs
    
    def create(self, validated_data):
        """Create user account with proper logging"""
        validated_data.pop('password_confirm')
        
        try:
            user = User.objects.create_user(**validated_data)
            logger.info(f"New user created: {user.username} ({user.email})")
            return user
        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise serializers.ValidationError("Account creation failed. Please try again.")


class UserLoginSerializer(serializers.Serializer):
    """
    High-level purpose: Handle user login authentication
    - Validates email/password combination
    - Returns user object if authentication succeeds
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Authenticate user credentials"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")
        
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    High-level purpose: Serialize user data for API responses
    - Expose safe user information (no passwords)
    - Include is_staff for admin role handling (simpler than custom field)
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'date_joined']