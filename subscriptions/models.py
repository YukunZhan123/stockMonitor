from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
import uuid


class StockSubscription(models.Model):
    """
    High-level purpose: Stock subscription model for email notifications
    - Links users to specific stock tickers they want to monitor
    - Stores email for notifications (can be different from user email)
    - Tracks stock price and last notification details
    - Supports scheduled and on-demand email notifications
    """
    
    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stock_subscriptions')
    
    # Stock information
    stock_ticker = models.CharField(
        max_length=10,
        help_text="Stock ticker symbol (e.g., AAPL, GOOGL)"
    )
    stock_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Current stock price"
    )
    
    # Email notification settings
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text="Email address for stock notifications"
    )
    
    # Notification tracking
    last_notification_sent = models.DateTimeField(null=True, blank=True)
    last_price_sent = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_subscriptions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['stock_ticker']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            # Prevent duplicate subscriptions for same user/stock/email combo
            models.UniqueConstraint(
                fields=['user', 'stock_ticker', 'email'],
                name='unique_user_stock_email'
            )
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.stock_ticker} ({self.email})"
    
    @property
    def price_display(self):
        """Format price for display"""
        if self.stock_price:
            return f"${self.stock_price:.2f}"
        return "N/A"


class NotificationLog(models.Model):
    """
    High-level purpose: Track all email notifications sent
    - Audit trail of notification history
    - Track success/failure of email sends
    - Support for analytics and monitoring
    """
    
    NOTIFICATION_TYPES = [
        ('scheduled', 'Scheduled Notification'),
        ('manual', 'Manual Send'),
        ('price_alert', 'Price Alert'),
    ]
    
    NOTIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent Successfully'),
        ('failed', 'Failed to Send'),
        ('bounced', 'Email Bounced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        StockSubscription, 
        on_delete=models.CASCADE, 
        related_name='notification_logs'
    )
    
    # Notification details
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS, default='pending')
    
    # Email content
    subject = models.CharField(max_length=200)
    email_to = models.EmailField()
    stock_price_at_send = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notification_logs'
        indexes = [
            models.Index(fields=['subscription', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['notification_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.stock_ticker} notification to {self.email_to} - {self.status}"