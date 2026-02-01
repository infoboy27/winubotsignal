"""
Binance Pay Direct Debit Integration for Subscription Payments
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

logger = get_logger(__name__)


class BinancePayService:
    """Binance Pay Direct Debit service for subscription payments."""
    
    def __init__(self):
        # Load from environment variables
        self.api_key = os.getenv("BINANCE_PAY_API_KEY", "")
        self.secret_key = os.getenv("BINANCE_PAY_SECRET_KEY", "")
        self.merchant_id = os.getenv("BINANCE_PAY_MERCHANT_ID", "")
        self.webhook_secret = os.getenv("BINANCE_PAY_WEBHOOK_SECRET", "")
        self.base_url = "https://bpay.binanceapi.com"
        
        if not all([self.api_key, self.secret_key, self.merchant_id]):
            logger.warning("Binance Pay credentials not configured")
        
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
            "BinancePay-Nonce": str(int(time.time())),
            "BinancePay-Certificate-SN": self.api_key,
            "BinancePay-Signature": signature
        }
    
    async def create_direct_debit_contract(
        self,
        user_id: int,
        plan_id: str,
        amount: float,
        currency: str = "USDT",
        billing_cycle: str = "monthly"
    ) -> Dict[str, Any]:
        """Create a Direct Debit contract for subscription."""
        
        contract_code = f"WinuSub_{user_id}_{int(time.time())}"
        
        params = {
            "merchantId": self.merchant_id,
            "contractCode": contract_code,
            "amount": amount,
            "currency": currency,
            "billingCycle": billing_cycle,
            "description": f"Winu Trading Bot Subscription - Plan {plan_id}",
            "callbackUrl": "https://api.winu.app/webhooks/binance-pay",
            "returnUrl": "https://winu.app/subscription/success",
            "cancelUrl": "https://winu.app/subscription/cancel"
        }
        
        headers = self._get_headers(params)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/binancepay/openapi/v2/contract/create",
                    json=params,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "000000":  # Success
                        return {
                            "contract_code": contract_code,
                            "contract_id": data["data"]["contractId"],
                            "authorization_url": data["data"]["authorizationUrl"],
                            "status": "pending_authorization"
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Binance Pay error: {data.get('message', 'Unknown error')}"
                        )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to create Binance Pay contract"
                    )
                    
        except httpx.TimeoutException:
            raise HTTPException(status_code=408, detail="Binance Pay API timeout")
        except Exception as e:
            logger.error(f"Binance Pay contract creation error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def get_contract_status(self, contract_id: str) -> Dict[str, Any]:
        """Get the status of a Direct Debit contract."""
        
        params = {
            "merchantId": self.merchant_id,
            "contractId": contract_id
        }
        
        headers = self._get_headers(params)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/binancepay/openapi/v2/contract/query",
                    params=params,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "000000":
                        return {
                            "status": data["data"]["status"],
                            "authorized": data["data"]["status"] == "AUTHORIZED",
                            "expires_at": data["data"].get("expireTime")
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Binance Pay error: {data.get('message', 'Unknown error')}"
                        )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to query contract status"
                    )
                    
        except Exception as e:
            logger.error(f"Binance Pay contract query error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def apply_payment(
        self,
        contract_id: str,
        amount: float,
        currency: str = "USDT",
        description: str = "Winu Trading Bot Subscription Payment"
    ) -> Dict[str, Any]:
        """Apply a payment using an authorized Direct Debit contract."""
        
        payment_id = f"WinuPay_{int(time.time())}"
        
        params = {
            "merchantId": self.merchant_id,
            "contractId": contract_id,
            "paymentId": payment_id,
            "amount": amount,
            "currency": currency,
            "description": description
        }
        
        headers = self._get_headers(params)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/binancepay/openapi/v2/payment/apply",
                    json=params,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "000000":
                        return {
                            "payment_id": payment_id,
                            "status": data["data"]["status"],
                            "transaction_id": data["data"].get("transactionId"),
                            "paid_at": data["data"].get("paidTime")
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Binance Pay payment error: {data.get('message', 'Unknown error')}"
                        )
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to apply Binance Pay payment"
                    )
                    
        except Exception as e:
            logger.error(f"Binance Pay payment application error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def cancel_contract(self, contract_id: str) -> bool:
        """Cancel a Direct Debit contract."""
        
        params = {
            "merchantId": self.merchant_id,
            "contractId": contract_id
        }
        
        headers = self._get_headers(params)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/binancepay/openapi/v2/contract/cancel",
                    json=params,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("code") == "000000"
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Binance Pay contract cancellation error: {e}")
            return False
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle Binance Pay webhook notifications."""
        
        try:
            event_type = payload.get("eventType")
            
            if event_type == "CONTRACT_STATUS_CHANGE":
                contract_id = payload["data"]["contractId"]
                status = payload["data"]["status"]
                
                # Update contract status in database
                await self._update_contract_status(contract_id, status)
                
                return {"status": "success", "message": "Contract status updated"}
                
            elif event_type == "PAYMENT_SUCCESS":
                payment_id = payload["data"]["paymentId"]
                transaction_id = payload["data"]["transactionId"]
                amount = payload["data"]["amount"]
                currency = payload["data"]["currency"]
                
                # Process successful payment
                await self._process_successful_payment(
                    payment_id, transaction_id, amount, currency
                )
                
                return {"status": "success", "message": "Payment processed"}
                
            elif event_type == "PAYMENT_FAILED":
                payment_id = payload["data"]["paymentId"]
                reason = payload["data"].get("reason", "Unknown")
                
                # Handle failed payment
                await self._process_failed_payment(payment_id, reason)
                
                return {"status": "success", "message": "Payment failure processed"}
                
            else:
                logger.warning(f"Unknown Binance Pay webhook event: {event_type}")
                return {"status": "ignored", "message": f"Unknown event type: {event_type}"}
                
        except Exception as e:
            logger.error(f"Binance Pay webhook handling error: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _update_contract_status(self, contract_id: str, status: str):
        """Update contract status in database."""
        # Implementation depends on your database structure
        # This is a placeholder - implement based on your needs
        logger.info(f"Contract {contract_id} status updated to {status}")
    
    async def _process_successful_payment(
        self, payment_id: str, transaction_id: str, amount: float, currency: str
    ):
        """Process successful payment and update subscription."""
        # Implementation depends on your database structure
        # This is a placeholder - implement based on your needs
        logger.info(f"Payment {payment_id} successful: {amount} {currency}")
    
    async def _process_failed_payment(self, payment_id: str, reason: str):
        """Process failed payment."""
        # Implementation depends on your database structure
        # This is a placeholder - implement based on your needs
        logger.info(f"Payment {payment_id} failed: {reason}")


# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    "basic": {
        "name": "Basic Plan",
        "price_usd": 15.00,
        "price_usdt": 15.00,  # 1:1 USD to USDT for simplicity
        "features": [
            "Basic trading signals",
            "Email alerts", 
            "Web dashboard access",
            "Community Discord access",
            "Basic support"
        ],
        "max_positions": 3,
        "min_signal_score": 0.70,
        "telegram_access": False
    },
    "pro": {
        "name": "Pro Plan", 
        "price_usd": 40.00,
        "price_usdt": 40.00,
        "features": [
            "All trading signals",
            "Telegram alerts & group access",
            "Priority support",
            "Advanced analytics",
            "Risk management tools",
            "Mobile app access"
        ],
        "max_positions": 5,
        "min_signal_score": 0.65,
        "telegram_access": True
    },
    "premium": {
        "name": "Premium Plan",
        "price_usd": 80.00,
        "price_usdt": 80.00,
        "features": [
            "All trading signals",
            "Exclusive Telegram VIP group",
            "24/7 priority support",
            "Custom trading strategies",
            "API access",
            "Advanced analytics",
            "Portfolio management",
            "Direct access to trading team"
        ],
        "max_positions": 10,
        "min_signal_score": 0.60,
        "telegram_access": True
    }
}


async def create_subscription_with_binance_pay(
    user_id: int,
    plan_id: str,
    db: AsyncSession
) -> Dict[str, Any]:
    """Create a subscription using Binance Pay Direct Debit."""
    
    if plan_id not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    binance_pay = BinancePayService()
    
    try:
        # Create Direct Debit contract
        contract_result = await binance_pay.create_direct_debit_contract(
            user_id=user_id,
            plan_id=plan_id,
            amount=plan["price_usdt"],
            currency="USDT",
            billing_cycle="monthly"
        )
        
        return {
            "plan": plan,
            "contract": contract_result,
            "authorization_url": contract_result["authorization_url"],
            "message": "Please authorize the Direct Debit contract in your Binance account"
        }
        
    except Exception as e:
        logger.error(f"Subscription creation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")
