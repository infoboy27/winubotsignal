"""
Enhanced Subscription Access Control Middleware
Supports Free Trial, Professional, and VIP Elite tiers with proper access control
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User, SubscriptionPlan, TelegramGroupAccess
from common.logging import get_logger
from common.schemas import SubscriptionAccessCheck

logger = get_logger(__name__)


class SubscriptionAccessController:
    """Enhanced subscription access control with trial logic."""
    
    def __init__(self):
        self.subscription_plans = {
            "free_trial": {
                "name": "Free Trial",
                "duration_days": 7,
                "dashboard_access_limit": 1,
                "telegram_access": False,
                "support_level": "none"
            },
            "professional": {
                "name": "Professional",
                "price_usd": 14.99,
                "interval": "monthly",
                "telegram_access": True,
                "support_level": "priority"
            },
            "vip_elite": {
                "name": "VIP Elite",
                "price_usd": 29.99,
                "interval": "monthly",
                "telegram_access": True,
                "support_level": "24/7"
            }
        }
    
    async def check_subscription_access(
        self,
        user: User,
        db: AsyncSession,
        access_type: str = "dashboard",  # dashboard, telegram, support, api
        increment_access_count: bool = False
    ) -> SubscriptionAccessCheck:
        """
        Check if user has valid subscription access.
        
        Args:
            user: User object
            db: Database session
            access_type: Type of access being requested (dashboard, telegram, support, api)
            increment_access_count: Whether to increment dashboard access count for trial users
        
        Returns:
            SubscriptionAccessCheck: Access check result with detailed information
        """
        try:
            # Admin users always have access
            if user.is_admin:
                return SubscriptionAccessCheck(
                    access=True,
                    reason="admin_access",
                    tier="admin",
                    message="Admin access granted"
                )
            
            # Check trial period
            if user.subscription_tier == "free" and not user.trial_used:
                return SubscriptionAccessCheck(
                    access=False,
                    reason="trial_not_started",
                    tier="free",
                    message="Please start your free trial to access the dashboard"
                )
            
            # Handle trial users
            if user.subscription_tier == "free" and user.trial_used:
                trial_result = await self._check_trial_access(
                    user, db, access_type, increment_access_count
                )
                return trial_result
            
            # Handle paid subscription users
            if user.subscription_tier in ["professional", "vip_elite"]:
                return await self._check_paid_subscription_access(user, db, access_type)
            
            # No valid subscription
            return SubscriptionAccessCheck(
                access=False,
                reason="no_subscription",
                tier="free",
                message="Please subscribe to Professional or VIP Elite to continue"
            )
            
        except Exception as e:
            logger.error(f"Error checking subscription access: {e}")
            return SubscriptionAccessCheck(
                access=False,
                reason="error",
                tier="unknown",
                message="An error occurred while checking access",
                errors=[str(e)]
            )
    
    async def _check_trial_access(
        self,
        user: User,
        db: AsyncSession,
        access_type: str,
        increment_access_count: bool
    ) -> SubscriptionAccessCheck:
        """Check trial access with proper limits."""
        
        # Start trial if not started
        if not user.trial_start_date:
            user.trial_start_date = datetime.utcnow()
            await db.commit()
            logger.info(f"Trial started for user {user.id}")
        
        # Calculate trial duration
        trial_duration = datetime.utcnow() - user.trial_start_date
        days_remaining = max(0, 7 - trial_duration.days)
        
        # Check if trial is expired
        if trial_duration.days >= 7:
            return SubscriptionAccessCheck(
                access=False,
                reason="trial_expired",
                tier="free_trial",
                message="Your 7-day free trial has expired. Please subscribe to continue.",
                trial_days_remaining=0
            )
        
        # Check dashboard access limit
        if access_type == "dashboard":
            if user.trial_dashboard_access_count >= 1:
                return SubscriptionAccessCheck(
                    access=False,
                    reason="trial_limit_exceeded",
                    tier="free_trial",
                    message="You have reached your 1-time dashboard access limit. Please subscribe to continue.",
                    trial_days_remaining=days_remaining,
                    dashboard_access_remaining=0
                )
            
            # Increment access count if requested
            if increment_access_count:
                user.trial_dashboard_access_count += 1
                await db.commit()
                logger.info(f"Dashboard access count incremented for user {user.id}: {user.trial_dashboard_access_count}")
            
            return SubscriptionAccessCheck(
                access=True,
                reason="trial_active",
                tier="free_trial",
                message="Trial access granted",
                trial_days_remaining=days_remaining,
                dashboard_access_remaining=1 - user.trial_dashboard_access_count
            )
        
        # Other access types not available in trial
        return SubscriptionAccessCheck(
            access=False,
            reason="trial_limited",
            tier="free_trial",
            message=f"{access_type} access not available in trial. Subscribe to unlock.",
            trial_days_remaining=days_remaining
        )
    
    async def _check_paid_subscription_access(
        self,
        user: User,
        db: AsyncSession,
        access_type: str
    ) -> SubscriptionAccessCheck:
        """Check paid subscription access."""
        
        # Check if payment is overdue
        if user.payment_due_date and user.payment_due_date < datetime.utcnow():
            # Check if access was already revoked
            if not user.access_revoked_at:
                # Revoke access
                await self._revoke_user_access(user, db)
            
            return SubscriptionAccessCheck(
                access=False,
                reason="payment_overdue",
                tier=user.subscription_tier,
                message="Your subscription payment is overdue. Please update your payment to restore access.",
                payment_due_date=user.payment_due_date
            )
        
        # Check specific access types
        if access_type == "dashboard":
            return SubscriptionAccessCheck(
                access=True,
                reason="paid_subscription",
                tier=user.subscription_tier,
                message=f"{user.subscription_tier.title()} subscription active"
            )
        
        elif access_type == "telegram":
            plan = self.subscription_plans.get(user.subscription_tier, {})
            if plan.get("telegram_access", False):
                return SubscriptionAccessCheck(
                    access=True,
                    reason="telegram_access_granted",
                    tier=user.subscription_tier,
                    message="Telegram group access granted"
                )
            else:
                return SubscriptionAccessCheck(
                    access=False,
                    reason="telegram_access_denied",
                    tier=user.subscription_tier,
                    message="Telegram access not available in your current plan"
                )
        
        elif access_type == "support":
            plan = self.subscription_plans.get(user.subscription_tier, {})
            support_level = plan.get("support_level", "none")
            return SubscriptionAccessCheck(
                access=True,
                reason="support_access_granted",
                tier=user.subscription_tier,
                message=f"{support_level} support access granted"
            )
        
        elif access_type == "api":
            # API access for VIP Elite only
            if user.subscription_tier == "vip_elite":
                return SubscriptionAccessCheck(
                    access=True,
                    reason="api_access_granted",
                    tier=user.subscription_tier,
                    message="API access granted"
                )
            else:
                return SubscriptionAccessCheck(
                    access=False,
                    reason="api_access_denied",
                    tier=user.subscription_tier,
                    message="API access available in VIP Elite plan only"
                )
        
        # Default access granted for paid subscribers
        return SubscriptionAccessCheck(
            access=True,
            reason="paid_subscription",
            tier=user.subscription_tier,
            message=f"{user.subscription_tier.title()} subscription active"
        )
    
    async def _revoke_user_access(self, user: User, db: AsyncSession):
        """Revoke user access due to overdue payment."""
        try:
            # Mark access as revoked
            user.access_revoked_at = datetime.utcnow()
            user.subscription_status = "past_due"
            
            # Revoke Telegram group access
            await self._revoke_telegram_access(user, db)
            
            # Create subscription event
            from common.database import SubscriptionEvent
            event = SubscriptionEvent(
                user_id=user.id,
                event_type="access_revoked",
                event_data={
                    "reason": "payment_overdue",
                    "revoked_at": user.access_revoked_at.isoformat(),
                    "subscription_tier": user.subscription_tier
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            logger.info(f"Access revoked for user {user.id} due to overdue payment")
            
        except Exception as e:
            logger.error(f"Error revoking user access: {e}")
            await db.rollback()
    
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
            logger.error(f"Error revoking Telegram access: {e}")
    
    async def get_user_subscription_info(self, user: User, db: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive subscription information for user."""
        try:
            # Get current plan
            plan_info = self.subscription_plans.get(user.subscription_tier, {})
            
            # Get Telegram access
            result = await db.execute(
                select(TelegramGroupAccess).where(
                    TelegramGroupAccess.user_id == user.id,
                    TelegramGroupAccess.is_active == True
                )
            )
            telegram_access = result.scalars().all()
            
            # Calculate trial info
            trial_info = {}
            if user.subscription_tier == "free" and user.trial_start_date:
                trial_duration = datetime.utcnow() - user.trial_start_date
                trial_info = {
                    "days_remaining": max(0, 7 - trial_duration.days),
                    "dashboard_access_remaining": max(0, 1 - user.trial_dashboard_access_count),
                    "trial_start_date": user.trial_start_date.isoformat(),
                    "is_expired": trial_duration.days >= 7
                }
            
            return {
                "subscription_tier": user.subscription_tier,
                "subscription_status": user.subscription_status,
                "trial_used": user.trial_used,
                "trial_info": trial_info,
                "payment_due_date": user.payment_due_date.isoformat() if user.payment_due_date else None,
                "access_revoked_at": user.access_revoked_at.isoformat() if user.access_revoked_at else None,
                "plan_info": plan_info,
                "telegram_access": [
                    {
                        "group_name": access.group_name,
                        "access_granted_at": access.access_granted_at.isoformat(),
                        "is_active": access.is_active
                    }
                    for access in telegram_access
                ],
                "last_payment_date": user.last_payment_date.isoformat() if user.last_payment_date else None,
                "payment_method": user.payment_method
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription info: {e}")
            return {"error": str(e)}


# Global instance
subscription_controller = SubscriptionAccessController()


def require_subscription(access_type: str = "dashboard", increment_access_count: bool = False):
    """
    Decorator to require subscription access for endpoints.
    
    Args:
        access_type: Type of access required (dashboard, telegram, support, api)
        increment_access_count: Whether to increment dashboard access count for trial users
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user and db from kwargs (assuming FastAPI dependency injection)
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check subscription access
            access_check = await subscription_controller.check_subscription_access(
                user, db, access_type, increment_access_count
            )
            
            if not access_check.access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": access_check.message,
                        "reason": access_check.reason,
                        "tier": access_check.tier,
                        "trial_days_remaining": access_check.trial_days_remaining,
                        "dashboard_access_remaining": access_check.dashboard_access_remaining
                    }
                )
            
            # Add access info to kwargs for the endpoint
            kwargs['subscription_info'] = access_check
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator













