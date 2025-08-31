from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import StockSubscription, NotificationLog


@admin.register(StockSubscription)
class StockSubscriptionAdmin(admin.ModelAdmin):
    """Admin interface for stock subscriptions"""
    
    list_display = [
        'stock_ticker', 'username_display', 'user_email_display', 'email', 'current_price_display', 
        'is_active', 'last_notification_display', 'created_at'
    ]
    list_filter = ['is_active', 'stock_ticker', 'user__username', 'created_at', 'last_notification_sent']
    search_fields = ['stock_ticker', 'email', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_notification_sent', 'last_price_sent']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Subscription Details', {
            'fields': ('user', 'stock_ticker', 'email', 'is_active')
        }),
        ('Price Information', {
            'fields': ('stock_price', 'last_price_sent', 'last_notification_sent')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def username_display(self, obj):
        return format_html('<strong>{}</strong>', obj.user.username)
    username_display.short_description = 'Username'
    username_display.admin_order_field = 'user__username'
    
    def user_email_display(self, obj):
        return obj.user.email
    user_email_display.short_description = 'User Email'
    user_email_display.admin_order_field = 'user__email'
    
    def current_price_display(self, obj):
        if obj.stock_price:
            return format_html('<span style="font-weight: bold;">${:.2f}</span>', obj.stock_price)
        return '-'
    current_price_display.short_description = 'Current Price'
    current_price_display.admin_order_field = 'stock_price'
    
    def last_notification_display(self, obj):
        if obj.last_notification_sent:
            time_diff = timezone.now() - obj.last_notification_sent
            if time_diff.days > 0:
                return f"{time_diff.days} days ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                return f"{hours} hours ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        return "Never"
    last_notification_display.short_description = 'Last Notification'
    last_notification_display.admin_order_field = 'last_notification_sent'
    
    actions = ['activate_subscriptions', 'deactivate_subscriptions', 'refresh_prices']
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscriptions activated.')
    activate_subscriptions.short_description = 'Activate selected subscriptions'
    
    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscriptions deactivated.')
    deactivate_subscriptions.short_description = 'Deactivate selected subscriptions'
    
    def refresh_prices(self, request, queryset):
        from .services import StockDataService
        stock_service = StockDataService()
        updated = 0
        
        # Get unique tickers to avoid duplicate API calls
        unique_tickers = queryset.values_list('stock_ticker', flat=True).distinct()
        price_cache = {}
        
        # Fetch prices for all unique tickers first
        for ticker in unique_tickers:
            try:
                price_cache[ticker] = stock_service.get_current_price(ticker)
            except Exception:
                price_cache[ticker] = None
        
        # Bulk update subscriptions using cached prices
        subscriptions_to_update = []
        for subscription in queryset:
            price = price_cache.get(subscription.stock_ticker)
            if price is not None:
                subscription.stock_price = price
                subscriptions_to_update.append(subscription)
                updated += 1
        
        # Bulk update database
        if subscriptions_to_update:
            from .models import StockSubscription
            StockSubscription.objects.bulk_update(
                subscriptions_to_update, 
                ['stock_price', 'updated_at'], 
                batch_size=100
            )
        
        self.message_user(request, f'Refreshed prices for {updated} subscriptions.')
    refresh_prices.short_description = 'Refresh stock prices'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Admin interface for notification logs"""
    
    list_display = [
        'stock_ticker_display', 'username_display', 'notification_type', 'status_display', 
        'email_to', 'price_at_send', 'sent_at', 'created_at'
    ]
    list_filter = ['status', 'notification_type', 'subscription__user__username', 'created_at', 'sent_at']
    search_fields = ['email_to', 'subject', 'subscription__stock_ticker', 'subscription__user__username']
    readonly_fields = ['id', 'created_at', 'sent_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('subscription', 'notification_type', 'status', 'email_to', 'subject')
        }),
        ('Content & Timing', {
            'fields': ('stock_price_at_send', 'sent_at', 'error_message')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def stock_ticker_display(self, obj):
        return format_html('<strong>{}</strong>', obj.subscription.stock_ticker)
    stock_ticker_display.short_description = 'Stock'
    stock_ticker_display.admin_order_field = 'subscription__stock_ticker'
    
    def username_display(self, obj):
        return format_html('<strong>{}</strong>', obj.subscription.user.username)
    username_display.short_description = 'Username'
    username_display.admin_order_field = 'subscription__user__username'
    
    def status_display(self, obj):
        colors = {
            'pending': '#f59e0b',  # yellow
            'sent': '#10b981',     # green
            'failed': '#ef4444',   # red
            'bounced': '#f59e0b',  # yellow
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def price_at_send(self, obj):
        if obj.stock_price_at_send:
            return f"${obj.stock_price_at_send:.2f}"
        return '-'
    price_at_send.short_description = 'Price at Send'
    price_at_send.admin_order_field = 'stock_price_at_send'
    
    def has_add_permission(self, request):
        # Notification logs are created automatically, not manually
        return False