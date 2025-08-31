from celery import shared_task
from django.utils import timezone
from django.db import transaction
from collections import defaultdict
import logging

from .models import StockSubscription, NotificationLog
from .services import StockDataService, NotificationService

logger = logging.getLogger('subscriptions')


@shared_task(bind=True, max_retries=3)
def send_periodic_notifications(self):
    """
    Periodic task to send stock price notifications
    - Runs every hour during market hours (9AM-5PM ET, Mon-Fri)
    - Groups subscriptions by email address to merge emails
    - Updates stock prices before sending
    """
    try:
        logger.info("Starting periodic stock notifications task")
        
        # Get all active subscriptions
        subscriptions = StockSubscription.objects.filter(is_active=True).select_related('user')
        
        if not subscriptions.exists():
            logger.info("No active subscriptions found")
            return {'message': 'No active subscriptions', 'sent': 0}
        
        # Update all stock prices first
        _update_stock_prices(subscriptions)
        
        # Group subscriptions by email address for merging
        email_groups = _group_subscriptions_by_email(subscriptions)
        
        # Send merged emails
        results = _send_merged_emails(email_groups)
        
        logger.info(f"Periodic notifications completed: {results['sent']} emails sent, {results['failed']} failed")
        return results
        
    except Exception as exc:
        logger.error(f"Periodic notifications task failed: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _update_stock_prices(subscriptions):
    """Update stock prices for all subscriptions"""
    stock_service = StockDataService()
    updated_count = 0
    
    # Group by ticker to avoid duplicate API calls
    ticker_groups = defaultdict(list)
    for subscription in subscriptions:
        ticker_groups[subscription.stock_ticker].append(subscription)
    
    for ticker, ticker_subscriptions in ticker_groups.items():
        try:
            current_price = stock_service.get_current_price(ticker)
            if current_price:
                # Update all subscriptions with this ticker
                for subscription in ticker_subscriptions:
                    subscription.stock_price = current_price
                    subscription.save(update_fields=['stock_price', 'updated_at'])
                    updated_count += 1
                logger.info(f"Updated price for {ticker}: ${current_price}")
            else:
                logger.warning(f"Could not get price for {ticker}")
        except Exception as e:
            logger.error(f"Failed to update price for {ticker}: {str(e)}")
    
    logger.info(f"Updated prices for {updated_count} subscriptions")


def _group_subscriptions_by_email(subscriptions):
    """Group subscriptions by email address for merging"""
    email_groups = defaultdict(list)
    
    for subscription in subscriptions:
        email_groups[subscription.email].append(subscription)
    
    return email_groups


def _send_merged_emails(email_groups):
    """Send merged emails to each email address"""
    notification_service = NotificationService()
    sent_count = 0
    failed_count = 0
    errors = []
    
    for email, subscriptions in email_groups.items():
        try:
            if len(subscriptions) == 1:
                # Single subscription - use regular notification
                notification_log = notification_service.send_stock_notification(
                    subscription=subscriptions[0],
                    notification_type='scheduled'
                )
            else:
                # Multiple subscriptions - use merged notification
                notification_log = notification_service.send_merged_notification(
                    subscriptions=subscriptions,
                    notification_type='scheduled'
                )
            
            if notification_log.status == 'sent':
                sent_count += 1
                logger.info(f"Sent notification to {email} for {len(subscriptions)} subscriptions")
            else:
                failed_count += 1
                errors.append(f"Failed to send to {email}: {notification_log.error_message}")
                
        except Exception as e:
            failed_count += 1
            error_msg = f"Failed to send to {email}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
    
    return {
        'sent': sent_count,
        'failed': failed_count,
        'total_emails': len(email_groups),
        'errors': errors
    }


@shared_task(bind=True, max_retries=3)
def update_stock_prices_task(self):
    """
    Background task to update stock prices for all active subscriptions
    Can be run independently of the notification task
    """
    try:
        logger.info("Starting stock prices update task")
        
        subscriptions = StockSubscription.objects.filter(is_active=True)
        _update_stock_prices(subscriptions)
        
        return {'message': 'Stock prices updated successfully'}
        
    except Exception as exc:
        logger.error(f"Stock prices update task failed: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))