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
    logger.info("📅 Schedule: Every 60 seconds")
    
    # Run immediately on startup
    run_notifications()
    
    # Then run every minute
    while True:
        try:
            # Sleep for 60 seconds (1 minute)
            time.sleep(60)
            
            # Run notifications
            run_notifications()
            
        except KeyboardInterrupt:
            logger.info("📴 Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"💥 Unexpected error in scheduler: {str(e)}")
            # Continue running even if there's an error
            time.sleep(10)  # Wait 10 seconds before retrying

if __name__ == '__main__':
    main()