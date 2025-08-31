import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stocksubscription.settings')

app = Celery('stocksubscription')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Periodic tasks configuration
from celery.schedules import crontab

app.conf.beat_schedule = {
    'send-hourly-stock-notifications': {
        'task': 'subscriptions.tasks.send_periodic_notifications',
        'schedule': crontab(
            minute=0,  # At the start of every hour
            hour='9-17',  # 9AM to 5PM (17 is 5PM in 24-hour format)
            day_of_week='1-5',  # Monday to Friday (1=Monday, 5=Friday)
        ),
        'options': {
            'timezone': 'America/New_York',  # Eastern Time
        }
    },
}

app.conf.timezone = 'America/New_York'