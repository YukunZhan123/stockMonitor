#!/usr/bin/env python
"""
Notification scheduler module - integrated with Django app startup
"""

import time
import logging
import subprocess
import sys
from datetime import datetime
import pytz

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

def start_notification_scheduler():
    """Main scheduler function - called from Django app startup"""
    logger.info("Notification scheduler starting as Django background service...")
    logger.info("Schedule: Every hour, Monday-Friday 9AM-5PM ET")
    
    while True:
        try:
            # Check business hours before running
            is_business, time_info = is_business_hours()
            
            if is_business:
                logger.info(f"[OK] {time_info} - Running notifications")
                run_notifications()
            else:
                logger.info(f"[SKIP] {time_info} - Skipping notifications")
            
            # Sleep for 1 hour before next run
            time.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error in scheduler: {str(e)}")
            # Continue running even if there's an error
            time.sleep(30)  # Wait 30 seconds before retrying