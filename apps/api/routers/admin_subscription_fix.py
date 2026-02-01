"""Admin endpoints for subscription management and fixes."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

import sys
sys.path.append('/packages')

from common.database import User, SubscriptionEvent
from common.logging import get_logger
from dependencies import get_db

router = APIRouter(prefix="/admin/subscriptions", tags=["Admin Subscriptions"])
logger = get_logger(__name__)


class ManualSubscriptionActivation(BaseModel):
    user_id: int
    subscription_tier: str  # professional or vip_elite
    duration_days: int = 30
    reason: str


class SubscriptionStatusUpdate(BaseModel):
    user_id: int
    subscription_status: str  # active, inactive, past_due, canceled
    reason: str


class UserSearch(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[int] = None


@router.post("/activate-manual", tags=["Admin"])
async def manually_activate_subscription(
    request: ManualSubscriptionActivation,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually activate subscription for a user.
    Use this when payment webhooks fail or for support escalations.
    """
    try:
        # Get user
        result = await db.execute(select(User).where(User.id == request.user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
        
        # Validate tier
        if request.subscription_tier not in ["professional", "vip_elite"]:
            raise HTTPException(
                status_code=400, 
                detail="Invalid tier. Must be 'professional' or 'vip_elite'"
            )
        
        # Store old values for logging
        old_status = user.subscription_status
        old_tier = user.subscription_tier
        
        # Update user subscription
        user.subscription_status = "active"
        user.subscription_tier = request.subscription_tier
        user.last_payment_date = datetime.utcnow()
        user.payment_due_date = datetime.utcnow() + timedelta(days=request.duration_days)
        user.subscription_renewal_date = datetime.utcnow() + timedelta(days=request.duration_days)
        user.current_period_end = datetime.utcnow() + timedelta(days=request.duration_days)
        user.access_revoked_at = None
        user.subscription_updated_at = datetime.utcnow()
        
        # Create subscription event for audit trail
        subscription_event = SubscriptionEvent(
            user_id=request.user_id,
            event_type="manual_activation",
            event_data={
                "reason": request.reason,
                "tier": request.subscription_tier,
                "duration_days": request.duration_days,
                "activated_by": "admin_manual",
                "activated_at": datetime.utcnow().isoformat(),
                "old_status": old_status,
                "old_tier": old_tier,
                "new_status": "active",
                "new_tier": request.subscription_tier
            },
            processed=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(subscription_event)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Subscription manually activated for user {user.id}: {request.subscription_tier} for {request.duration_days} days. Reason: {request.reason}")
        
        return {
            "success": True,
            "message": f"Subscription activated for user {user.username}",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "subscription_tier": user.subscription_tier,
            "subscription_status": user.subscription_status,
            "payment_due_date": user.payment_due_date.isoformat() if user.payment_due_date else None,
            "event_id": subscription_event.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error manually activating subscription: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to activate subscription: {str(e)}")


@router.post("/update-status", tags=["Admin"])
async def update_subscription_status(
    request: SubscriptionStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update subscription status for a user.
    """
    try:
        # Get user
        result = await db.execute(select(User).where(User.id == request.user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
        
        # Validate status
        valid_statuses = ["active", "inactive", "past_due", "canceled"]
        if request.subscription_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        old_status = user.subscription_status
        user.subscription_status = request.subscription_status
        user.subscription_updated_at = datetime.utcnow()
        
        # Create event
        subscription_event = SubscriptionEvent(
            user_id=request.user_id,
            event_type="status_update",
            event_data={
                "reason": request.reason,
                "old_status": old_status,
                "new_status": request.subscription_status,
                "updated_by": "admin_manual",
                "updated_at": datetime.utcnow().isoformat()
            },
            processed=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(subscription_event)
        
        await db.commit()
        
        logger.info(f"Subscription status updated for user {user.id}: {old_status} -> {request.subscription_status}. Reason: {request.reason}")
        
        return {
            "success": True,
            "message": f"Status updated for user {user.username}",
            "user_id": user.id,
            "username": user.username,
            "old_status": old_status,
            "new_status": user.subscription_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription status: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.get("/problematic-users", tags=["Admin"])
async def get_problematic_users(db: AsyncSession = Depends(get_db)):
    """
    Find users who might have payment issues:
    - Verified email but inactive subscription with free tier
    - Active subscription but expired period_end
    - Past_due for more than 24 hours
    """
    try:
        # Case 1: Verified users stuck on free/inactive (potential webhook failures)
        result = await db.execute(
            select(User).where(
                User.email_verified == True,
                User.subscription_status == "inactive",
                User.subscription_tier == "free"
            ).limit(20)
        )
        stuck_users = result.scalars().all()
        
        # Case 2: Active subscriptions that are expired
        result = await db.execute(
            select(User).where(
                User.subscription_status == "active",
                User.current_period_end < datetime.utcnow()
            ).limit(20)
        )
        expired_active_users = result.scalars().all()
        
        # Case 3: Past due for too long
        grace_period_expired = datetime.utcnow() - timedelta(hours=24)
        result = await db.execute(
            select(User).where(
                User.subscription_status == "past_due",
                User.subscription_updated_at < grace_period_expired
            ).limit(20)
        )
        overdue_users = result.scalars().all()
        
        return {
            "stuck_on_free": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "subscription_tier": u.subscription_tier,
                    "subscription_status": u.subscription_status
                } for u in stuck_users
            ],
            "expired_but_active": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "subscription_tier": u.subscription_tier,
                    "subscription_status": u.subscription_status,
                    "current_period_end": u.current_period_end.isoformat() if u.current_period_end else None
                } for u in expired_active_users
            ],
            "overdue_past_grace": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "subscription_tier": u.subscription_tier,
                    "subscription_status": u.subscription_status,
                    "subscription_updated_at": u.subscription_updated_at.isoformat() if u.subscription_updated_at else None
                } for u in overdue_users
            ],
            "total_issues": len(stuck_users) + len(expired_active_users) + len(overdue_users)
        }
        
    except Exception as e:
        logger.error(f"Error finding problematic users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", tags=["Admin"])
async def get_user_subscription_details(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed subscription information for a user."""
    try:
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Get recent subscription events
        result = await db.execute(
            select(SubscriptionEvent)
            .where(SubscriptionEvent.user_id == user_id)
            .order_by(SubscriptionEvent.created_at.desc())
            .limit(10)
        )
        events = result.scalars().all()
        
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "email_verified": user.email_verified,
                "subscription_status": user.subscription_status,
                "subscription_tier": user.subscription_tier,
                "last_payment_date": user.last_payment_date.isoformat() if user.last_payment_date else None,
                "payment_due_date": user.payment_due_date.isoformat() if user.payment_due_date else None,
                "current_period_end": user.current_period_end.isoformat() if user.current_period_end else None,
                "access_revoked_at": user.access_revoked_at.isoformat() if user.access_revoked_at else None,
                "subscription_updated_at": user.subscription_updated_at.isoformat() if user.subscription_updated_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "recent_events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "event_data": e.event_data,
                    "processed": e.processed,
                    "created_at": e.created_at.isoformat() if e.created_at else None
                } for e in events
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user subscription details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

