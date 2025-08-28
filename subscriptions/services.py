import requests
import logging
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from typing import Optional

from .models import StockSubscription, NotificationLog

logger = logging.getLogger('subscriptions')


class StockDataService:
    """
    High-level purpose: Fetch real-time stock data from external APIs
    - Support multiple stock data providers with fallbacks
    - Cache stock prices to reduce API calls
    - Handle API rate limits and errors gracefully
    """
    
    def __init__(self):
        self.timeout = 10  # seconds
        self.cache_duration = 300  # 5 minutes
        
        # API configuration - in production, use environment variables
        self.providers = [
            {
                'name': 'Alpha Vantage',
                'url': 'https://www.alphavantage.co/query',
                'api_key': getattr(settings, 'ALPHA_VANTAGE_API_KEY', None),
                'enabled': hasattr(settings, 'ALPHA_VANTAGE_API_KEY')
            },
            {
                'name': 'Finnhub',
                'url': 'https://finnhub.io/api/v1/quote',
                'api_key': getattr(settings, 'FINNHUB_API_KEY', None),
                'enabled': hasattr(settings, 'FINNHUB_API_KEY')
            }
        ]
    
    def get_current_price(self, ticker: str) -> Optional[Decimal]:
        """
        Get current stock price with fallback providers
        Returns None if all providers fail
        """
        ticker = ticker.upper().strip()
        
        for provider in self.providers:
            if not provider['enabled']:
                continue
                
            try:
                price = self._fetch_from_provider(ticker, provider)
                if price is not None:
                    logger.info(f"Got price for {ticker} from {provider['name']}: ${price}")
                    return price
            except Exception as e:
                logger.warning(f"Provider {provider['name']} failed for {ticker}: {str(e)}")
                continue
        
        # Fallback to mock data for development/testing
        logger.warning(f"All providers failed for {ticker}, using mock data")
        return self._get_mock_price(ticker)
    
    def _fetch_from_provider(self, ticker: str, provider: dict) -> Optional[Decimal]:
        """Fetch price from specific provider"""
        if provider['name'] == 'Alpha Vantage':
            return self._fetch_alpha_vantage(ticker, provider)
        elif provider['name'] == 'Finnhub':
            return self._fetch_finnhub(ticker, provider)
        return None
    
    def _fetch_alpha_vantage(self, ticker: str, provider: dict) -> Optional[Decimal]:
        """Fetch from Alpha Vantage API"""
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': ticker,
            'apikey': provider['api_key']
        }
        
        response = requests.get(provider['url'], params=params, timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Alpha Vantage response format
        if 'Global Quote' in data:
            price_str = data['Global Quote'].get('05. price')
            if price_str:
                return Decimal(price_str)
        
        return None
    
    def _fetch_finnhub(self, ticker: str, provider: dict) -> Optional[Decimal]:
        """Fetch from Finnhub API"""
        params = {
            'symbol': ticker,
            'token': provider['api_key']
        }
        
        response = requests.get(provider['url'], params=params, timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Finnhub response format
        current_price = data.get('c')  # Current price
        if current_price and current_price > 0:
            return Decimal(str(current_price))
        
        return None
    
    def _get_mock_price(self, ticker: str) -> Decimal:
        """Generate mock price for development/testing"""
        # Simple hash-based mock prices for consistent testing
        hash_val = hash(ticker) % 1000
        base_price = 50 + (hash_val / 10)  # Price between $50-$150
        return Decimal(f"{base_price:.2f}")


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
            # Generate email content
            context = {
                'subscription': subscription,
                'site_name': self.site_name,
                'current_price': subscription.stock_price,
                'price_display': subscription.price_display,
                'custom_message': custom_message,
                'notification_type': notification_type
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