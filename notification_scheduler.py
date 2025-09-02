#!/usr/bin/env python
"""
Simple notification scheduler - runs as a worker service
Calls the Django management command on schedule
"""

import os
import sys
import time
import logging
import subprocess
from datetime import datetime
import pytz
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stocksubscription.settings')
django.setup()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Eastern Time timezone
EASTERN_TZ = pytz.timezone('US/Eastern')

def is_business_hours():
    """Check if current time is within business hours (Mon-Fri, 9AM-5PM ET)"""
    now_et = datetime.now(EASTERN_TZ)
    
    # Check if it's a weekday (0=Monday, 6=Sunday)
    if now_et.weekday() >= 5:  # Saturday or Sunday
        return False, f"Weekend - {now_et.strftime('%A')}"
    
    # Check if it's between 9 AM and 5 PM
    hour = now_et.hour
    if hour < 9 or hour >= 17:  # Before 9 AM or after 5 PM
        return False, f"Outside hours - {now_et.strftime('%I:%M %p %Z')}"
    
    return True, f"Business hours - {now_et.strftime('%A %I:%M %p %Z')}"

def run_notifications():
    """Run the Django management command"""
    try:
        logger.info("Starting notification run...")
        
        # Run the Django management command
        result = subprocess.run([
            sys.executable, 'manage.py', 'send_notifications'
        ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            logger.info("Notification run completed successfully")
            if result.stdout:
                logger.info(f"Output: {result.stdout.strip()}")
        else:
            logger.error(f"Notification run failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr.strip()}")
                
    except subprocess.TimeoutExpired:
        logger.error("Notification run timed out after 5 minutes")
    except Exception as e:
        logger.error(f"Error running notifications: {str(e)}")

def main():
    """Main scheduler loop"""
    logger.info("🚀 Notification scheduler starting...")
    logger.info("📅 Schedule: Every hour during business hours (Mon-Fri, 9AM-5PM ET)")
    
    last_run_hour = None
    
    while True:
        try:
            # Check if we're in business hours
            is_business, time_info = is_business_hours()
            now_et = datetime.now(EASTERN_TZ)
            current_hour = now_et.hour
            
            if is_business:
                # Only run once per hour (at the top of each hour)
                if last_run_hour != current_hour:
                    logger.info(f"✅ {time_info} - Running notifications")
                    run_notifications()
                    last_run_hour = current_hour
                else:
                    logger.debug(f"⏳ {time_info} - Already ran this hour, waiting...")
            else:
                logger.info(f"⏸️  {time_info} - Skipping notifications")
                # Reset the hour tracker when outside business hours
                last_run_hour = None
            
            # Sleep for 5 minutes before checking again
            time.sleep(300)  # 5 minutes
            
        except KeyboardInterrupt:
            logger.info("📴 Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"💥 Unexpected error in scheduler: {str(e)}")
            # Continue running even if there's an error
            time.sleep(30)  # Wait 30 seconds before retrying

if __name__ == '__main__':
    main()