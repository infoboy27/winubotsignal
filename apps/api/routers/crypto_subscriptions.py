"""
Crypto Subscription API endpoints for individual accounts
Supports Coinbase Commerce, Stripe Crypto, and direct crypto payments
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import User, SubscriptionEvent
from dependencies import get_db
from routers.auth import get_current_user
from services.crypto_payments import (
    CoinbaseCommerceService,
    StripeCryptoService,
    DirectCryptoPaymentService,
    create_subscription_payment,
    activate_subscription_after_payment,
    SUBSCRIPTION_PLANS
)
from services.nowpayments_service import NOWPaymentsService, POPULAR_CRYPTOCURRENCIES
from common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/crypto-subscriptions", tags=["Crypto Subscriptions"])


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans with crypto payment options."""
    return {
        "plans": SUBSCRIPTION_PLANS,
        "payment_methods": [
            {
                "id": "coinbase_commerce",
                "name": "Coinbase Commerce",
                "description": "Pay with crypto via Coinbase",
                "supported_currencies": ["USDC", "BTC", "ETH", "LTC", "BCH"],
                "instant_confirmation": True
            },
            {
                "id": "nowpayments",
                "name": "NOWPayments",
                "description": "Pay with 300+ cryptocurrencies",
                "supported_currencies": [currency["symbol"].upper() for currency in POPULAR_CRYPTOCURRENCIES],
                "instant_confirmation": True,
                "popular_currencies": POPULAR_CRYPTOCURRENCIES[:10]  # Top 10 for UI
            },
            {
                "id": "stripe_crypto", 
                "name": "Stripe Crypto",
                "description": "Pay with crypto via Stripe",
                "supported_currencies": ["USDC", "USDT"],
                "instant_confirmation": True
            },
            {
                "id": "direct_crypto",
                "name": "Direct Crypto Transfer",
                "description": "Send crypto directly to our wallet",
                "supported_currencies": ["USDT", "BTC", "ETH", "BNB"],
                "instant_confirmation": False
            }
        ]
    }


