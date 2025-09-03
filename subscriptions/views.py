from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
import logging

from .models import StockSubscription, NotificationLog
from .serializers import (
    StockSubscriptionSerializer, 
    StockSubscriptionListSerializer,
    NotificationLogSerializer,
    SendNotificationSerializer
)
from .services import StockDataService, NotificationService
from stocksubscription.utils.error_handler import (
    handle_view_errors,
)

logger = logging.getLogger('subscriptions')


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API responses"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class StockSubscriptionViewSet(ModelViewSet):
    """
    High-level purpose: CRUD operations for stock subscriptions
    - List, create, update, delete user's stock subscriptions
    - Filter by active status and stock ticker
    - Support manual notification sending
    - Paginated responses for performance
    """
    
    serializer_class = StockSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Filter subscriptions - admin users see all, regular users see only their own"""
        if self.request.user.is_staff:
            # Admin users can see all subscriptions
            queryset = StockSubscription.objects.all()
        else:
            # Regular users can only see their own subscriptions
            queryset = StockSubscription.objects.filter(user=self.request.user)
        
        # Filter by active status
        is_active = self.request.query_params.get('active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by stock ticker
        ticker = self.request.query_params.get('ticker')
        if ticker:
            queryset = queryset.filter(stock_ticker__icontains=ticker.upper())
        
        return queryset.select_related('user')
    
    def get_serializer_class(self):
        """Use optimized serializer for list view"""
        if self.action == 'list':
            return StockSubscriptionListSerializer
        return StockSubscriptionSerializer
    
    def create(self, request, *args, **kwargs):
        """Create new stock subscription"""
        logger.info(f"Creating subscription for user {request.user.id}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Subscription creation failed for user {request.user.id}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Fetch current stock price before saving
        stock_ticker = serializer.validated_data['stock_ticker']
        try:
            stock_service = StockDataService()
            current_price = stock_service.get_current_price(stock_ticker)
            if current_price:
                serializer.validated_data['stock_price'] = current_price
            else:
                logger.info(f"Price not available for {stock_ticker}, will retry later")
                # Don't set price - leave as None so frontend shows "N/A"
        except Exception as e:
            logger.warning(f"Could not fetch price for {stock_ticker}: {str(e)}")
            # Continue without price - it will be updated later
        
        subscription = serializer.save()
        
        logger.info(f"Subscription created: {subscription.id}")
        return Response(
            StockSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update existing subscription"""
        instance = self.get_object()
        logger.info(f"Updating subscription {instance.id}")
        
        # Check if user can modify this subscription
        if not request.user.is_staff and instance.user != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            logger.warning(f"Subscription update failed for {instance.id}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Update stock price if ticker changed
        if 'stock_ticker' in serializer.validated_data:
            stock_ticker = serializer.validated_data['stock_ticker']
            try:
                stock_service = StockDataService()
                current_price = stock_service.get_current_price(stock_ticker)
                serializer.validated_data['stock_price'] = current_price
            except Exception as e:
                logger.warning(f"Could not fetch price for {stock_ticker}: {str(e)}")
        
        subscription = serializer.save()
        return Response(StockSubscriptionSerializer(subscription).data)
    
    def destroy(self, request, *args, **kwargs):
        """Delete subscription"""
        instance = self.get_object()
        logger.info(f"Deleting subscription {instance.id} for user {request.user.id}")
        
        # Check if user can delete this subscription
        if not request.user.is_staff and instance.user != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
    @action(detail=False, methods=['post'])
    def refresh_prices(self, request):
        """Refresh stock prices for subscriptions (admin: all, regular user: only their own)"""
        if request.user.is_staff:
            logger.info(f"Admin refreshing prices for all subscriptions")
        else:
            logger.info(f"Refreshing prices for user {request.user.id}")
        
        subscriptions = self.get_queryset().filter(is_active=True)
        stock_service = StockDataService()
        updated_count = 0
        
        # Get unique tickers to avoid duplicate API calls
        unique_tickers = subscriptions.values_list('stock_ticker', flat=True).distinct()
        price_cache = {}
        
        # Fetch prices for all unique tickers first
        for ticker in unique_tickers:
            try:
                price_cache[ticker] = stock_service.get_current_price(ticker)
            except Exception as e:
                logger.warning(f"Could not fetch price for {ticker}: {str(e)}")
                price_cache[ticker] = None
        
        # Bulk update subscriptions using cached prices
        subscriptions_to_update = []
        for subscription in subscriptions:
            price = price_cache.get(subscription.stock_ticker)
            if price is not None:
                subscription.stock_price = price
                subscriptions_to_update.append(subscription)
                updated_count += 1
        
        # Bulk update database
        if subscriptions_to_update:
            StockSubscription.objects.bulk_update(
                subscriptions_to_update, 
                ['stock_price'], 
                batch_size=100
            )
        
        return Response({
            'message': f'Updated prices for {updated_count} subscriptions',
            'total_subscriptions': subscriptions.count(),
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def trigger_notifications(self, request):
        """Start the notification scheduler that runs continuously (admin only)"""
        # Only allow admin users to trigger this
        if not request.user.is_staff:
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Start the scheduler in a background thread that runs forever
            from subscriptions.scheduler import start_notification_scheduler
            import threading
            
            # Check if scheduler is already running
            for thread in threading.enumerate():
                if thread.name == 'notification-scheduler':
                    return Response({
                        'message': 'Notification scheduler is already running',
                        'status': 'already_running'
                    })
            
            # Start scheduler in daemon thread
            scheduler_thread = threading.Thread(
                target=start_notification_scheduler, 
                daemon=True,
                name='notification-scheduler'
            )
            scheduler_thread.start()
            
            return Response({
                'message': 'Notification scheduler started successfully - will run every 5 minutes',
                'status': 'started',
                'triggered_by': request.user.email
            })
            
        except Exception as e:
            logger.error(f"Failed to start notification scheduler: {str(e)}")
            return Response({
                'error': 'Failed to start notification scheduler',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationLogViewSet(ModelViewSet):
    """
    High-level purpose: View notification history
    - Read-only access to notification logs
    - Filter by subscription and status
    - Paginated for performance
    """
    
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    http_method_names = ['get']  # Read-only
    
    def get_queryset(self):
        """Filter logs - admin users see all, regular users see only their own"""
        if self.request.user.is_staff:
            # Admin users can see all notification logs
            queryset = NotificationLog.objects.all()
        else:
            # Regular users can only see their own subscription logs
            queryset = NotificationLog.objects.filter(
                subscription__user=self.request.user
            )
        
        queryset = queryset.select_related('subscription', 'subscription__user')
        
        # Filter by subscription
        subscription_id = self.request.query_params.get('subscription')
        if subscription_id:
            queryset = queryset.filter(subscription_id=subscription_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by notification type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset


# Manual send-now endpoint (workaround for DRF action routing issue)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@handle_view_errors
def send_now_view(request, pk):
    """Send notification immediately for specific subscription"""
    try:
        if request.user.is_staff:
            # Admin users can send notifications for any subscription
            subscription = StockSubscription.objects.get(pk=pk)
        else:
            # Regular users can only send notifications for their own subscriptions
            subscription = StockSubscription.objects.get(pk=pk, user=request.user)
    except StockSubscription.DoesNotExist:
        return Response({'error': 'Subscription not found'}, status=status.HTTP_404_NOT_FOUND)
    
    logger.info(f"Manual notification requested for subscription {subscription.id}")
    
    # Get optional custom message
    custom_message = request.data.get('message', None)
    
    try:
        # Update stock price first
        stock_service = StockDataService()
        current_price = stock_service.get_current_price(subscription.stock_ticker)
        if current_price:
            subscription.stock_price = current_price
            subscription.save(update_fields=['stock_price', 'updated_at'])
        
        # Send notification
        notification_service = NotificationService()
        
        notification_log = notification_service.send_stock_notification(
            subscription=subscription,
            notification_type='manual',
            custom_message=custom_message
        )
        
        return Response({
            'message': 'Notification sent successfully',
            'notification_id': notification_log.id,
            'stock_price': str(subscription.stock_price) if subscription.stock_price else None,
            'sent_to': subscription.email
        })
        
    except Exception as e:
        logger.error(f"Failed to send notification for {subscription.id}: {str(e)}")
        return Response({
            'error': 'Failed to send notification',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Legacy function-based views for specific endpoints




# Public webhook endpoint (no authentication required)
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def trigger_notifications_webhook(request):
    """
    Public webhook to trigger notifications - can be called by external schedulers
    No authentication required - use this for cron services or external triggers
    """
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
        return response
    
    try:
        from django.core.management import call_command
        import io
        
        # Capture the output of the management command
        output = io.StringIO()
        call_command('send_notifications', stdout=output)
        result = output.getvalue()
        
        response = JsonResponse({
            'status': 'success',
            'message': 'Notifications triggered successfully',
            'output': result
        })
        response['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        logger.error(f"Webhook trigger failed: {str(e)}")
        response = JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)
        response['Access-Control-Allow-Origin'] = '*'
        return response