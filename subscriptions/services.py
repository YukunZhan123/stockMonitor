import requests
import logging
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.cache import cache
from typing import Optional, Dict, Any
import json

from .models import StockSubscription, NotificationLog
from .ai_analysis import StockAnalysisService

logger = logging.getLogger('subscriptions')


class StockDataService:
    """
    Simple Yahoo Finance API integration
    """
    
    def __init__(self):
        self.cache_duration = 300  # 5 minutes
    
    def get_current_price(self, ticker: str) -> Optional[Decimal]:
        """
        Get current stock price from Yahoo Finance API
        """
        ticker = ticker.upper().strip()
        
        # Check cache first
        cache_key = f"stock_price_{ticker}"
        cached_price = cache.get(cache_key)
        if cached_price is not None:
            logger.info(f"Got cached price for {ticker}: ${cached_price}")
            return Decimal(str(cached_price))
        
        try:
            # Use Yahoo Finance quote API directly
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'chart' in data and 'result' in data['chart'] and data['chart']['result']:
                result = data['chart']['result'][0]
                
                # Get the latest price
                if 'meta' in result and 'regularMarketPrice' in result['meta']:
                    price = result['meta']['regularMarketPrice']
                    if price and price > 0:
                        price_decimal = Decimal(str(price))
                        # Cache for 5 minutes
                        cache.set(cache_key, float(price_decimal), self.cache_duration)
                        logger.info(f"Got price for {ticker}: ${price_decimal}")
                        return price_decimal
                        
        except Exception as e:
            logger.warning(f"Yahoo Finance API failed for {ticker}: {str(e)}")
        
        return None
    
    def validate_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Simple ticker validation - just try to get a price
        """
        ticker = ticker.upper().strip()
        
        # Check cache first
        cache_key = f"ticker_validation_{ticker}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Just try to get the price - if it works, ticker is valid
        price = self.get_current_price(ticker)
        
        if price:
            result = {
                'valid': True,
                'symbol': ticker,
                'price': float(price)
            }
        else:
            result = {
                'valid': False,
                'error': 'Invalid ticker symbol'
            }
        
        # Cache result for 15 minutes
        cache.set(cache_key, result, self.cache_duration * 3)
        return result


class NotificationService:
    """
    High-level purpose: Handle email notifications for stock subscriptions
    - Send formatted stock price emails
    - Track notification history and status
    - Support different notification types (scheduled, manual, alerts)
    - Handle email delivery failures gracefully
    """
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@stockmonitor.com')
        self.site_name = getattr(settings, 'SITE_NAME', 'Stock Monitor')
        self.ai_service = StockAnalysisService()
    
    def send_stock_notification(
        self, 
        subscription: StockSubscription,
        notification_type: str = 'scheduled',
        custom_message: Optional[str] = None
    ) -> NotificationLog:
        """
        Send email notification for stock subscription
        Returns NotificationLog instance with send status
        """
        
        # Create notification log entry
        notification_log = NotificationLog.objects.create(
            subscription=subscription,
            notification_type=notification_type,
            email_to=subscription.email,
            stock_price_at_send=subscription.stock_price,
            subject=self._generate_subject(subscription),
            status='pending'
        )
        
        try:
            # Get AI recommendation for the stock
            ai_recommendation = self.ai_service.get_stock_recommendation(
                subscription.stock_ticker, 
                subscription.stock_price
            )
            
            # Generate email content
            context = {
                'subscription': subscription,
                'site_name': self.site_name,
                'current_price': subscription.stock_price,
                'price_display': subscription.price_display,
                'custom_message': custom_message,
                'notification_type': notification_type,
                'ai_recommendation': ai_recommendation
            }
            
            # Generate HTML and text versions
            html_content = render_to_string('emails/stock_notification.html', context)
            text_content = render_to_string('emails/stock_notification.txt', context)
            
            # Send email
            success = send_mail(
                subject=notification_log.subject,
                message=text_content,
                from_email=self.from_email,
                recipient_list=[subscription.email],
                html_message=html_content,
                fail_silently=False
            )
            
            if success:
                # Update notification log
                notification_log.status = 'sent'
                notification_log.sent_at = timezone.now()
                
                # Update subscription tracking
                subscription.last_notification_sent = timezone.now()
                subscription.last_price_sent = subscription.stock_price
                subscription.save(update_fields=['last_notification_sent', 'last_price_sent'])
                
                logger.info(f"Notification sent successfully: {notification_log.id}")
            else:
                notification_log.status = 'failed'
                notification_log.error_message = 'Email send returned False'
                logger.error(f"Email send failed for notification: {notification_log.id}")
        
        except Exception as e:
            notification_log.status = 'failed'
            notification_log.error_message = str(e)
            logger.error(f"Email notification failed: {notification_log.id} - {str(e)}")
        
        finally:
            notification_log.save()
        
        return notification_log
    
    def _generate_subject(self, subscription: StockSubscription) -> str:
        """Generate email subject line"""
        if subscription.stock_price:
            return f"{subscription.stock_ticker} Stock Update - {subscription.price_display}"
        else:
            return f"{subscription.stock_ticker} Stock Update"
    
    def send_bulk_notifications(self, subscriptions_queryset) -> dict:
        """
        Send notifications for multiple subscriptions
        Returns summary of send results
        """
        results = {
            'total': subscriptions_queryset.count(),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for subscription in subscriptions_queryset:
            try:
                notification_log = self.send_stock_notification(subscription, 'scheduled')
                if notification_log.status == 'sent':
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{subscription.stock_ticker}: {notification_log.error_message}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{subscription.stock_ticker}: {str(e)}")
                logger.error(f"Bulk notification failed for {subscription.id}: {str(e)}")
        
        logger.info(f"Bulk notification complete: {results['sent']} sent, {results['failed']} failed")
        return results
    
    def send_merged_notification(
        self, 
        subscriptions: list,
        notification_type: str = 'scheduled',
        custom_message: Optional[str] = None
    ) -> NotificationLog:
        """
        Send single email with multiple stock subscriptions merged
        Used when user has multiple subscriptions to same email address
        """
        if not subscriptions:
            raise ValueError("No subscriptions provided")
        
        # Use first subscription as primary for logging purposes
        primary_subscription = subscriptions[0]
        email_address = primary_subscription.email
        
        # Create notification log entry (using primary subscription)
        notification_log = NotificationLog.objects.create(
            subscription=primary_subscription,
            notification_type=notification_type,
            email_to=email_address,
            stock_price_at_send=primary_subscription.stock_price,
            subject=self._generate_merged_subject(subscriptions),
            status='pending'
        )
        
        try:
            # Get AI recommendations for all stocks
            stock_data = {sub.stock_ticker: sub.stock_price for sub in subscriptions}
            ai_recommendations = self.ai_service.get_multiple_recommendations(stock_data)
            
            # Generate email content with multiple stocks
            context = {
                'subscriptions': subscriptions,
                'primary_subscription': primary_subscription,
                'site_name': self.site_name,
                'custom_message': custom_message,
                'notification_type': notification_type,
                'stock_count': len(subscriptions),
                'ai_recommendations': ai_recommendations
            }
            
            # Use merged email templates
            html_content = render_to_string('emails/stock_notification_merged.html', context)
            text_content = render_to_string('emails/stock_notification_merged.txt', context)
            
            # Send email
            success = send_mail(
                subject=notification_log.subject,
                message=text_content,
                from_email=self.from_email,
                recipient_list=[email_address],
                html_message=html_content,
                fail_silently=False
            )
            
            if success:
                # Update notification log
                notification_log.status = 'sent'
                notification_log.sent_at = timezone.now()
                
                # Update all subscriptions' last notification sent
                for subscription in subscriptions:
                    subscription.last_notification_sent = timezone.now()
                    subscription.last_price_sent = subscription.stock_price
                    subscription.save(update_fields=['last_notification_sent', 'last_price_sent'])
                
                logger.info(f"Merged notification sent: {len(subscriptions)} stocks to {email_address}")
            else:
                notification_log.status = 'failed'
                notification_log.error_message = 'Email send returned False'
                logger.error(f"Merged email send failed for: {email_address}")
        
        except Exception as e:
            notification_log.status = 'failed'
            notification_log.error_message = str(e)
            logger.error(f"Merged email notification failed: {email_address} - {str(e)}")
        
        finally:
            notification_log.save()
        
        return notification_log
    
    def _generate_merged_subject(self, subscriptions: list) -> str:
        """Generate subject line for merged email"""
        tickers = [sub.stock_ticker for sub in subscriptions]
        if len(tickers) <= 3:
            return f"Stock Updates: {', '.join(tickers)}"
        else:
            return f"Stock Updates: {', '.join(tickers[:2])} and {len(tickers)-2} more"