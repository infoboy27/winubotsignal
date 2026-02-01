"""
Crypto Payment Integration for Individual Accounts
Supports Coinbase Commerce, Stripe Crypto, and direct crypto payments
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import User, SubscriptionEvent
from common.logging import get_logger
from .nowpayments_service import NOWPaymentsService

logger = get_logger(__name__)


class CoinbaseCommerceService:
    """Coinbase Commerce integration for crypto payments."""
    
    def __init__(self):
        self.api_key = os.getenv("COINBASE_COMMERCE_API_KEY", "")
        self.webhook_secret = os.getenv("COINBASE_COMMERCE_WEBHOOK_SECRET", "")
        self.base_url = "https://api.commerce.coinbase.com"
        
        if not self.api_key:
            logger.warning("Coinbase Commerce API key not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Coinbase Commerce API."""
        return {
            "Content-Type": "application/json",
            "X-CC-Api-Key": self.api_key,
            "X-CC-Version": "2018-03-22"
        }
    
    async def create_charge(
        self,
        amount: float,
        currency: str = "USDC",
        name: str = "Winu Trading Bot Subscription",
        description: str = "Monthly subscription for trading signals",
        user_id: int = None
    ) -> Dict[str, Any]:
        """Create a charge for subscription payment."""
        
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Coinbase Commerce not configured")
        
        charge_data = {
            "name": name,
            "description": description,
            "pricing_type": "fixed_price",
            "local_price": {
                "amount": str(amount),
                "currency": "USD"
            },
            "pricing": {
                "USD": str(amount)
            },
            "metadata": {
                "user_id": str(user_id) if user_id else "",
                "subscription": "true",
                "timestamp": str(int(time.time()))
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/charges",
                    json=charge_data,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    return {
                        "charge_id": data["data"]["id"],
                        "payment_url": data["data"]["hosted_url"],
                        "amount": amount,
                        "currency": currency,
                        "status": "pending"
                    }
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Coinbase Commerce error: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Coinbase Commerce API timeout")
        except Exception as e:
            logger.error(f"Coinbase Commerce charge creation error: {e}")
            raise HTTPException(status_code=500, detail="Failed to create charge")
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """Get the status of a charge."""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/charges/{charge_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "charge_id": charge_id,
                        "status": data["data"]["timeline"][-1]["status"],
                        "paid": data["data"]["timeline"][-1]["status"] == "COMPLETED",
                        "amount": data["data"]["pricing"]["local"]["amount"],
                        "currency": data["data"]["pricing"]["local"]["currency"]
                    }
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to get charge status"
                    )
                    
        except Exception as e:
            logger.error(f"Coinbase Commerce status query error: {e}")
            raise HTTPException(status_code=500, detail="Failed to query charge status")
    
    def verify_webhook(self, payload: str, signature: str) -> bool:
        """Verify Coinbase Commerce webhook signature."""
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)


class StripeCryptoService:
    """Stripe Crypto integration for crypto payments."""
    
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.base_url = "https://api.stripe.com/v1"
        
        if not self.api_key:
            logger.warning("Stripe API key not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Stripe API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    async def create_crypto_payment_intent(
        self,
        amount: int,  # Amount in cents
        currency: str = "usd",
        user_id: int = None
    ) -> Dict[str, Any]:
        """Create a Stripe payment intent for crypto payment."""
        
        if not self.api_key:
            raise HTTPException(status_code=500, detail="Stripe not configured")
        
        payment_intent_data = {
            "amount": amount,
            "currency": currency,
            "payment_method_types[]": "link",
            "metadata[user_id]": str(user_id) if user_id else "",
            "metadata[subscription]": "true"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payment_intents",
                    data=payment_intent_data,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "payment_intent_id": data["id"],
                        "client_secret": data["client_secret"],
                        "amount": amount,
                        "currency": currency,
                        "status": data["status"]
                    }
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Stripe error: {response.text}"
                    )
                    
        except Exception as e:
            logger.error(f"Stripe payment intent creation error: {e}")
            raise HTTPException(status_code=500, detail="Failed to create payment intent")


class DirectCryptoPaymentService:
    """Direct crypto payment service using wallet addresses."""
    
    def __init__(self):
        self.wallet_addresses = {
            "USDT": os.getenv("USDT_WALLET_ADDRESS", ""),
            "BTC": os.getenv("BTC_WALLET_ADDRESS", ""),
            "ETH": os.getenv("ETH_WALLET_ADDRESS", ""),
            "BNB": os.getenv("BNB_WALLET_ADDRESS", "")
        }
    
    def generate_payment_info(
        self,
        amount: float,
        currency: str = "USDT",
        user_id: int = None
    ) -> Dict[str, Any]:
        """Generate payment information for direct crypto transfer."""
        
        wallet_address = self.wallet_addresses.get(currency.upper())
        if not wallet_address:
            raise HTTPException(status_code=400, detail=f"Wallet address not configured for {currency}")
        
        # Generate unique payment reference
        payment_ref = f"WINU_{user_id}_{int(time.time())}"
        
        return {
            "wallet_address": wallet_address,
            "amount": amount,
            "currency": currency.upper(),
            "payment_reference": payment_ref,
            "instructions": [
                f"Send exactly {amount} {currency.upper()} to the address above",
                f"Use payment reference: {payment_ref}",
                "Payment will be verified within 15 minutes",
                "Contact support if payment is not processed"
            ]
        }


