"""Subscription access control middleware."""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User
from common.logging import get_logger

logger = get_logger(__name__)


async def check_subscription_access(
    user: User,
    db: AsyncSession,
    require_active: bool = True
) -> bool:
    """
    Check if user has valid subscription access.
    
    Args:
        user: User object
        db: Database session
        require_active: Whether to require active subscription (default: True)
    
    Returns:
        bool: True if user has access, False otherwise
    """
    # Admin users always have access
    if user.is_admin:
        return True
    
    # Check subscription status
    if user.subscription_status == "active":
        # Check if subscription is not expired
        if user.current_period_end and user.current_period_end > datetime.utcnow():
            return True
        else:
            # Subscription expired, update status
            user.subscription_status = "inactive"
            await db.commit()
            logger.info(f"Subscription expired for user {user.id}")
            return False
    
    # Check for grace period (24 hours for past_due)
    if user.subscription_status == "past_due":
        # Allow 24-hour grace period
        if user.subscription_updated_at:
            grace_period = datetime.utcnow() - user.subscription_updated_at
            if grace_period.total_seconds() < 24 * 3600:  # 24 hours
                return True
            else:
                # Grace period expired
                user.subscription_status = "inactive"
                await db.commit()
                logger.info(f"Grace period expired for user {user.id}")
                return False
    
    # No access for inactive/canceled subscriptions
    return False


def require_subscription(require_active: bool = True):
    """
    Decorator to require subscription access for endpoints.
    
    Args:
        require_active: Whether to require active subscription
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user and db from kwargs (assuming they're injected)
            user = kwargs.get('current_user')
            db = kwargs.get('db')
            
            if not user or not db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check subscription access
            has_access = await check_subscription_access(user, db, require_active)
            
            if not has_access:
                if user.subscription_status == "inactive":
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Active subscription required. Please subscribe to access this feature.",
                        headers={"X-Subscription-Required": "true"}
                    )
                elif user.subscription_status == "past_due":
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Payment required. Your subscription is past due.",
                        headers={"X-Subscription-Required": "true"}
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Valid subscription required.",
                        headers={"X-Subscription-Required": "true"}
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def get_user_subscription_info(user: User) -> dict:
    """
    Get user's subscription information for frontend display.
    
    Args:
        user: User object
    
    Returns:
        dict: Subscription information
    """
    is_active = user.subscription_status == "active"
    is_expired = False
    
    if user.current_period_end:
        is_expired = user.current_period_end < datetime.utcnow()
    
    return {
        "status": user.subscription_status,
        "is_active": is_active and not is_expired,
        "current_period_end": user.current_period_end,
        "plan_id": user.plan_id,
        "has_stripe_customer": bool(user.stripe_customer_id),
        "telegram_linked": bool(user.telegram_user_id),
        "subscription_created_at": user.subscription_created_at,
        "subscription_updated_at": user.subscription_updated_at
    }
