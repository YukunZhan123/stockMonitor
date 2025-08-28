from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from subscriptions.models import StockSubscription
from subscriptions.services import StockDataService


class Command(BaseCommand):
    help = 'Refresh stock prices for all active subscriptions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker',
            type=str,
            help='Refresh prices for specific ticker only',
        )
        parser.add_argument(
            '--max-age',
            type=int,
            default=60,
            help='Only refresh prices older than this many minutes (default: 60)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Refresh all prices regardless of age',
        )

    def handle(self, *args, **options):
        stock_service = StockDataService()
        
        # Build query
        queryset = StockSubscription.objects.filter(is_active=True)
        
        if options['ticker']:
            queryset = queryset.filter(stock_ticker=options['ticker'].upper())
            
        if not options['force']:
            # Only refresh prices older than max_age minutes
            cutoff_time = timezone.now() - timedelta(minutes=options['max_age'])
            queryset = queryset.filter(
                Q(updated_at__lt=cutoff_time) | Q(stock_price__isnull=True)
            )
        
        total_count = queryset.count()
        if total_count == 0:
            self.stdout.write(
                self.style.WARNING('No subscriptions found matching criteria')
            )
            return
        
        self.stdout.write(f'Refreshing prices for {total_count} subscriptions...')
        
        updated_count = 0
        error_count = 0
        
        # Group by ticker to reduce API calls
        tickers = queryset.values_list('stock_ticker', flat=True).distinct()
        price_cache = {}
        
        # Fetch prices for unique tickers
        for ticker in tickers:
            try:
                price = stock_service.get_current_price(ticker)
                if price:
                    price_cache[ticker] = price
                    self.stdout.write(f'  {ticker}: ${price}')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  {ticker}: Price not available')
                    )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  {ticker}: Error - {str(e)}')
                )
        
        # Update subscriptions with cached prices
        for subscription in queryset.select_related('user'):
            ticker = subscription.stock_ticker
            if ticker in price_cache:
                old_price = subscription.stock_price
                new_price = price_cache[ticker]
                
                subscription.stock_price = new_price
                subscription.save(update_fields=['stock_price', 'updated_at'])
                updated_count += 1
                
                if old_price != new_price:
                    if new_price > (old_price or 0):
                        change = "UP"
                    elif new_price < (old_price or 0):
                        change = "DOWN"
                    else:
                        change = "SAME"
                    self.stdout.write(
                        f'  Updated {subscription.user.username}\'s {ticker}: '
                        f'${old_price or "N/A"} -> ${new_price} ({change})'
                    )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nRefresh complete: {updated_count} updated, {error_count} errors'
            )
        )
        
        if updated_count > 0:
            self.stdout.write(
                f'Use "python manage.py send_notifications" to send updated prices to users'
            )