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
    log_error,
    ValidationError as CustomValidationError,
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
        """Filter subscriptions to current user only"""
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
    
    @handle_view_errors
    def create(self, request, *args, **kwargs):
        """Create new stock subscription"""
        logger.info(f"Creating subscription for user {request.user.id}")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Fetch current stock price before saving
        stock_ticker = serializer.validated_data['stock_ticker']
        try:
            stock_service = StockDataService()
            current_price = stock_service.get_current_price(stock_ticker)
            serializer.validated_data['stock_price'] = current_price
        except Exception as e:
            logger.warning(f"Could not fetch price for {stock_ticker}: {str(e)}")
            # Continue without price - it will be updated later
        
        subscription = serializer.save()
        
        logger.info(f"Subscription created: {subscription.id}")
        return Response(
            StockSubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED
        )
    
    @handle_view_errors
    def update(self, request, *args, **kwargs):
        """Update existing subscription"""
        instance = self.get_object()
        logger.info(f"Updating subscription {instance.id}")
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
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
    
    @handle_view_errors
    def destroy(self, request, *args, **kwargs):
        """Delete subscription"""
        instance = self.get_object()
        logger.info(f"Deleting subscription {instance.id} for user {request.user.id}")
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    @handle_view_errors
    def send_now(self, request, pk=None):
        """Send notification immediately for specific subscription"""
        subscription = self.get_object()
        
        logger.info(f"Manual notification requested for subscription {subscription.id}")
        
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Update stock price first
            stock_service = StockDataService()
            current_price = stock_service.get_current_price(subscription.stock_ticker)
            subscription.stock_price = current_price
            subscription.save(update_fields=['stock_price', 'updated_at'])
            
            # Send notification
            notification_service = NotificationService()
            custom_message = serializer.validated_data.get('message')
            
            notification_log = notification_service.send_stock_notification(
                subscription=subscription,
                notification_type='manual',
                custom_message=custom_message
            )
            
            return Response({
                'message': 'Notification sent successfully',
                'notification_id': notification_log.id,
                'stock_price': str(current_price),
                'sent_to': subscription.email
            })
            
        except Exception as e:
            logger.error(f"Failed to send notification for {subscription.id}: {str(e)}")
            return Response({
                'error': 'Failed to send notification',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    @handle_view_errors
    def refresh_prices(self, request):
        """Refresh stock prices for all user's subscriptions"""
        logger.info(f"Refreshing prices for user {request.user.id}")
        
        subscriptions = self.get_queryset().filter(is_active=True)
        stock_service = StockDataService()
        updated_count = 0
        
        for subscription in subscriptions:
            try:
                current_price = stock_service.get_current_price(subscription.stock_ticker)
                subscription.stock_price = current_price
                subscription.save(update_fields=['stock_price', 'updated_at'])
                updated_count += 1
            except Exception as e:
                logger.warning(f"Could not update price for {subscription.stock_ticker}: {str(e)}")
        
        return Response({
            'message': f'Updated prices for {updated_count} subscriptions',
            'total_subscriptions': subscriptions.count(),
            'updated_count': updated_count
        })


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
        """Filter to current user's subscription logs only"""
        queryset = NotificationLog.objects.filter(
            subscription__user=self.request.user
        ).select_related('subscription')
        
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


# Legacy function-based views for specific endpoints
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@handle_view_errors
def subscription_stats(request):
    """Get subscription statistics for current user"""
    subscriptions = StockSubscription.objects.filter(user=request.user)
    
    stats = {
        'total_subscriptions': subscriptions.count(),
        'active_subscriptions': subscriptions.filter(is_active=True).count(),
        'unique_stocks': subscriptions.values('stock_ticker').distinct().count(),
        'total_notifications_sent': NotificationLog.objects.filter(
            subscription__user=request.user,
            status='sent'
        ).count(),
        'recent_notifications': NotificationLog.objects.filter(
            subscription__user=request.user
        ).count()
    }
    
    return Response(stats)