@router.post("/create-payment")
async def create_subscription_payment_endpoint(
    plan_id: str,
    payment_method: str = "coinbase_commerce",
    pay_currency: str = "btc",  # For NOWPayments
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a subscription payment using crypto."""
    
    try:
        result = await create_subscription_payment(
            user_id=current_user.id,
            plan_id=plan_id,
            payment_method=payment_method,
            pay_currency=pay_currency,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Subscription payment creation failed: {e}", exc_info=True)
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create payment: {str(e)}"
        )


@router.get("/payment-status/{payment_id}")
async def get_payment_status(
    payment_id: str,
    payment_method: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of a payment."""
    
    try:
        if payment_method == "coinbase_commerce":
            service = CoinbaseCommerceService()
            status = await service.get_charge_status(payment_id)
            
        elif payment_method == "stripe_crypto":
            service = StripeCryptoService()
            # Stripe status checking would be implemented here
            status = {"status": "pending", "paid": False}
            
        elif payment_method == "direct_crypto":
            # For direct crypto, status would be checked manually or via blockchain monitoring
            status = {"status": "pending", "paid": False}
            
        else:
            raise HTTPException(status_code=400, detail="Invalid payment method")
        
        return {
            "payment_id": payment_id,
            "payment_method": payment_method,
            "status": status["status"],
            "paid": status.get("paid", False)
        }
        
    except Exception as e:
        logger.error(f"Payment status query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to query payment status"
        )


@router.post("/activate-subscription")
async def activate_subscription(
    plan_id: str,
    payment_reference: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate subscription after payment verification."""
    
    try:
        result = await activate_subscription_after_payment(
            user_id=current_user.id,
            plan_id=plan_id,
            payment_reference=payment_reference,
            db=db
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Subscription activation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to activate subscription"
        )


@router.post("/webhooks/coinbase-commerce")
async def coinbase_commerce_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Coinbase Commerce webhook notifications."""
    
    try:
        # Get the raw body and signature
        body = await request.body()
        signature = request.headers.get("X-CC-Webhook-Signature", "")
        
        # Verify webhook signature
        service = CoinbaseCommerceService()
        if not service.verify_webhook(body.decode(), signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook data
        webhook_data = await request.json()
        event_type = webhook_data.get("type")
        
        if event_type == "charge:confirmed":
            # Payment was successful
            charge_data = webhook_data["data"]
            user_id = charge_data.get("metadata", {}).get("user_id")
            
            if user_id:
                # Determine plan from amount
                amount = float(charge_data["pricing"]["local"]["amount"])
                plan_id = None
                
                for pid, plan in SUBSCRIPTION_PLANS.items():
                    if plan["price_usd"] == amount:
                        plan_id = pid
                        break
                
                if plan_id:
                    await activate_subscription_after_payment(
                        user_id=int(user_id),
                        plan_id=plan_id,
                        payment_reference=charge_data["id"],
                        db=db
                    )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Coinbase Commerce webhook processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed"
        )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook notifications."""
    
    try:
        # Get the raw body and signature
        body = await request.body()
        signature = request.headers.get("Stripe-Signature", "")
        
        # Verify webhook signature (implement Stripe signature verification)
        # For now, we'll skip verification for development
        
        # Parse webhook data
        webhook_data = await request.json()
        event_type = webhook_data.get("type")
        
        if event_type == "payment_intent.succeeded":
            # Payment was successful
            payment_intent = webhook_data["data"]["object"]
            user_id = payment_intent.get("metadata", {}).get("user_id")
            
            if user_id:
                # Determine plan from amount
                amount = payment_intent["amount"] / 100  # Convert from cents
                plan_id = None
                
                for pid, plan in SUBSCRIPTION_PLANS.items():
                    if plan["price_usd"] == amount:
                        plan_id = pid
                        break
                
                if plan_id:
                    await activate_subscription_after_payment(
                        user_id=int(user_id),
                        plan_id=plan_id,
                        payment_reference=payment_intent["id"],
                        db=db
                    )
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Stripe webhook processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed"
        )


@router.get("/user-subscription")
async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current subscription status."""
    
    try:
        # Query user's subscription from database
        # This is a placeholder - implement based on your database structure
        
        subscription_event = await db.execute(
            """
            SELECT * FROM subscription_events 
            WHERE user_id = :user_id 
            AND event_type = 'activated'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"user_id": current_user.id}
        )
        
        subscription = subscription_event.fetchone()
        
        if subscription:
            return {
                "has_subscription": True,
                "plan": subscription.event_data.get("plan_name"),
                "activated_at": subscription.created_at,
                "features": subscription.event_data.get("features", []),
                "telegram_access": subscription.event_data.get("telegram_access", False),
                "discord_access": subscription.event_data.get("discord_access", False)
            }
        else:
            return {
                "has_subscription": False,
                "plan": None,
                "activated_at": None,
                "features": [],
                "telegram_access": False,
                "discord_access": False
            }
        
    except Exception as e:
        logger.error(f"User subscription query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user subscription"
        )


@router.get("/telegram-invite")
async def get_telegram_invite(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get Telegram group invite link based on user's subscription."""
    
    try:
        # Get user's subscription
        subscription_event = await db.execute(
            """
            SELECT * FROM subscription_events 
            WHERE user_id = :user_id 
            AND event_type = 'activated'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"user_id": current_user.id}
        )
        
        subscription = subscription_event.fetchone()
        
        if not subscription:
            raise HTTPException(status_code=403, detail="No active subscription")
        
        plan_data = subscription.event_data
        telegram_access = plan_data.get("telegram_access", False)
        
        if not telegram_access:
            raise HTTPException(status_code=403, detail="Your plan doesn't include Telegram access")
        
        # Return appropriate Telegram group based on plan
        plan_name = plan_data.get("plan_name", "")
        
        if "Premium" in plan_name:
            invite_link = "https://t.me/winu_premium_vip"  # VIP group
        elif "Pro" in plan_name:
            invite_link = "https://t.me/winu_pro_signals"  # Pro group
        else:
            invite_link = "https://t.me/winu_community"    # Basic group
        
        return {
            "invite_link": invite_link,
            "plan": plan_name,
            "access_granted": True
        }
        
    except Exception as e:
        logger.error(f"Telegram invite generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate Telegram invite"
        )


@router.post("/test-payment")
async def test_payment_integration():
    """Test endpoint to verify payment integration."""
    
    try:
        # Test Coinbase Commerce
        coinbase_service = CoinbaseCommerceService()
        coinbase_configured = bool(coinbase_service.api_key)
        
        # Test Stripe
        stripe_service = StripeCryptoService()
        stripe_configured = bool(stripe_service.api_key)
        
        # Test Direct Crypto
        direct_service = DirectCryptoPaymentService()
        direct_configured = bool(direct_service.wallet_addresses.get("USDT"))
        
        # Test NOWPayments
        nowpayments_service = NOWPaymentsService()
        nowpayments_configured = bool(nowpayments_service.api_key)
        
        return {
            "status": "success",
            "message": "Payment integration test completed",
            "coinbase_commerce": {
                "configured": coinbase_configured,
                "status": "ready" if coinbase_configured else "not_configured"
            },
            "nowpayments": {
                "configured": nowpayments_configured,
                "status": "ready" if nowpayments_configured else "not_configured"
            },
            "stripe_crypto": {
                "configured": stripe_configured,
                "status": "ready" if stripe_configured else "not_configured"
            },
            "direct_crypto": {
                "configured": direct_configured,
                "status": "ready" if direct_configured else "not_configured"
            }
        }
        
    except Exception as e:
        logger.error(f"Payment integration test failed: {e}")
        return {
            "status": "error",
            "message": f"Payment integration test failed: {str(e)}"
        }


# NOWPayments specific endpoints
@router.get("/nowpayments/currencies")
async def get_nowpayments_currencies():
    """Get available cryptocurrencies from NOWPayments."""
    try:
        service = NOWPaymentsService()
        currencies = await service.get_available_currencies()
        return {
            "status": "success",
            "currencies": currencies,
            "popular_currencies": POPULAR_CRYPTOCURRENCIES
        }
    except Exception as e:
        logger.error(f"Failed to get NOWPayments currencies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get currencies")


@router.get("/nowpayments/estimate")
async def get_nowpayments_estimate(
    amount: float,
    currency_from: str = "usd",
    currency_to: str = "btc"
):
    """Get estimated price from NOWPayments."""
    try:
        service = NOWPaymentsService()
        estimate = await service.get_estimated_price(amount, currency_from, currency_to)
        return {
            "status": "success",
            "estimate": estimate
        }
    except Exception as e:
        logger.error(f"Failed to get NOWPayments estimate: {e}")
        raise HTTPException(status_code=500, detail="Failed to get estimate")


@router.get("/nowpayments/payment/{payment_id}")
async def get_nowpayments_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get NOWPayments payment status."""
    try:
        service = NOWPaymentsService()
        payment_status = await service.get_payment_status(payment_id)
        return {
            "status": "success",
            "payment": payment_status
        }
    except Exception as e:
        logger.error(f"Failed to get NOWPayments payment status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get payment status")


@router.get("/nowpayments/invoice/{invoice_id}")
async def get_nowpayments_invoice_status(
    invoice_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get NOWPayments invoice status."""
    try:
        service = NOWPaymentsService()
        invoice_status = await service.get_invoice_status(invoice_id)
        return {
            "status": "success",
            "invoice": invoice_status
        }
    except Exception as e:
        logger.error(f"Failed to get NOWPayments invoice status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get invoice status")


@router.post("/webhooks/nowpayments")
async def nowpayments_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle NOWPayments webhook notifications."""
    webhook_log_id = None
    try:
        # Get the raw body
        body = await request.body()
        payload = body.decode('utf-8')
        
        # Get signature from headers
        signature = request.headers.get('x-nowpayments-sig')
        headers_dict = dict(request.headers)
        
        # Parse webhook data
        webhook_data = json.loads(payload)
        
        # Import webhook logger
        from services.webhook_logger import log_webhook, update_webhook_status
        
        # Extract preliminary data
        payment_id = webhook_data.get("payment_id") or webhook_data.get("invoice_id")
        payment_status = webhook_data.get("payment_status") or webhook_data.get("invoice_status")
        order_id = webhook_data.get("order_id")
        
        user_id = None
        plan_id = None
        if order_id:
            order_parts = order_id.split("_")
            if len(order_parts) >= 4 and order_parts[0] == "WINU" and order_parts[1] == "SUB":
                user_id = int(order_parts[2])
                plan_id = order_parts[3]
        
        # Verify signature
        service = NOWPaymentsService()
        signature_valid = service.verify_webhook_signature(payload, signature)
        
        # Log the webhook
        webhook_log_id = await log_webhook(
            db=db,
            payment_method="nowpayments",
            webhook_type=payment_status,
            webhook_data=webhook_data,
            headers=headers_dict,
            signature=signature,
            signature_valid=signature_valid,
            user_id=user_id,
            payment_id=str(payment_id) if payment_id else None,
            plan_id=plan_id
        )
        
        if not signature_valid:
            logger.warning("Invalid NOWPayments webhook signature")
            await update_webhook_status(db, webhook_log_id, "failed", "Invalid signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        logger.info(f"NOWPayments webhook received: {webhook_data}")
        
        # Update webhook status to processing
        await update_webhook_status(db, webhook_log_id, "processing")
        
        # Invoice is paid when status is "finished", "paid", or "confirmed"
        if payment_status in ["finished", "paid", "confirmed"] and order_id:
            if user_id and plan_id:
                logger.info(f"🎯 Payment {payment_status} for user {user_id}, plan {plan_id}, reference {payment_id}")
                
                # Activate subscription
                await activate_subscription_after_payment(
                    user_id=user_id,
                    plan_id=plan_id,
                    payment_reference=str(payment_id),
                    db=db
                )
                
                logger.info(f"✅ Subscription activated for user {user_id}, plan {plan_id}")
                
                # Send Discord notification for successful payment
                import aiohttp
                try:
                    discord_webhook_url = "https://discord.com/api/webhooks/1425572155751399616/i5VBCt_sm4eYpcUJ8aG3AoFJuDfEAAlV1asqqbURnqGjTP4H2KkzXwrsAk2DbSXVOH-y"
                    embed = {
                        "title": "✅ Payment Successful",
                        "description": f"Subscription activated successfully",
                        "color": 0x00FF00,
                        "fields": [
                            {"name": "User ID", "value": str(user_id), "inline": True},
                            {"name": "Plan", "value": plan_id, "inline": True},
                            {"name": "Payment ID", "value": str(payment_id), "inline": False},
                            {"name": "Method", "value": "NOWPayments", "inline": True},
                        ],
                        "timestamp": datetime.utcnow().isoformat(),
                        "footer": {"text": "Winu Bot Payment Monitor"}
                    }
                    async with aiohttp.ClientSession() as session:
                        await session.post(discord_webhook_url, json={"embeds": [embed]})
                except Exception as discord_error:
                    logger.warning(f"Failed to send Discord notification: {discord_error}")
                
                # Update webhook status to completed
                await update_webhook_status(db, webhook_log_id, "completed")
            else:
                logger.warning(f"Invalid order_id format: {order_id}")
                await update_webhook_status(db, webhook_log_id, "failed", "Invalid order_id format")
        else:
            logger.info(f"⏳ Payment in progress - Status: {payment_status}, Order: {order_id}")
            await update_webhook_status(db, webhook_log_id, "completed")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"NOWPayments webhook processing failed: {e}")
        if webhook_log_id:
            try:
                await update_webhook_status(db, webhook_log_id, "failed", str(e))
            except:
                pass
        
        # Send Discord notification for failed payment
        try:
            import aiohttp
            discord_webhook_url = "https://discord.com/api/webhooks/1425572155751399616/i5VBCt_sm4eYpcUJ8aG3AoFJuDfEAAlV1asqqbURnqGjTP4H2KkzXwrsAk2DbSXVOH-y"
            embed = {
                "title": "❌ Webhook Processing Failed",
                "description": f"Error processing NOWPayments webhook",
                "color": 0xFF0000,
                "fields": [
                    {"name": "Error", "value": str(e)[:1000], "inline": False},
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "Winu Bot Payment Monitor"}
            }
            async with aiohttp.ClientSession() as session:
                await session.post(discord_webhook_url, json={"embeds": [embed]})
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed"
        )



