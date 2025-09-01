#!/usr/bin/env python
"""
Script to manually create/update the periodic task in the database
Run this if the scheduler isn't automatically creating the task
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stocksubscription.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, CrontabSchedule

def create_notification_task():
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
        print("[OK] Created new crontab schedule: every minute")
    else:
        print("[OK] Using existing crontab schedule")
    
    # Delete old task if it exists
    old_task = PeriodicTask.objects.filter(name='send-hourly-notifications').first()
    if old_task:
        old_task.delete()
        print("[DELETE] Deleted old hourly task")
    
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
        print("[OK] Created new periodic task: send-minute-notifications")
    else:
        print("[OK] Updated existing periodic task")
    
    print(f"[INFO] Task details:")
    print(f"  - Name: {task.name}")
    print(f"  - Enabled: {task.enabled}")
    print(f"  - Schedule: {task.crontab}")
    print(f"  - Total runs: {task.total_run_count}")
    print(f"  - Last run: {task.last_run_at}")

if __name__ == '__main__':
    create_notification_task()