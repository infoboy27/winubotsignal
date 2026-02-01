"""
Automated Billing Manager for Subscription System
Handles monthly billing, payment reminders, and overdue payment processing
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User, PaymentTransaction, SubscriptionEvent, TelegramGroupAccess
from common.logging import get_logger

logger = get_logger(__name__)


class BillingManager:
    """Manages automated billing and payment processing."""
    
    def __init__(self):
        self.subscription_plans = {
            "professional": {
                "price_usd": 14.99,
                "price_usdt": 14.99,
                "interval_days": 30
            },
            "vip_elite": {
                "price_usd": 29.99,
                "price_usdt": 29.99,
                "interval_days": 30
            }
        }
    
    async def process_monthly_billing(self, db: AsyncSession) -> Dict[str, Any]:
        """Process monthly billing for all active subscribers."""
        try:
            logger.info("Starting monthly billing process...")
            
            # Get all users with active paid subscriptions
            result = await db.execute(
                select(User).where(
                    User.subscription_tier.in_(["professional", "vip_elite"]),
                    User.subscription_status == "active"
                )
            )
            active_users = result.scalars().all()
            
            billing_results = {
                "total_users": len(active_users),
                "successful_billings": 0,
                "failed_billings": 0,
                "overdue_users": 0,
                "errors": []
            }
            
            for user in active_users:
                try:
                    await self._process_user_billing(user, db)
                    billing_results["successful_billings"] += 1
                except Exception as e:
                    logger.error(f"Billing failed for user {user.id}: {e}")
                    billing_results["failed_billings"] += 1
                    billing_results["errors"].append(f"User {user.id}: {str(e)}")
            
            # Check for overdue payments
            overdue_result = await self._check_overdue_payments(db)
            billing_results["overdue_users"] = overdue_result["overdue_count"]
            
            logger.info(f"Monthly billing completed: {billing_results}")
            return billing_results
            
        except Exception as e:
            logger.error(f"Error in monthly billing process: {e}")
            return {"error": str(e)}
    
    async def _process_user_billing(self, user: User, db: AsyncSession):
        """Process billing for a single user."""
        try:
            # Calculate next payment date
            if user.payment_due_date:
                # User already has a payment due date, extend it
                next_payment_date = user.payment_due_date + timedelta(days=30)
            else:
                # Set first payment due date
                next_payment_date = datetime.utcnow() + timedelta(days=30)
            
            # Update user's payment due date
            user.payment_due_date = next_payment_date
            user.subscription_renewal_date = next_payment_date
            
            # Create billing event
            event = SubscriptionEvent(
                user_id=user.id,
                event_type="billing_generated",
                event_data={
                    "payment_due_date": next_payment_date.isoformat(),
                    "amount_usdt": self.subscription_plans[user.subscription_tier]["price_usdt"],
                    "subscription_tier": user.subscription_tier,
                    "billing_cycle": "monthly"
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            # Send payment reminder
            await self._send_payment_reminder(user, next_payment_date)
            
            # Schedule overdue check
            await self._schedule_overdue_check(user, next_payment_date + timedelta(days=7))
            
            logger.info(f"Billing processed for user {user.id}, next payment due: {next_payment_date}")
            
        except Exception as e:
            logger.error(f"Error processing billing for user {user.id}: {e}")
            await db.rollback()
            raise
    
    async def _check_overdue_payments(self, db: AsyncSession) -> Dict[str, Any]:
        """Check for overdue payments and handle them."""
        try:
            # Get users with overdue payments
            overdue_date = datetime.utcnow() - timedelta(days=1)  # 1 day grace period
            
            result = await db.execute(
                select(User).where(
                    and_(
                        User.subscription_tier.in_(["professional", "vip_elite"]),
                        User.payment_due_date < overdue_date,
                        User.access_revoked_at.is_(None)  # Not already revoked
                    )
                )
            )
            overdue_users = result.scalars().all()
            
            overdue_results = {
                "overdue_count": len(overdue_users),
                "processed_users": 0,
                "errors": []
            }
            
            for user in overdue_users:
                try:
                    await self._handle_overdue_payment(user, db)
                    overdue_results["processed_users"] += 1
                except Exception as e:
                    logger.error(f"Error handling overdue payment for user {user.id}: {e}")
                    overdue_results["errors"].append(f"User {user.id}: {str(e)}")
            
            return overdue_results
            
        except Exception as e:
            logger.error(f"Error checking overdue payments: {e}")
            return {"error": str(e)}
    
    async def _handle_overdue_payment(self, user: User, db: AsyncSession):
        """Handle overdue payment - revoke access and send notifications."""
        try:
            # Revoke dashboard access
            user.access_revoked_at = datetime.utcnow()
            user.subscription_status = "past_due"
            
            # Revoke Telegram group access
            await self._revoke_telegram_access(user, db)
            
            # Create overdue event
            event = SubscriptionEvent(
                user_id=user.id,
                event_type="access_revoked",
                event_data={
                    "reason": "payment_overdue",
                    "revoked_at": user.access_revoked_at.isoformat(),
                    "subscription_tier": user.subscription_tier,
                    "payment_due_date": user.payment_due_date.isoformat() if user.payment_due_date else None
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            # Send overdue notification
            await self._send_overdue_notification(user)
            
            logger.info(f"Access revoked for user {user.id} due to overdue payment")
            
        except Exception as e:
            logger.error(f"Error handling overdue payment for user {user.id}: {e}")
            await db.rollback()
            raise
    
    async def _revoke_telegram_access(self, user: User, db: AsyncSession):
        """Revoke Telegram group access for user."""
        try:
            # Update Telegram group access records
            result = await db.execute(
                select(TelegramGroupAccess).where(
                    TelegramGroupAccess.user_id == user.id,
                    TelegramGroupAccess.is_active == True
                )
            )
            telegram_accesses = result.scalars().all()
            
            for access in telegram_accesses:
                access.is_active = False
                access.access_revoked_at = datetime.utcnow()
            
            logger.info(f"Telegram access revoked for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error revoking Telegram access for user {user.id}: {e}")
            raise
    
    async def _send_payment_reminder(self, user: User, payment_due_date: datetime):
        """Send payment reminder to user."""
        try:
            # This would integrate with your notification system (email, SMS, etc.)
            logger.info(f"Payment reminder sent to user {user.id} for payment due: {payment_due_date}")
            
            # Example: Send email notification
            # await email_service.send_payment_reminder(user.email, payment_due_date)
            
        except Exception as e:
            logger.error(f"Error sending payment reminder to user {user.id}: {e}")
    
    async def _send_overdue_notification(self, user: User):
        """Send overdue payment notification to user."""
        try:
            # This would integrate with your notification system
            logger.info(f"Overdue notification sent to user {user.id}")
            
            # Example: Send urgent email notification
            # await email_service.send_overdue_notification(user.email)
            
        except Exception as e:
            logger.error(f"Error sending overdue notification to user {user.id}: {e}")
    
    async def _schedule_overdue_check(self, user: User, check_date: datetime):
        """Schedule overdue payment check for user."""
        try:
            # This would integrate with your task scheduler (Celery, etc.)
            logger.info(f"Overdue check scheduled for user {user.id} on {check_date}")
            
            # Example: Schedule Celery task
            # check_overdue_payment.apply_async(args=[user.id], eta=check_date)
            
        except Exception as e:
            logger.error(f"Error scheduling overdue check for user {user.id}: {e}")
    
    async def restore_access_after_payment(self, user: User, db: AsyncSession):
        """Restore user access after successful payment."""
        try:
            # Clear access revocation
            user.access_revoked_at = None
            user.subscription_status = "active"
            user.last_payment_date = datetime.utcnow()
            
            # Restore Telegram access if applicable
            if user.subscription_tier in ["professional", "vip_elite"]:
                await self._restore_telegram_access(user, db)
            
            # Create restoration event
            event = SubscriptionEvent(
                user_id=user.id,
                event_type="access_restored",
                event_data={
                    "reason": "payment_completed",
                    "restored_at": datetime.utcnow().isoformat(),
                    "subscription_tier": user.subscription_tier
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            logger.info(f"Access restored for user {user.id} after payment")
            
        except Exception as e:
            logger.error(f"Error restoring access for user {user.id}: {e}")
            await db.rollback()
            raise
    
    async def _restore_telegram_access(self, user: User, db: AsyncSession):
        """Restore Telegram group access for user."""
        try:
            # Check if user already has active Telegram access
            result = await db.execute(
                select(TelegramGroupAccess).where(
                    TelegramGroupAccess.user_id == user.id,
                    TelegramGroupAccess.is_active == True
                )
            )
            existing_access = result.scalar_one_or_none()
            
            if not existing_access and user.telegram_user_id:
                # Create new Telegram access
                telegram_access = TelegramGroupAccess(
                    user_id=user.id,
                    telegram_user_id=user.telegram_user_id,
                    telegram_username=getattr(user, 'telegram_username', None),
                    group_name=f"{user.subscription_tier}_group",
                    is_active=True
                )
                db.add(telegram_access)
            
            logger.info(f"Telegram access restored for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error restoring Telegram access for user {user.id}: {e}")
            raise
    
    async def get_billing_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get billing statistics and metrics."""
        try:
            # Get subscription counts
            result = await db.execute(
                select(User.subscription_tier, User.subscription_status)
            )
            users = result.all()
            
            stats = {
                "total_users": len(users),
                "subscription_tiers": {},
                "subscription_status": {},
                "revenue_metrics": {
                    "monthly_recurring_revenue": 0,
                    "active_subscribers": 0,
                    "trial_users": 0,
                    "overdue_users": 0
                }
            }
            
            # Count by tier and status
            for tier, status in users:
                # Tier counts
                if tier not in stats["subscription_tiers"]:
                    stats["subscription_tiers"][tier] = 0
                stats["subscription_tiers"][tier] += 1
                
                # Status counts
                if status not in stats["subscription_status"]:
                    stats["subscription_status"][status] = 0
                stats["subscription_status"][status] += 1
                
                # Revenue calculations
                if tier in ["professional", "vip_elite"] and status == "active":
                    stats["revenue_metrics"]["active_subscribers"] += 1
                    if tier == "professional":
                        stats["revenue_metrics"]["monthly_recurring_revenue"] += 14.99
                    elif tier == "vip_elite":
                        stats["revenue_metrics"]["monthly_recurring_revenue"] += 29.99
                
                if tier == "free":
                    stats["revenue_metrics"]["trial_users"] += 1
                
                if status == "past_due":
                    stats["revenue_metrics"]["overdue_users"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting billing statistics: {e}")
            return {"error": str(e)}


# Global instance
billing_manager = BillingManager()


async def run_monthly_billing():
    """Run monthly billing process (to be called by scheduler)."""
    try:
        from dependencies import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            result = await billing_manager.process_monthly_billing(db)
            logger.info(f"Monthly billing completed: {result}")
            return result
            
    except Exception as e:
        logger.error(f"Error in monthly billing: {e}")
        return {"error": str(e)}


async def check_overdue_payments():
    """Check for overdue payments (to be called by scheduler)."""
    try:
        from dependencies import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            result = await billing_manager._check_overdue_payments(db)
            logger.info(f"Overdue payment check completed: {result}")
            return result
            
    except Exception as e:
        logger.error(f"Error checking overdue payments: {e}")
        return {"error": str(e)}













