from rest_framework import serializers
from django.contrib.auth.models import User
from .models import StockSubscription, NotificationLog
from .services import StockDataService
import re


class StockSubscriptionSerializer(serializers.ModelSerializer):
    """
    High-level purpose: Serialize stock subscription data for API responses
    - Validate stock ticker format and email
    - Auto-assign current user to subscription
    - Format output with computed fields
    """
    
    # Read-only fields for API responses
    price_display = serializers.ReadOnlyField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = StockSubscription
        fields = [
            'id', 'stock_ticker', 'email', 'stock_price', 'price_display',
            'is_active', 'created_at', 'updated_at', 'last_notification_sent',
            'user_email', 'user_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'stock_price', 'last_notification_sent']
    
    def validate_stock_ticker(self, value):
        """Validate stock ticker format and verify it has a valid price"""
        if not value:
            raise serializers.ValidationError("Stock ticker is required")
        
        # Clean and uppercase the ticker
        value = value.upper().strip()
        
        # Basic format validation (1-5 letters, possibly with numbers)
        if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', value):
            raise serializers.ValidationError(
                "Invalid stock ticker format. Use standard ticker symbols (e.g., AAPL, GOOGL)"
            )
        
        # Validate ticker has a valid price using StockDataService
        stock_service = StockDataService()
        ticker_validation = stock_service.validate_ticker(value)
        
        if not ticker_validation.get('valid'):
            raise serializers.ValidationError(
                f"'{value}' is not a valid stock ticker or price data is unavailable. "
                "Please verify the ticker symbol is correct."
            )
        
        return value
    
    def validate_email(self, value):
        """Enhanced email validation"""
        if not value:
            raise serializers.ValidationError("Email address is required")
        
        # Normalize email
        value = value.lower().strip()
        
        # Check for disposable email domains (basic protection)
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'trashmail.com'
        ]
        domain = value.split('@')[1] if '@' in value else ''
        if domain in disposable_domains:
            raise serializers.ValidationError("Disposable email addresses are not allowed")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Check for duplicate subscription
        user = self.context['request'].user
        stock_ticker = attrs.get('stock_ticker')
        email = attrs.get('email')
        
        # For updates, exclude current instance
        queryset = StockSubscription.objects.filter(
            user=user,
            stock_ticker=stock_ticker,
            email=email
        )
        
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(
                "You already have a subscription for this stock and email combination"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create subscription with current user and fetch initial stock price"""
        validated_data['user'] = self.context['request'].user
        
        # Fetch and set initial stock price
        stock_service = StockDataService()
        current_price = stock_service.get_current_price(validated_data['stock_ticker'])
        if current_price:
            validated_data['stock_price'] = current_price
            
        return super().create(validated_data)


class NotificationLogSerializer(serializers.ModelSerializer):
    """
    High-level purpose: Serialize notification log data for API responses
    - Read-only serializer for notification history
    - Include related subscription details and user info
    """
    
    stock_ticker = serializers.CharField(source='subscription.stock_ticker', read_only=True)
    subscription_email = serializers.EmailField(source='subscription.email', read_only=True)
    user_email = serializers.EmailField(source='subscription.user.email', read_only=True)
    user_username = serializers.CharField(source='subscription.user.username', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification_type', 'status', 'subject', 'email_to',
            'stock_price_at_send', 'sent_at', 'error_message', 'created_at',
            'stock_ticker', 'subscription_email', 'user_email', 'user_username'
        ]
        read_only_fields = '__all__'


class StockSubscriptionListSerializer(StockSubscriptionSerializer):
    """
    Optimized serializer for list views
    - Minimal fields for performance
    - Include user info for admin visibility
    """
    
    class Meta(StockSubscriptionSerializer.Meta):
        fields = [
            'id', 'stock_ticker', 'email', 'stock_price', 'price_display',
            'is_active', 'created_at', 'user_email', 'user_username'
        ]


class SendNotificationSerializer(serializers.Serializer):
    """
    Serializer for manual notification sending
    - Validates subscription exists and belongs to user
    - Supports custom message override
    """
    
    message = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Optional custom message to include in the notification"
    )
    
    def validate(self, attrs):
        # Subscription validation is handled in the view
        return attrs