# Updated subscription plans with new pricing
SUBSCRIPTION_PLANS = {
    "professional": {
        "name": "Professional",
        "price_usd": 14.99,
        "price_usdt": 14.99,
        "features": [
            "Dashboard access",
            "Telegram group access",
            "Priority support",
            "Real-time signals",
            "Email alerts"
        ],
        "max_positions": 5,
        "min_signal_score": 0.65,
        "telegram_access": True,
        "discord_access": True
    },
    "vip_elite": {
        "name": "VIP Elite",
        "price_usd": 29.99,
        "price_usdt": 29.99,
        "features": [
            "All Professional features",
            "24/7 priority support",
            "Early access to new features",
            "Access to trading bot",
            "Custom alerts",
            "Access to airdrops",
            "Advanced analytics"
        ],
        "max_positions": 10,
        "min_signal_score": 0.60,
        "telegram_access": True,
        "discord_access": True
    }
}


async def create_subscription_payment(
    user_id: int,
    plan_id: str,
    payment_method: str = "coinbase_commerce",  # coinbase_commerce, stripe_crypto, direct_crypto, nowpayments
    pay_currency: str = "btc",  # For NOWPayments
    db: AsyncSession = None
) -> Dict[str, Any]:
    """Create a subscription payment using the specified payment method."""
    
    if plan_id not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    
    try:
        if payment_method == "coinbase_commerce":
            service = CoinbaseCommerceService()
            result = await service.create_charge(
                amount=plan["price_usd"],
                currency="USDC",
                name=f"{plan['name']} - Winu Trading Bot",
                description=f"Monthly subscription for {plan['name']}",
                user_id=user_id
            )
            
        elif payment_method == "stripe_crypto":
            service = StripeCryptoService()
            result = await service.create_crypto_payment_intent(
                amount=int(plan["price_usd"] * 100),  # Convert to cents
                currency="usd",
                user_id=user_id
            )
            
        elif payment_method == "direct_crypto":
            service = DirectCryptoPaymentService()
            result = service.generate_payment_info(
                amount=plan["price_usdt"],
                currency="USDT",
                user_id=user_id
            )
            
        elif payment_method == "nowpayments":
            # Get user email if db session is available
            customer_email = None
            if db:
                from sqlalchemy import select
                from common.database import User
                result_user = await db.execute(select(User).where(User.id == user_id))
                user = result_user.scalar_one_or_none()
                if user:
                    customer_email = user.email
            
            service = NOWPaymentsService()
            result = await service.create_subscription_payment(
                user_id=user_id,
                plan_id=plan_id,
                amount_usd=plan["price_usd"],
                pay_currency=pay_currency,
                customer_email=customer_email,
                use_invoice=True  # Use hosted payment page
            )
            
        else:
            raise HTTPException(status_code=400, detail="Invalid payment method")
        
        return {
            "success": True,
            "plan": plan,
            "payment_method": payment_method,
            "payment_data": result,
            "message": f"Payment created for {plan['name']}"
        }
        
    except Exception as e:
        logger.error(f"Subscription payment creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment: {str(e)}")


async def activate_subscription_after_payment(
    user_id: int,
    plan_id: str,
    payment_reference: str,
    db: AsyncSession
):
    """Activate user subscription after successful payment."""
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    
    try:
        # Get user from database
        from sqlalchemy import select
        from common.database import User
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {user_id} not found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user subscription status
        user.subscription_status = "active"
        user.subscription_tier = plan_id
        user.plan_id = plan_id
        user.last_payment_date = datetime.utcnow()
        user.payment_due_date = datetime.utcnow() + timedelta(days=30)
        user.subscription_renewal_date = datetime.utcnow() + timedelta(days=30)
        user.current_period_end = datetime.utcnow() + timedelta(days=30)
        user.access_revoked_at = None
        user.subscription_updated_at = datetime.utcnow()
        
        # Create subscription event for tracking
        subscription_event = SubscriptionEvent(
            user_id=user_id,
            event_type="activated",
            event_data={
                "plan_id": plan_id,
                "plan_name": plan["name"],
                "payment_reference": payment_reference,
                "activated_at": datetime.utcnow().isoformat(),
                "features": plan["features"],
                "telegram_access": plan["telegram_access"],
                "discord_access": plan["discord_access"]
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(subscription_event)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"✅ SUBSCRIPTION ACTIVATED - User: {user_id}, Plan: {plan['name']}, Status: {user.subscription_status}, Tier: {user.subscription_tier}, Reference: {payment_reference}")
        
        return {
            "success": True,
            "message": "Subscription activated successfully",
            "plan": plan
        }
        
    except Exception as e:
        logger.error(f"❌ CRITICAL SUBSCRIPTION ACTIVATION FAILURE - User: {user_id}, Plan: {plan_id}, Reference: {payment_reference}, Error: {str(e)}", exc_info=True)
        await db.rollback()
        
        # Create failure event for tracking
        try:
            failure_event = SubscriptionEvent(
                user_id=user_id,
                event_type="activation_failed",
                event_data={
                    "plan_id": plan_id,
                    "payment_reference": payment_reference,
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(failure_event)
            await db.commit()
        except:
            pass  # Don't fail on failure event creation
        
        raise HTTPException(status_code=500, detail="Failed to activate subscription")



