"""Billing router for subscription management with Stripe integration."""

import stripe
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.config import get_settings
from common.database import User, SubscriptionEvent
from common.schemas import (
    SubscriptionPlan, UserSubscription, CheckoutSessionRequest, 
    CheckoutSessionResponse, SubscriptionEventSchema, SubscriptionStatus
)
from common.logging import get_logger
from dependencies import get_db
from routers.auth import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Initialize Stripe (only if secret key is available)
if settings.stripe.secret_key:
    stripe.api_key = settings.stripe.secret_key

# Available subscription plans
SUBSCRIPTION_PLANS = {
    "monthly": SubscriptionPlan(
        id="price_monthly",
        name="Monthly Premium",
        price=29.99,
        currency="usd",
        interval="month",
        features=[
            "Real-time trading signals",
            "Telegram group access",
            "Dashboard access",
            "Email alerts",
            "Priority support"
        ]
    ),
    "yearly": SubscriptionPlan(
        id="price_yearly",
        name="Yearly Premium",
        price=299.99,
        currency="usd",
        interval="year",
        features=[
            "Real-time trading signals",
            "Telegram group access",
            "Dashboard access",
            "Email alerts",
            "Priority support",
            "2 months free (20% discount)"
        ]
    )
}


@router.get("/plans", response_model=List[SubscriptionPlan], tags=["Billing"])
async def get_subscription_plans():
    """Get available subscription plans."""
    if not settings.stripe.secret_key:
        return []
    return list(SUBSCRIPTION_PLANS.values())


@router.get("/subscription", response_model=UserSubscription, tags=["Billing"])
async def get_user_subscription(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's subscription information."""
    return UserSubscription(
        status=SubscriptionStatus(current_user.subscription_status),
        current_period_end=current_user.current_period_end,
        plan_id=current_user.plan_id,
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        telegram_user_id=current_user.telegram_user_id,
        subscription_created_at=current_user.subscription_created_at,
        subscription_updated_at=current_user.subscription_updated_at
    )


@router.post("/checkout", response_model=CheckoutSessionResponse, tags=["Billing"])
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for subscription."""
    try:
        # Get the plan
        plan = SUBSCRIPTION_PLANS.get(request.plan_id)
        if not plan:
            raise HTTPException(
                status_code=400,
                detail="Invalid plan ID"
            )
        
        # Create or get Stripe customer
        customer_id = current_user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.username,
                metadata={
                    "user_id": str(current_user.id),
                    "username": current_user.username
                }
            )
            customer_id = customer.id
            
            # Update user with customer ID
            current_user.stripe_customer_id = customer_id
            await db.commit()
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "plan_id": request.plan_id
            }
        )
        
        logger.info(f"Created checkout session for user {current_user.id}: {session.id}")
        
        return CheckoutSessionResponse(
            session_url=session.url,
            session_id=session.id
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Payment processing error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/checkout-guest", response_model=CheckoutSessionResponse, tags=["Billing"])
async def create_guest_checkout_session(
    plan_id: str = Form(...),
    email: str = Form(...),
    success_url: str = Form(...),
    cancel_url: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for unauthenticated users during onboarding."""
    try:
        # Get the plan
        plan = SUBSCRIPTION_PLANS.get(plan_id)
        if not plan:
            raise HTTPException(
                status_code=400,
                detail="Invalid plan ID"
            )
        
        # Create Stripe customer for guest user
        customer = stripe.Customer.create(
            email=email,
            metadata={
                "is_guest": "true",
                "email": email
            }
        )
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan['price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url or f"{settings.api.frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url or f"{settings.api.frontend_url}/payment/cancel",
            metadata={
                "plan_id": plan_id,
                "email": email,
                "is_guest": "true"
            }
        )
        
        return CheckoutSessionResponse(
            session_id=session.id,
            session_url=session.url
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating guest checkout session: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Payment processing error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating guest checkout session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/customer-portal", tags=["Billing"])
async def create_customer_portal_session(
    current_user: User = Depends(get_current_active_user)
):
    """Create Stripe customer portal session for subscription management."""
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No active subscription found"
        )
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url="https://dashboard.winu.app/billing"
        )
        
        return {"url": session.url}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating customer portal: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Error creating customer portal: {str(e)}"
        )


