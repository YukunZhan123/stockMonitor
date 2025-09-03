#!/usr/bin/env python
"""
Notification scheduler module - integrated with Django app startup
"""

import time
import logging
import subprocess
import sys
from datetime import datetime, timedelta
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

def calculate_next_run_time():
    """Calculate next exact hour within business hours (9AM-5PM ET)"""
    now_et = datetime.now(EASTERN_TZ)
    
    # Start from next hour (round up to next hour boundary)
    next_hour = (now_et + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    
    # If we're past 5 PM or before 9 AM, schedule for 9 AM next business day
    if next_hour.hour > 17:  # After 5 PM
        # Move to 9 AM tomorrow
        next_business_day = next_hour + timedelta(days=1)
        next_run = next_business_day.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Skip weekends - move to Monday if it's Saturday/Sunday
        while next_run.weekday() >= 5:  # Saturday=5, Sunday=6
            next_run += timedelta(days=1)
            
    elif next_hour.hour < 9:  # Before 9 AM
        # Schedule for 9 AM today (if weekday) or next Monday
        next_run = next_hour.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Skip weekends
        while next_run.weekday() >= 5:
            next_run += timedelta(days=1)
            
    else:  # Between 9 AM and 5 PM
        next_run = next_hour
        
        # Skip weekends
        while next_run.weekday() >= 5:
            next_run += timedelta(days=1)
            next_run = next_run.replace(hour=9)  # Start at 9 AM on Monday
    
    return next_run

def start_notification_scheduler():
    """Main scheduler function - sends at exact hours: 9:00, 10:00, 11:00, etc."""
    logger.info("Notification scheduler starting as Django background service...")
    logger.info("Schedule: Every hour on the hour, Monday-Friday 9AM-5PM ET")
    
    while True:
        try:
            # Calculate next exact run time
            next_run = calculate_next_run_time()
            now_et = datetime.now(EASTERN_TZ)
            
            # Calculate sleep time until next exact hour
            sleep_seconds = (next_run - now_et).total_seconds()
            
            if sleep_seconds > 0:
                logger.info(f"Next notification scheduled for: {next_run.strftime('%A %I:%M %p %Z')}")
                logger.info(f"Sleeping for {int(sleep_seconds/60)} minutes...")
                time.sleep(sleep_seconds)
            
            # Check if we're still in business hours (in case time changed)
            is_business, time_info = is_business_hours()
            
            if is_business:
                logger.info(f"[OK] {time_info} - Running notifications")
                run_notifications()
            else:
                logger.info(f"[SKIP] {time_info} - Outside business hours, recalculating next run")
                continue  # Recalculate next run time
            
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error in scheduler: {str(e)}")
            # Continue running even if there's an error
            time.sleep(60)  # Wait 1 minute before retrying