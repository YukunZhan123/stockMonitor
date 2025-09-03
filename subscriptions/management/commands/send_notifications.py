from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from collections import defaultdict
import logging

from subscriptions.models import StockSubscription, NotificationLog
from subscriptions.services import StockDataService, NotificationService

logger = logging.getLogger('subscriptions')


class Command(BaseCommand):
    help = 'Send periodic stock price notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually sending notifications',
        )

    def handle(self, *args, **options):
        """
        Send stock price notifications - simplified version without Celery
        """
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'[{timezone.now()}] Starting periodic stock notifications')
        )
        
        try:
            # Get all active subscriptions
            subscriptions = StockSubscription.objects.filter(is_active=True).select_related('user')
            
            if not subscriptions.exists():
                self.stdout.write(
                    self.style.WARNING('No active subscriptions found')
                )
                return
            
            self.stdout.write(f'Found {subscriptions.count()} active subscriptions')
            
            # Initialize services
            stock_service = StockDataService()
            notification_service = NotificationService()
            
            # Group subscriptions by email address to merge notifications
            user_subscriptions = defaultdict(list)
            for subscription in subscriptions:
                user_subscriptions[subscription.user.email].append(subscription)
            
            total_sent = 0
            total_errors = 0
            
            # Process each user's subscriptions (ONE EMAIL PER USER)
            for user_email, user_subs in user_subscriptions.items():
                user_sent_count = 0
                try:
                    if dry_run:
                        self.stdout.write(f'[DRY RUN] Would send merged notification to {user_email} for {len(user_subs)} stocks')
                        continue
                    
                    # Update stock prices for user's subscriptions
                    updated_stocks = []
                    for subscription in user_subs:
                        try:
                            # Get current stock price
                            current_price = stock_service.get_current_price(subscription.stock_ticker)
                            
                            if current_price is None:
                                self.stdout.write(f'⚠ No price data for {subscription.stock_ticker}')
                                continue
                            
                            # Update subscription with latest price
                            subscription.stock_price = current_price
                            subscription.updated_at = timezone.now()
                            subscription.save(update_fields=['stock_price', 'updated_at'])
                            
                            updated_stocks.append(subscription)
                            
                        except Exception as e:
                            logger.error(f"Failed to update stock {subscription.stock_ticker}: {str(e)}")
                            total_errors += 1
                            continue
                    
                    if not updated_stocks:
                        continue
                    
                    # Send ONE merged notification for all user's stocks
                    log_entry = notification_service.send_merged_notification(
                        subscriptions=updated_stocks,
                        notification_type='periodic'
                    )
                    
                    if log_entry and log_entry.status == 'sent':
                        total_sent += 1  # Count emails sent, not stocks
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Sent 1 merged email with {len(updated_stocks)} stocks to {user_email}')
                        )
                    else:
                        total_errors += 1
                        self.stdout.write(
                            self.style.ERROR(f'✗ Failed to send merged notification to {user_email}')
                        )
                
                except Exception as e:
                    logger.error(f"Error processing notifications for {user_email}: {str(e)}")
                    total_errors += 1
                    continue
            
            # Summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'Notification run completed: {total_sent} sent, {total_errors} errors'
                )
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('This was a dry run - no notifications were actually sent')
                )
                
        except Exception as e:
            logger.error(f"Critical error in send_notifications command: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Critical error: {str(e)}')
            )
            raise