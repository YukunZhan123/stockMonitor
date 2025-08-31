from django.core.management.base import BaseCommand
from subscriptions.tasks import send_periodic_notifications


class Command(BaseCommand):
    help = 'Test the periodic email notification system manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send even outside business hours',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Testing periodic email notifications...')
        )
        
        try:
            # Run the periodic task
            result = send_periodic_notifications()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Task completed successfully: {result}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Task failed: {str(e)}')
            )