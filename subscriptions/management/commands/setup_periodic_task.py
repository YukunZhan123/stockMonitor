from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule


class Command(BaseCommand):
    help = 'Create or update the periodic notification task'

    def handle(self, *args, **options):
        # Create or get the crontab schedule (every minute)
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute='*',
            hour='*',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='America/New_York'
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('[OK] Created new crontab schedule: every minute'))
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Using existing crontab schedule'))
        
        # Delete old task if it exists
        old_task = PeriodicTask.objects.filter(name='send-hourly-notifications').first()
        if old_task:
            old_task.delete()
            self.stdout.write(self.style.WARNING('[DELETE] Deleted old hourly task'))
        
        # Create or update the periodic task
        task, created = PeriodicTask.objects.update_or_create(
            name='send-minute-notifications',
            defaults={
                'task': 'subscriptions.tasks.send_periodic_notifications',
                'crontab': schedule,
                'enabled': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('[OK] Created new periodic task: send-minute-notifications'))
        else:
            self.stdout.write(self.style.SUCCESS('[OK] Updated existing periodic task'))
        
        self.stdout.write(self.style.SUCCESS(f"Task details:"))
        self.stdout.write(f"  - Name: {task.name}")
        self.stdout.write(f"  - Enabled: {task.enabled}")
        self.stdout.write(f"  - Schedule: {task.crontab}")
        self.stdout.write(f"  - Total runs: {task.total_run_count}")
        self.stdout.write(f"  - Last run: {task.last_run_at}")