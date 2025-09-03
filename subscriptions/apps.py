from django.apps import AppConfig
import threading
import os


class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subscriptions'
    
    def ready(self):
        # Scheduler is now run as separate worker service in DigitalOcean
        # No need to start it from Django app
        pass
    
    def start_scheduler(self):
        """Start the notification scheduler in a background thread"""
        try:
            from .scheduler import start_notification_scheduler
            # Start scheduler in daemon thread so it doesn't prevent app shutdown
            scheduler_thread = threading.Thread(target=start_notification_scheduler, daemon=True)
            scheduler_thread.start()
            print("Notification scheduler started successfully")
        except Exception as e:
            print(f"Failed to start scheduler: {e}")