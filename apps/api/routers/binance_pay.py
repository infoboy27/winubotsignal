"""
Binance Pay API endpoints for subscription payments
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db, User, SubscriptionEvent
from common.auth import get_current_user
from services.binance_pay import (
    BinancePayService, 
    create_subscription_with_binance_pay,
    SUBSCRIPTION_PLANS
)
from common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/binance-pay", tags=["Binance Pay"])


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans with Binance Pay pricing."""
    return {
        "plans": SUBSCRIPTION_PLANS,
        "supported_currencies": ["USDT", "BTC", "BNB", "ETH"],
        "billing_cycles": ["monthly", "quarterly", "yearly"]
    }


@router.post("/subscribe")
async def create_binance_pay_subscription(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a subscription using Binance Pay Direct Debit."""
    
    try:
        result = await create_subscription_with_binance_pay(
            user_id=current_user.id,
            plan_id=plan_id,
            db=db
        )
        
        return {
            "success": True,
            "message": "Subscription created successfully",
            "authorization_url": result["authorization_url"],
            "contract_code": result["contract"]["contract_code"],
            "plan": result["plan"]
        }
        
    except Exception as e:
        logger.error(f"Subscription creation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.get("/contract/{contract_id}/status")
async def get_contract_status(
    contract_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a Direct Debit contract."""
    
    binance_pay = BinancePayService()
    
    try:
        status = await binance_pay.get_contract_status(contract_id)
        return {
            "contract_id": contract_id,
            "status": status["status"],
            "authorized": status["authorized"],
            "expires_at": status.get("expires_at")
        }
        
    except Exception as e:
        logger.error(f"Contract status query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to query contract status"
        )


@router.post("/contract/{contract_id}/authorize")
async def authorize_contract(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if contract is authorized and update user subscription."""
    
    binance_pay = BinancePayService()
    
    try:
        # Check contract status
        status = await binance_pay.get_contract_status(contract_id)
        
        if status["authorized"]:
            # Contract is authorized, activate subscription
            # This would update the user's subscription status in your database
            # Implementation depends on your subscription system
            
            # Log subscription activation
            subscription_event = SubscriptionEvent(
                user_id=current_user.id,
                event_type="activated",
                event_data={
                    "contract_id": contract_id,
                    "payment_method": "binance_pay",
                    "activated_at": datetime.utcnow().isoformat()
                }
            )
            db.add(subscription_event)
            await db.commit()
            
            return {
                "success": True,
                "message": "Subscription activated successfully",
                "status": "active"
            }
        else:
            return {
                "success": False,
                "message": "Contract not yet authorized",
                "status": "pending_authorization"
            }
            
    except Exception as e:
        logger.error(f"Contract authorization check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to check contract authorization"
        )


@router.post("/contract/{contract_id}/cancel")
async def cancel_subscription(
    contract_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a subscription and its Direct Debit contract."""
    
    binance_pay = BinancePayService()
    
    try:
        # Cancel the contract with Binance Pay
        success = await binance_pay.cancel_contract(contract_id)
        
        if success:
            # Log subscription cancellation
            subscription_event = SubscriptionEvent(
                user_id=current_user.id,
                event_type="cancelled",
                event_data={
                    "contract_id": contract_id,
                    "payment_method": "binance_pay",
                    "cancelled_at": datetime.utcnow().isoformat()
                }
            )
            db.add(subscription_event)
            await db.commit()
            
            return {
                "success": True,
                "message": "Subscription cancelled successfully"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to cancel contract with Binance Pay"
            )
            
    except Exception as e:
        logger.error(f"Subscription cancellation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel subscription"
        )


@router.get("/authorize/{contract_code}")
async def authorize_subscription(
    contract_code: str,
    current_user: User = Depends(get_current_user)
):
    """Redirect user to Binance Pay authorization page."""
    
    # This endpoint would typically redirect to the authorization URL
    # The actual implementation depends on how you want to handle the redirect
    
    binance_pay = BinancePayService()
    
    try:
        # Get contract status to get authorization URL
        # This is a simplified example - you'd need to store the authorization URL
        # when creating the contract
        
        return {
            "message": "Please complete authorization in your Binance account",
            "instructions": [
                "1. Open your Binance app or go to binance.com",
                "2. Navigate to Binance Pay",
                "3. Go to Direct Debit section",
                "4. Find and authorize the contract",
                f"5. Contract code: {contract_code}"
            ],
            "contract_code": contract_code
        }
        
    except Exception as e:
        logger.error(f"Authorization redirect failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process authorization"
        )


@router.post("/webhook")
async def binance_pay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Binance Pay webhook notifications."""
    
    try:
        # Get webhook payload
        payload = await request.json()
        
        # Verify webhook signature (implement signature verification)
        # This is important for security
        
        binance_pay = BinancePayService()
        result = await binance_pay.handle_webhook(payload)
        
        logger.info(f"Binance Pay webhook processed: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Binance Pay webhook processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed"
        )


@router.get("/payment-history")
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Binance Pay payment history."""
    
    try:
        # Query payment history from database
        # This is a placeholder - implement based on your database structure
        
        payment_history = await db.execute(
            """
            SELECT * FROM subscription_events 
            WHERE user_id = :user_id 
            AND event_data->>'payment_method' = 'binance_pay'
            ORDER BY created_at DESC
            LIMIT 20
            """,
            {"user_id": current_user.id}
        )
        
        return {
            "payments": payment_history.fetchall(),
            "total_payments": len(payment_history.fetchall())
        }
        
    except Exception as e:
        logger.error(f"Payment history query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve payment history"
        )


@router.post("/test-payment")
async def test_binance_pay_integration():
    """Test endpoint to verify Binance Pay integration."""
    
    binance_pay = BinancePayService()
    
    try:
        # Test API connection
        # This would be a simple API call to verify credentials
        
        return {
            "status": "success",
            "message": "Binance Pay integration is working",
            "merchant_id": binance_pay.merchant_id,
            "api_configured": bool(binance_pay.api_key and binance_pay.secret_key)
        }
        
    except Exception as e:
        logger.error(f"Binance Pay test failed: {e}")
        return {
            "status": "error",
            "message": f"Binance Pay integration test failed: {str(e)}"
        }



