"""
Celery Tasks for Automated Billing
Handles scheduled billing processes and overdue payment checks
"""

from celery import Celery
from datetime import datetime, timedelta
import asyncio

import sys
sys.path.append('/packages')

from common.logging import get_logger
from services.billing_manager import billing_manager

logger = get_logger(__name__)

# Initialize Celery (this would be configured with your Redis/RabbitMQ broker)
celery_app = Celery('winu_billing', broker='redis://localhost:6379/0')


@celery_app.task
def run_monthly_billing_task():
    """Celery task to run monthly billing process."""
    try:
        logger.info("Starting monthly billing task...")
        
        # Run the async billing process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(billing_manager.process_monthly_billing())
        loop.close()
        
        logger.info(f"Monthly billing task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in monthly billing task: {e}")
        return {"error": str(e)}


@celery_app.task
def check_overdue_payments_task():
    """Celery task to check for overdue payments."""
    try:
        logger.info("Starting overdue payments check task...")
        
        # Run the async overdue check process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(billing_manager._check_overdue_payments())
        loop.close()
        
        logger.info(f"Overdue payments check task completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in overdue payments check task: {e}")
        return {"error": str(e)}


@celery_app.task
def send_payment_reminders_task():
    """Celery task to send payment reminders."""
    try:
        logger.info("Starting payment reminders task...")
        
        # This would send reminders to users whose payments are due soon
        # Implementation depends on your notification system
        
        logger.info("Payment reminders task completed")
        return {"success": True, "reminders_sent": 0}
        
    except Exception as e:
        logger.error(f"Error in payment reminders task: {e}")
        return {"error": str(e)}


@celery_app.task
def cleanup_expired_trials_task():
    """Celery task to clean up expired trials."""
    try:
        logger.info("Starting expired trials cleanup task...")
        
        # This would handle users whose trials have expired
        # and ensure they can't access the system
        
        logger.info("Expired trials cleanup task completed")
        return {"success": True, "trials_cleaned": 0}
        
    except Exception as e:
        logger.error(f"Error in expired trials cleanup task: {e}")
        return {"error": str(e)}


# Schedule tasks (these would be configured in your Celery beat schedule)
CELERY_BEAT_SCHEDULE = {
    'monthly-billing': {
        'task': 'apps.api.tasks.billing_tasks.run_monthly_billing_task',
        'schedule': 30.0,  # Run every 30 days
    },
    'overdue-payments-check': {
        'task': 'apps.api.tasks.billing_tasks.check_overdue_payments_task',
        'schedule': 86400.0,  # Run every 24 hours
    },
    'payment-reminders': {
        'task': 'apps.api.tasks.billing_tasks.send_payment_reminders_task',
        'schedule': 86400.0,  # Run every 24 hours
    },
    'cleanup-expired-trials': {
        'task': 'apps.api.tasks.billing_tasks.cleanup_expired_trials_task',
        'schedule': 3600.0,  # Run every hour
    },
}

# Configure Celery
celery_app.conf.update(
    beat_schedule=CELERY_BEAT_SCHEDULE,
    timezone='UTC',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_expires=3600,
)













