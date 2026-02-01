"""
New Subscription System API Router
Handles Free Trial, Professional ($14.99), and VIP Elite ($29.99) subscriptions via Binance Pay
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User, SubscriptionPlan, PaymentTransaction, SubscriptionEvent
from common.schemas import (
    SubscriptionPlanSchema, PaymentTransactionSchema, UserSubscriptionInfo,
    BinancePaySubscriptionRequest, SubscriptionAccessCheck, APIResponse
)
from common.logging import get_logger
from dependencies import get_db
from routers.auth import get_current_active_user
from services.subscription_binance_pay import SubscriptionBinancePayService
from middleware.new_subscription_access import subscription_controller

router = APIRouter()
logger = get_logger(__name__)

# Initialize service
binance_pay_service = SubscriptionBinancePayService()


@router.get("/plans", response_model=List[SubscriptionPlanSchema], tags=["Subscriptions"])
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """Get available subscription plans (public endpoint)."""
    try:
        plans = await binance_pay_service.get_subscription_plans(db)
        return plans
    except Exception as e:
        logger.error(f"Error getting subscription plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription plans")


@router.post("/trial/start", response_model=APIResponse, tags=["Subscriptions"])
async def start_free_trial(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Start free trial for user."""
    try:
        result = await binance_pay_service.start_free_trial(current_user.id, db)
        return APIResponse(
            success=result["success"],
            data=result.get("trial_info") if result["success"] else None,
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting free trial: {e}")
        raise HTTPException(status_code=500, detail="Failed to start free trial")


@router.post("/subscribe", response_model=APIResponse, tags=["Subscriptions"])
async def create_subscription(
    request: BinancePaySubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create subscription payment via Binance Pay."""
    try:
        result = await binance_pay_service.create_subscription_payment(
            current_user.id, request.plan_id, request, db
        )
        return APIResponse(
            success=result["success"],
            data={
                "payment_url": result.get("payment_url"),
                "payment_id": result.get("payment_id"),
                "amount_usdt": result.get("amount_usdt"),
                "plan": result.get("plan"),
                "test_mode": result.get("test_mode", False)
            },
            message=result["message"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get("/info", response_model=UserSubscriptionInfo, tags=["Subscriptions"])
async def get_subscription_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's subscription information."""
    try:
        info = await subscription_controller.get_user_subscription_info(current_user, db)
        return UserSubscriptionInfo(**info)
    except Exception as e:
        logger.error(f"Error getting subscription info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get subscription info")


@router.post("/check-access", response_model=SubscriptionAccessCheck, tags=["Subscriptions"])
async def check_access(
    access_type: str = "dashboard",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check user's access for specific type."""
    try:
        access_check = await subscription_controller.check_subscription_access(
            current_user, db, access_type
        )
        return access_check
    except Exception as e:
        logger.error(f"Error checking access: {e}")
        raise HTTPException(status_code=500, detail="Failed to check access")


@router.get("/payment/{payment_id}/status", response_model=APIResponse, tags=["Subscriptions"])
async def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check payment status."""
    try:
        # Verify payment belongs to user
        result = await db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.transaction_id == payment_id,
                PaymentTransaction.user_id == current_user.id
            )
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return APIResponse(
            success=True,
            data={
                "status": transaction.status,
                "amount_usdt": float(transaction.amount_usdt),
                "plan_id": transaction.plan_id,
                "created_at": transaction.created_at,
                "completed_at": transaction.completed_at
            },
            message="Payment status retrieved"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get payment status")


@router.get("/transactions", response_model=List[PaymentTransactionSchema], tags=["Subscriptions"])
async def get_user_transactions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's payment transactions."""
    try:
        result = await db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.user_id == current_user.id)
            .order_by(PaymentTransaction.created_at.desc())
        )
        transactions = result.scalars().all()
        return transactions
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get transactions")


@router.post("/binance-pay/webhook", tags=["Subscriptions"])
async def binance_pay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Binance Pay webhook notifications."""
    try:
        webhook_data = await request.json()
        logger.info(f"Received Binance Pay webhook: {webhook_data}")
        
        result = await binance_pay_service.handle_payment_webhook(webhook_data, db)
        
        if result["success"]:
            return {"status": "success", "message": "Webhook processed"}
        else:
            logger.error(f"Webhook processing failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@router.get("/dashboard-access", response_model=APIResponse, tags=["Subscriptions"])
async def request_dashboard_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Request dashboard access (increments trial access count)."""
    try:
        access_check = await subscription_controller.check_subscription_access(
            current_user, db, "dashboard", increment_access_count=True
        )
        
        if access_check.access:
            return APIResponse(
                success=True,
                data={
                    "access_granted": True,
                    "tier": access_check.tier,
                    "trial_days_remaining": access_check.trial_days_remaining,
                    "dashboard_access_remaining": access_check.dashboard_access_remaining
                },
                message="Dashboard access granted"
            )
        else:
            return APIResponse(
                success=False,
                data={
                    "access_granted": False,
                    "reason": access_check.reason,
                    "tier": access_check.tier,
                    "trial_days_remaining": access_check.trial_days_remaining,
                    "dashboard_access_remaining": access_check.dashboard_access_remaining
                },
                message=access_check.message
            )
            
    except Exception as e:
        logger.error(f"Error requesting dashboard access: {e}")
        raise HTTPException(status_code=500, detail="Failed to request dashboard access")


@router.get("/telegram-access", response_model=APIResponse, tags=["Subscriptions"])
async def check_telegram_access(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Check Telegram group access."""
    try:
        access_check = await subscription_controller.check_subscription_access(
            current_user, db, "telegram"
        )
        
        # Get Telegram access details
        result = await db.execute(
            select(TelegramGroupAccess).where(
                TelegramGroupAccess.user_id == current_user.id,
                TelegramGroupAccess.is_active == True
            )
        )
        telegram_access = result.scalars().all()
        
        return APIResponse(
            success=access_check.access,
            data={
                "telegram_access": access_check.access,
                "groups": [
                    {
                        "group_name": access.group_name,
                        "access_granted_at": access.access_granted_at.isoformat(),
                        "telegram_user_id": access.telegram_user_id,
                        "telegram_username": access.telegram_username
                    }
                    for access in telegram_access
                ]
            },
            message=access_check.message
        )
        
    except Exception as e:
        logger.error(f"Error checking Telegram access: {e}")
        raise HTTPException(status_code=500, detail="Failed to check Telegram access")


@router.get("/billing-info", response_model=APIResponse, tags=["Subscriptions"])
async def get_billing_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing information for user."""
    try:
        # Get subscription info
        sub_info = await subscription_controller.get_user_subscription_info(current_user, db)
        
        # Get recent transactions
        result = await db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.user_id == current_user.id)
            .order_by(PaymentTransaction.created_at.desc())
            .limit(5)
        )
        recent_transactions = result.scalars().all()
        
        billing_info = {
            "subscription_tier": sub_info["subscription_tier"],
            "subscription_status": sub_info["subscription_status"],
            "payment_due_date": sub_info["payment_due_date"],
            "last_payment_date": sub_info["last_payment_date"],
            "payment_method": sub_info["payment_method"],
            "access_revoked_at": sub_info["access_revoked_at"],
            "recent_transactions": [
                {
                    "id": tx.id,
                    "plan_id": tx.plan_id,
                    "amount_usdt": float(tx.amount_usdt),
                    "status": tx.status,
                    "created_at": tx.created_at.isoformat(),
                    "completed_at": tx.completed_at.isoformat() if tx.completed_at else None
                }
                for tx in recent_transactions
            ]
        }
        
        return APIResponse(
            success=True,
            data=billing_info,
            message="Billing information retrieved"
        )
        
    except Exception as e:
        logger.error(f"Error getting billing info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get billing information")
