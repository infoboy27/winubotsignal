"""
Enhanced Binance Pay Integration for New Subscription System
Supports Free Trial, Professional ($14.99), and VIP Elite ($29.99) tiers
"""

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import User, SubscriptionPlan, PaymentTransaction, SubscriptionEvent, TelegramGroupAccess
from common.logging import get_logger
from common.schemas import BinancePaySubscriptionRequest

logger = get_logger(__name__)


class SubscriptionBinancePayService:
    """Enhanced Binance Pay service for subscription payments."""
    
    def __init__(self):
        # Configuration
        self.merchant_id = "287402909"  # Fixed merchant ID as specified
        self.api_base = "https://bpay.binanceapi.com"
        self.api_key = os.getenv("BINANCE_PAY_API_KEY", "")
        self.secret_key = os.getenv("BINANCE_PAY_SECRET_KEY", "")
        self.webhook_secret = os.getenv("BINANCE_PAY_WEBHOOK_SECRET", "")
        
        # Subscription plans configuration
        self.subscription_plans = {
            "free_trial": {
                "name": "Free Trial",
                "price_usd": 0.00,
                "price_usdt": 0.00,
                "duration_days": 7,
                "dashboard_access_limit": 1,
                "features": [
                    "1-time dashboard access",
                    "Basic signal preview",
                    "Limited features"
                ],
                "telegram_access": False,
                "support_level": "none"
            },
            "professional": {
                "name": "Professional",
                "price_usd": 14.99,
                "price_usdt": 14.99,
                "interval": "monthly",
                "features": [
                    "Dashboard access",
                    "Telegram group access",
                    "Priority support",
                    "Real-time signals",
                    "Email alerts"
                ],
                "telegram_access": True,
                "support_level": "priority",
                "binance_pay_id": "287402909"
            },
            "vip_elite": {
                "name": "VIP Elite",
                "price_usd": 29.99,
                "price_usdt": 29.99,
                "interval": "monthly",
                "features": [
                    "All Professional features",
                    "24/7 priority support",
                    "Early access to new features",
                    "Access to trading bot",
                    "Custom alerts",
                    "Access to airdrops",
                    "Advanced analytics"
                ],
                "telegram_access": True,
                "support_level": "24/7",
                "binance_pay_id": "287402909"
            }
        }
        
        if not all([self.api_key, self.secret_key]):
            logger.warning("Binance Pay credentials not configured - using test mode")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC signature for Binance Pay API."""
        query_string = urlencode(sorted(params.items()))
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Get headers with signature for API requests."""
        signature = self._generate_signature(params)
        return {
            "Content-Type": "application/json",
            "BinancePay-Timestamp": str(int(time.time() * 1000)),
            "BinancePay-Nonce": str(uuid.uuid4()),
            "BinancePay-Certificate-SN": self.api_key,
            "BinancePay-Signature": signature
        }
    
    async def start_free_trial(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Start free trial for a user."""
        try:
            # Get user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check if user already used trial
            if user.trial_used:
                return {
                    "success": False,
                    "error": "Free trial already used",
                    "message": "You have already used your free trial. Please subscribe to Professional or VIP Elite to continue."
                }
            
            # Start trial
            user.trial_start_date = datetime.utcnow()
            user.trial_used = True
            user.subscription_tier = "free"
            user.subscription_status = "trial"
            
            # Create subscription event
            event = SubscriptionEvent(
                user_id=user_id,
                event_type="trial_started",
                event_data={
                    "trial_start_date": user.trial_start_date.isoformat(),
                    "trial_duration_days": 7,
                    "dashboard_access_limit": 1
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            logger.info(f"Free trial started for user {user_id}")
            
            return {
                "success": True,
                "message": "Free trial started successfully!",
                "trial_info": {
                    "start_date": user.trial_start_date.isoformat(),
                    "duration_days": 7,
                    "dashboard_access_limit": 1,
                    "days_remaining": 7
                }
            }
            
        except Exception as e:
            logger.error(f"Error starting free trial: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to start trial: {str(e)}")
    
    async def create_subscription_payment(
        self, 
        user_id: int, 
        plan_id: str, 
        request: BinancePaySubscriptionRequest,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Create subscription payment via Binance Pay."""
        
        try:
            # Validate plan
            if plan_id not in self.subscription_plans:
                raise HTTPException(status_code=400, detail="Invalid subscription plan")
            
            plan = self.subscription_plans[plan_id]
            
            # Get user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Generate unique payment ID
            payment_id = f"winu_sub_{user_id}_{plan_id}_{int(time.time())}"
            
            # Create payment transaction record
            transaction = PaymentTransaction(
                user_id=user_id,
                plan_id=plan_id,
                amount_usd=plan["price_usd"],
                amount_usdt=plan["price_usdt"],
                payment_method="binance_pay",
                transaction_id=payment_id,
                status="pending",
                payment_data={
                    "merchant_id": self.merchant_id,
                    "plan_name": plan["name"],
                    "telegram_user_id": request.telegram_user_id,
                    "telegram_username": request.telegram_username
                }
            )
            db.add(transaction)
            
            # Create subscription event
            event = SubscriptionEvent(
                user_id=user_id,
                event_type="payment_initiated",
                event_data={
                    "plan_id": plan_id,
                    "amount_usdt": plan["price_usdt"],
                    "payment_id": payment_id,
                    "merchant_id": self.merchant_id
                },
                processed=True
            )
            db.add(event)
            
            await db.commit()
            
            # If no API keys configured, return test mode response
            if not self.api_key or not self.secret_key:
                return {
                    "success": True,
                    "payment_url": f"https://test.binance.com/en/pay/test-payment?merchantId={self.merchant_id}&amount={plan['price_usdt']}",
                    "payment_id": payment_id,
                    "amount_usdt": plan["price_usdt"],
                    "plan": plan,
                    "test_mode": True,
                    "message": "Test mode - payment URL generated"
                }
            
            # Prepare Binance Pay API payload
            payload = {
                "merchantId": self.merchant_id,
                "prepayId": payment_id,
                "totalFee": {
                    "currency": "USDT",
                    "amount": str(plan["price_usdt"])
                },
                "productType": "Subscription",
                "productName": f"Winu {plan['name']} - Monthly Subscription",
                "productDetail": f"Monthly subscription for {plan['name']} plan",
                "returnUrl": f"https://winu.app/payment/success?payment_id={payment_id}",
                "cancelUrl": f"https://winu.app/payment/cancel?payment_id={payment_id}",
                "notifyUrl": f"https://api.winu.app/api/subscriptions/binance-pay/webhook"
            }
            
            # Make API call to Binance Pay
            headers = self._get_headers(payload)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_base}/binancepay/openapi/v2/order",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get("status") == "SUCCESS":
                        payment_url = result["data"]["checkoutUrl"]
                        
                        # Update transaction with Binance Pay response
                        transaction.payment_data.update({
                            "binance_pay_response": result["data"],
                            "checkout_url": payment_url
                        })
                        await db.commit()
                        
                        return {
                            "success": True,
                            "payment_url": payment_url,
                            "payment_id": payment_id,
                            "amount_usdt": plan["price_usdt"],
                            "plan": plan,
                            "qr_code": result["data"].get("qrCodeUrl"),
                            "message": f"Payment created for {plan['name']}"
                        }
                    else:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Binance Pay error: {result.get('message', 'Unknown error')}"
                        )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Binance Pay API error: {response.status_code}"
                    )
                    
        except Exception as e:
            logger.error(f"Error creating subscription payment: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create payment: {str(e)}")
    
    async def handle_payment_webhook(self, webhook_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """Handle Binance Pay webhook notifications."""
        try:
            payment_id = webhook_data.get("prepayId")
            status = webhook_data.get("status")
            
            if not payment_id:
                return {"success": False, "error": "Missing payment ID"}
            
            # Get transaction
            result = await db.execute(
                select(PaymentTransaction).where(PaymentTransaction.transaction_id == payment_id)
            )
            transaction = result.scalar_one_or_none()
            
            if not transaction:
                logger.error(f"Transaction not found for payment ID: {payment_id}")
                return {"success": False, "error": "Transaction not found"}
            
            # Get user
            result = await db.execute(select(User).where(User.id == transaction.user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found for transaction: {payment_id}")
                return {"success": False, "error": "User not found"}
            
            # Update transaction status
            transaction.status = "completed" if status == "SUCCESS" else "failed"
            transaction.completed_at = datetime.utcnow()
            transaction.payment_data.update({"webhook_data": webhook_data})
            
            if status == "SUCCESS":
                # Activate subscription
                await self._activate_subscription(user, transaction, db)
                
                # Create success event
                event = SubscriptionEvent(
                    user_id=user.id,
                    event_type="payment_completed",
                    event_data={
                        "plan_id": transaction.plan_id,
                        "amount_usdt": float(transaction.amount_usdt),
                        "payment_id": payment_id,
                        "transaction_id": transaction.id
                    },
                    processed=True
                )
                db.add(event)
            else:
                # Create failure event
                event = SubscriptionEvent(
                    user_id=user.id,
                    event_type="payment_failed",
                    event_data={
                        "plan_id": transaction.plan_id,
                        "payment_id": payment_id,
                        "failure_reason": webhook_data.get("message", "Unknown error")
                    },
                    processed=True
                )
                db.add(event)
            
            await db.commit()
            
            logger.info(f"Payment webhook processed: {payment_id} - {status}")
            
            return {
                "success": True,
                "message": f"Webhook processed: {status}",
                "transaction_id": transaction.id
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def _activate_subscription(self, user: User, transaction: PaymentTransaction, db: AsyncSession):
        """Activate subscription for user after successful payment."""
        try:
            plan = self.subscription_plans[transaction.plan_id]
            
            # Update user subscription
            user.subscription_tier = transaction.plan_id
            user.subscription_status = "active"
            user.payment_due_date = datetime.utcnow() + timedelta(days=30)  # 30 days from now
            user.subscription_renewal_date = datetime.utcnow() + timedelta(days=30)
            user.last_payment_date = datetime.utcnow()
            user.payment_method = "binance_pay"
            user.access_revoked_at = None  # Clear any previous revocation
            
            # Grant Telegram access if applicable
            if plan["telegram_access"] and transaction.payment_data.get("telegram_user_id"):
                # Import and use Telegram group manager
                from services.telegram_group_manager import telegram_group_manager
                
                telegram_result = await telegram_group_manager.grant_telegram_access(
                    user=user,
                    subscription_tier=transaction.plan_id,
                    telegram_user_id=transaction.payment_data["telegram_user_id"],
                    telegram_username=transaction.payment_data.get("telegram_username"),
                    db=db
                )
                
                if telegram_result["success"]:
                    logger.info(f"Telegram access granted for user {user.id}")
                else:
                    logger.warning(f"Failed to grant Telegram access for user {user.id}: {telegram_result.get('error')}")
            
            logger.info(f"Subscription activated for user {user.id}: {transaction.plan_id}")
            
        except Exception as e:
            logger.error(f"Error activating subscription: {e}")
            raise
    
    async def get_subscription_plans(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get available subscription plans."""
        try:
            # Get plans from database
            result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_active == True))
            db_plans = result.scalars().all()
            
            # Convert to dict format
            plans = []
            for plan in db_plans:
                plans.append({
                    "id": plan.id,
                    "name": plan.name,
                    "price_usd": float(plan.price_usd),
                    "price_usdt": float(plan.price_usdt),
                    "interval": plan.interval,
                    "duration_days": plan.duration_days,
                    "dashboard_access_limit": plan.dashboard_access_limit,
                    "features": plan.features,
                    "telegram_access": plan.telegram_access,
                    "support_level": plan.support_level,
                    "binance_pay_id": plan.binance_pay_id,
                    "is_active": plan.is_active
                })
            
            return plans
            
        except Exception as e:
            logger.error(f"Error getting subscription plans: {e}")
            return []
    
    async def check_payment_status(self, payment_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Check payment status."""
        try:
            result = await db.execute(
                select(PaymentTransaction).where(PaymentTransaction.transaction_id == payment_id)
            )
            transaction = result.scalar_one_or_none()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            return {
                "success": True,
                "status": transaction.status,
                "amount_usdt": float(transaction.amount_usdt),
                "plan_id": transaction.plan_id,
                "created_at": transaction.created_at,
                "completed_at": transaction.completed_at
            }
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return {"success": False, "error": str(e)}