@router.get("/events", response_model=List[SubscriptionEventSchema], tags=["Billing"])
async def get_subscription_events(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20
):
    """Get user's subscription events for auditing."""
    result = await db.execute(
        select(SubscriptionEvent)
        .where(SubscriptionEvent.user_id == current_user.id)
        .order_by(SubscriptionEvent.created_at.desc())
        .limit(limit)
    )
    
    events = result.scalars().all()
    return [
        SubscriptionEventSchema(
            id=event.id,
            user_id=event.user_id,
            event_type=event.event_type,
            stripe_event_id=event.stripe_event_id,
            event_data=event.event_data,
            processed=event.processed,
            created_at=event.created_at
        ) for event in events
    ]


@router.post("/webhook", tags=["Billing"])
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events for subscription updates."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe.webhook_secret
        )
    except ValueError:
        logger.error("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Log the event
    logger.info(f"Received Stripe webhook: {event['type']}")
    
    try:
        if event['type'] == 'customer.subscription.created':
            await handle_subscription_created(event, db)
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event, db)
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event, db)
        elif event['type'] == 'invoice.payment_succeeded':
            await handle_payment_succeeded(event, db)
        elif event['type'] == 'invoice.payment_failed':
            await handle_payment_failed(event, db)
        
        # Store the event for auditing
        await store_subscription_event(event, db)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing webhook {event['type']}: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def handle_subscription_created(event, db: AsyncSession):
    """Handle subscription created event."""
    subscription = event['data']['object']
    customer_id = subscription['customer']
    
    # Find user by Stripe customer ID
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User not found for customer {customer_id}")
        return
    
    # Update user subscription
    user.subscription_status = "active"
    user.stripe_subscription_id = subscription['id']
    user.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
    user.subscription_created_at = datetime.utcnow()
    user.subscription_updated_at = datetime.utcnow()
    
    await db.commit()
    logger.info(f"Subscription created for user {user.id}")


async def handle_subscription_updated(event, db: AsyncSession):
    """Handle subscription updated event."""
    subscription = event['data']['object']
    customer_id = subscription['customer']
    
    # Find user by Stripe customer ID
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User not found for customer {customer_id}")
        return
    
    # Update subscription status
    status_mapping = {
        'active': 'active',
        'past_due': 'past_due',
        'canceled': 'canceled',
        'unpaid': 'past_due'
    }
    
    user.subscription_status = status_mapping.get(subscription['status'], 'inactive')
    user.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
    user.subscription_updated_at = datetime.utcnow()
    
    await db.commit()
    logger.info(f"Subscription updated for user {user.id}: {user.subscription_status}")


async def handle_subscription_deleted(event, db: AsyncSession):
    """Handle subscription deleted event."""
    subscription = event['data']['object']
    customer_id = subscription['customer']
    
    # Find user by Stripe customer ID
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User not found for customer {customer_id}")
        return
    
    # Cancel subscription
    user.subscription_status = "canceled"
    user.subscription_updated_at = datetime.utcnow()
    
    await db.commit()
    logger.info(f"Subscription canceled for user {user.id}")


async def handle_payment_succeeded(event, db: AsyncSession):
    """Handle successful payment event."""
    invoice = event['data']['object']
    customer_id = invoice['customer']
    
    # Find user by Stripe customer ID
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User not found for customer {customer_id}")
        return
    
    # Ensure subscription is active
    user.subscription_status = "active"
    user.subscription_updated_at = datetime.utcnow()
    
    await db.commit()
    logger.info(f"Payment succeeded for user {user.id}")


async def handle_payment_failed(event, db: AsyncSession):
    """Handle failed payment event."""
    invoice = event['data']['object']
    customer_id = invoice['customer']
    
    # Find user by Stripe customer ID
    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.error(f"User not found for customer {customer_id}")
        return
    
    # Mark as past due
    user.subscription_status = "past_due"
    user.subscription_updated_at = datetime.utcnow()
    
    await db.commit()
    logger.info(f"Payment failed for user {user.id}")


async def store_subscription_event(event, db: AsyncSession):
    """Store subscription event for auditing."""
    # Extract user ID from metadata or customer
    user_id = None
    if 'data' in event and 'object' in event['data']:
        obj = event['data']['object']
        if 'metadata' in obj and 'user_id' in obj['metadata']:
            user_id = int(obj['metadata']['user_id'])
        elif 'customer' in obj:
            # Find user by customer ID
            result = await db.execute(
                select(User).where(User.stripe_customer_id == obj['customer'])
            )
            user = result.scalar_one_or_none()
            if user:
                user_id = user.id
    
    if user_id:
        subscription_event = SubscriptionEvent(
            user_id=user_id,
            event_type=event['type'],
            stripe_event_id=event['id'],
            event_data=event['data'],
            processed=True
        )
        db.add(subscription_event)
        await db.commit()
