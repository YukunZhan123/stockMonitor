from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from subscriptions.models import StockSubscription
from subscriptions.services import NotificationService


class Command(BaseCommand):
    help = 'Send scheduled stock price notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker',
            type=str,
            help='Send notifications for specific ticker only',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Send notifications for specific user only',
        )
        parser.add_argument(
            '--min-interval',
            type=int,
            default=60,
            help='Minimum minutes since last notification (default: 60)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send notifications regardless of last send time',
        )

    def handle(self, *args, **options):
        notification_service = NotificationService()
        
        # Build query for subscriptions that need notifications
        queryset = StockSubscription.objects.filter(
            is_active=True,
            stock_price__isnull=False  # Only send if we have current price
        ).select_related('user')
        
        if options['ticker']:
            queryset = queryset.filter(stock_ticker=options['ticker'].upper())
            
        if options['user_id']:
            queryset = queryset.filter(user_id=options['user_id'])
            
        if not options['force']:
            # Only send if enough time has passed since last notification
            cutoff_time = timezone.now() - timedelta(minutes=options['min_interval'])
            queryset = queryset.filter(
                last_notification_sent__lt=cutoff_time
            ) | queryset.filter(last_notification_sent__isnull=True)
        
        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No subscriptions found matching criteria')
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would send {total_count} notifications')
            )
            for subscription in queryset:
                self.stdout.write(
                    f'  EMAIL {subscription.user.username} - {subscription.stock_ticker} '
                    f'({subscription.price_display}) -> {subscription.email}'
                )
            return
        
        self.stdout.write(f'Sending notifications for {total_count} subscriptions...')
        
        # Send notifications
        results = notification_service.send_bulk_notifications(queryset)
        
        # Display results
        self.stdout.write(
            self.style.SUCCESS(
                f'\nBulk send complete: '
                f'{results["sent"]} sent, {results["failed"]} failed'
            )
        )
        
        if results['sent'] > 0:
            self.stdout.write(f'Successfully sent {results["sent"]} notifications')
            
        if results['failed'] > 0:
            self.stdout.write(
                self.style.ERROR(f'{results["failed"]} notifications failed:')
            )
            for error in results['errors']:
                self.stdout.write(f'  • {error}')
        
        # Show some statistics
        if results['sent'] > 0:
            self.stdout.write('\nNotification Stats:')
            sent_subscriptions = queryset.filter(
                last_notification_sent__gte=timezone.now() - timedelta(minutes=5)
            ).values_list('stock_ticker', flat=True)
            
            from collections import Counter
            ticker_counts = Counter(sent_subscriptions)
            
            for ticker, count in ticker_counts.most_common():
                self.stdout.write(f'  {ticker}: {count} notifications')
                
        self.stdout.write(
            f'\nNext run: python manage.py send_notifications --min-interval {options["min_interval"]}'
        )