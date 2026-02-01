"""
NOWPayments Integration for Cryptocurrency Payments
Supports 300+ cryptocurrencies with non-custodial payments
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

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import User, PaymentTransaction, SubscriptionEvent
from common.logging import get_logger

logger = get_logger(__name__)


class NOWPaymentsService:
    """NOWPayments service for cryptocurrency payments."""
    
    def __init__(self):
        # Configuration
        self.is_sandbox = os.getenv("NOWPAYMENTS_SANDBOX", "false").lower() == "true"
        
        # Use sandbox or production credentials based on mode
        if self.is_sandbox:
            self.api_key = os.getenv("NOWPAYMENTS_SANDBOX_API_KEY") or os.getenv("NOWPAYMENTS_API_KEY", "")
            self.secret_key = os.getenv("NOWPAYMENTS_SANDBOX_SECRET_KEY") or os.getenv("NOWPAYMENTS_SECRET_KEY", "")
            self.ipn_secret = os.getenv("NOWPAYMENTS_SANDBOX_IPN_SECRET") or os.getenv("NOWPAYMENTS_IPN_SECRET", "")
            self.base_url = "https://api-sandbox.nowpayments.io/v1"
            logger.info("🧪 NOWPayments initialized in SANDBOX mode")
        else:
            self.api_key = os.getenv("NOWPAYMENTS_API_KEY", "")
            self.secret_key = os.getenv("NOWPAYMENTS_SECRET_KEY", "")
            self.ipn_secret = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
            self.base_url = "https://api.nowpayments.io/v1"
            logger.info("💰 NOWPayments initialized in PRODUCTION mode")
        
        if not self.api_key:
            logger.warning("⚠️  NOWPayments API key not configured")
        else:
            logger.info(f"✅ NOWPayments API key configured: {self.api_key[:10]}...")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _generate_ipn_signature(self, payload: str) -> str:
        """Generate IPN signature for webhook verification."""
        return hmac.new(
            self.ipn_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
    
    async def get_available_currencies(self) -> Dict[str, Any]:
        """Get list of available cryptocurrencies."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/currencies",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to get currencies: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error getting currencies: {e}")
            raise HTTPException(status_code=500, detail="Failed to get available currencies")
    
    async def get_minimum_payment_amount(
        self, 
        currency_from: str = "usd", 
        currency_to: str = "btc"
    ) -> Dict[str, Any]:
        """Get minimum payment amount for currency pair."""
        try:
            params = {
                "currency_from": currency_from,
                "currency_to": currency_to
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/min-amount",
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to get minimum amount: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error getting minimum amount: {e}")
            raise HTTPException(status_code=500, detail="Failed to get minimum amount")
    
    async def get_estimated_price(
        self, 
        amount: float, 
        currency_from: str = "usd", 
        currency_to: str = "btc"
    ) -> Dict[str, Any]:
        """Get estimated price for payment amount."""
        try:
            params = {
                "amount": amount,
                "currency_from": currency_from,
                "currency_to": currency_to
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/estimate",
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to get estimated price: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error getting estimated price: {e}")
            raise HTTPException(status_code=500, detail="Failed to get estimated price")
    
    async def create_payment(
        self,
        price_amount: float,
        price_currency: str = "usd",
        pay_currency: str = "btc",
        order_id: str = None,
        order_description: str = "Winu Trading Bot Subscription",
        ipn_callback_url: str = None,
        case: str = None,
        customer_email: str = None,
        payout_address: str = None,
        payout_currency: str = None,
        payout_extra_id: str = None
    ) -> Dict[str, Any]:
        """Create a new payment."""
        
        if not order_id:
            order_id = f"WINU_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Default IPN callback URL
        if not ipn_callback_url:
            ipn_callback_url = f"{os.getenv('API_BASE_URL', 'https://api.winu.app')}/api/crypto-subscriptions/webhooks/nowpayments"
        
        payment_data = {
            "price_amount": price_amount,
            "price_currency": price_currency,
            "pay_currency": pay_currency,
            "order_id": order_id,
            "order_description": order_description,
            "ipn_callback_url": ipn_callback_url,
            "case": case or "success"
        }
        
        # Only add optional fields if they are provided
        if customer_email:
            payment_data["customer_email"] = customer_email
        if payout_address:
            payment_data["payout_address"] = payout_address
        if payout_currency:
            payment_data["payout_currency"] = payout_currency
        if payout_extra_id:
            payment_data["payout_extra_id"] = payout_extra_id
        
        try:
            logger.info(f"Creating NOWPayments payment with data: {payment_data}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payment",
                    json=payment_data,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    return {
                        "payment_id": data.get("payment_id"),
                        "payment_status": data.get("payment_status"),
                        "pay_address": data.get("pay_address"),
                        "price_amount": data.get("price_amount"),
                        "price_currency": data.get("price_currency"),
                        "pay_currency": data.get("pay_currency"),
                        "order_id": data.get("order_id"),
                        "order_description": data.get("order_description"),
                        "payment_url": data.get("payment_url"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at")
                    }
                else:
                    logger.error(f"NOWPayments API error - Status: {response.status_code}, Response: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to create payment: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise HTTPException(status_code=500, detail="Failed to create payment")
    
    async def create_invoice(
        self,
        price_amount: float,
        price_currency: str = "usd",
        order_id: str = None,
        order_description: str = "Winu Trading Bot Subscription",
        ipn_callback_url: str = None,
        success_url: str = None,
        cancel_url: str = None,
        customer_email: str = None
    ) -> Dict[str, Any]:
        """Create an invoice for hosted payment page."""
        
        if not order_id:
            order_id = f"WINU_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Default IPN callback URL
        if not ipn_callback_url:
            ipn_callback_url = f"{os.getenv('API_BASE_URL', 'https://api.winu.app')}/api/crypto-subscriptions/webhooks/nowpayments"
        
        # Default success/cancel URLs
        if not success_url:
            success_url = f"{os.getenv('WEB_BASE_URL', 'https://winu.app')}/payment/success"
        if not cancel_url:
            cancel_url = f"{os.getenv('WEB_BASE_URL', 'https://winu.app')}/payment/cancel"
        
        invoice_data = {
            "price_amount": price_amount,
            "price_currency": price_currency,
            "order_id": order_id,
            "order_description": order_description,
            "ipn_callback_url": ipn_callback_url,
            "success_url": success_url,
            "cancel_url": cancel_url
        }
        
        if customer_email:
            invoice_data["customer_email"] = customer_email
        
        try:
            logger.info(f"Creating NOWPayments invoice with data: {invoice_data}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/invoice",
                    json=invoice_data,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 201 or response.status_code == 200:
                    data = response.json()
                    invoice_id = data.get("id")
                    return {
                        "invoice_id": invoice_id,
                        "invoice_url": data.get("invoice_url") or f"https://nowpayments.io/payment/?iid={invoice_id}",
                        "order_id": data.get("order_id"),
                        "price_amount": data.get("price_amount"),
                        "price_currency": data.get("price_currency"),
                        "order_description": data.get("order_description"),
                        "created_at": data.get("created_at")
                    }
                else:
                    logger.error(f"NOWPayments invoice API error - Status: {response.status_code}, Response: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to create invoice: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise HTTPException(status_code=500, detail="Failed to create invoice")
    
    async def get_invoice_status(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice status by invoice ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/invoice/{invoice_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get invoice status: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to get invoice status"
                    )
        except Exception as e:
            logger.error(f"Error getting invoice status: {e}")
            raise HTTPException(status_code=500, detail="Failed to get invoice status")
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status by payment ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/payment/{payment_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to get payment status: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error getting payment status: {e}")
            raise HTTPException(status_code=500, detail="Failed to get payment status")
    
    async def get_payment_by_order_id(self, order_id: str) -> Dict[str, Any]:
        """Get payment by order ID."""
        try:
            params = {"order_id": order_id}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/payment",
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to get payment by order ID: {response.text}"
                    )
        except Exception as e:
            logger.error(f"Error getting payment by order ID: {e}")
            raise HTTPException(status_code=500, detail="Failed to get payment by order ID")
    
    async def create_subscription_payment(
        self,
        user_id: int,
        plan_id: str,
        amount_usd: float,
        pay_currency: str = "btc",
        customer_email: str = None,
        use_invoice: bool = True
    ) -> Dict[str, Any]:
        """Create a subscription payment using NOWPayments."""
        
        # Generate unique order ID
        order_id = f"WINU_SUB_{user_id}_{plan_id}_{int(time.time())}"
        
        # Use invoice for better UX (hosted payment page)
        if use_invoice:
            invoice_result = await self.create_invoice(
                price_amount=amount_usd,
                price_currency="usd",
                order_id=order_id,
                order_description=f"Winu Trading Bot - {plan_id.replace('_', ' ').title()} Subscription",
                customer_email=customer_email
            )
            
            return {
                "success": True,
                "invoice_id": invoice_result["invoice_id"],
                "order_id": order_id,
                "payment_url": invoice_result["invoice_url"],
                "amount": invoice_result["price_amount"],
                "currency": "USD",
                "status": "waiting",
                "created_at": invoice_result["created_at"],
                "message": "Please complete payment on NOWPayments"
            }
        else:
            # Fallback to direct payment method
            payment_result = await self.create_payment(
                price_amount=amount_usd,
                price_currency="usd",
                pay_currency=pay_currency,
                order_id=order_id,
                order_description=f"Winu Trading Bot - {plan_id} Subscription",
                customer_email=customer_email
            )
            
            return {
                "success": True,
                "payment_id": payment_result["payment_id"],
                "order_id": order_id,
                "pay_address": payment_result["pay_address"],
                "amount": payment_result["price_amount"],
                "currency": payment_result["pay_currency"],
                "payment_url": payment_result.get("payment_url"),
                "status": payment_result["payment_status"],
                "created_at": payment_result["created_at"],
                "message": f"Payment created for {pay_currency.upper()}"
            }
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature."""
        if not self.ipn_secret:
            logger.warning("IPN secret not configured, skipping signature verification")
            return True
        
        expected_signature = self._generate_ipn_signature(payload)
        return hmac.compare_digest(signature, expected_signature)


# Popular cryptocurrencies supported by NOWPayments
POPULAR_CRYPTOCURRENCIES = [
    {"symbol": "btc", "name": "Bitcoin", "network": "btc"},
    {"symbol": "eth", "name": "Ethereum", "network": "eth"},
    {"symbol": "usdt", "name": "Tether", "network": "trc20"},
    {"symbol": "usdc", "name": "USD Coin", "network": "eth"},
    {"symbol": "bnb", "name": "Binance Coin", "network": "bsc"},
    {"symbol": "ada", "name": "Cardano", "network": "ada"},
    {"symbol": "sol", "name": "Solana", "network": "sol"},
    {"symbol": "dot", "name": "Polkadot", "network": "dot"},
    {"symbol": "matic", "name": "Polygon", "network": "polygon"},
    {"symbol": "ltc", "name": "Litecoin", "network": "ltc"},
    {"symbol": "bch", "name": "Bitcoin Cash", "network": "bch"},
    {"symbol": "xrp", "name": "Ripple", "network": "xrp"},
    {"symbol": "doge", "name": "Dogecoin", "network": "doge"},
    {"symbol": "shib", "name": "Shiba Inu", "network": "eth"},
    {"symbol": "avax", "name": "Avalanche", "network": "avax"}
]