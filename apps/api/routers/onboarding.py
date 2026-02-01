"""User onboarding API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import stripe
import os

import sys
sys.path.append('/packages')

from common.database import User
from common.email import create_email_verification, verify_email_code, has_used_free_trial, send_welcome_email_to_user
from routers.auth import UserResponse
from dependencies import get_db
from routers.auth import get_password_hash, get_user_by_username, get_user_by_email
import stripe
from common.config import get_settings

import os
settings = get_settings()
# Initialize Stripe if available, but don't fail if not configured
try:
    # Try to get Stripe key from environment directly
    stripe_secret_key = os.getenv('STRIPE_SECRET_KEY') or getattr(settings.stripe, 'secret_key', None)
    if stripe_secret_key:
        stripe.api_key = stripe_secret_key
        print(f"✅ Stripe initialized with key: {stripe_secret_key[:20]}...")
    else:
        print("❌ No Stripe secret key found")
except Exception as e:
    print(f"❌ Error initializing Stripe: {e}")
    pass

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class UserRegistrationRequest(BaseModel):
    """User registration request."""
    username: str
    email: str
    password: str


class EmailVerificationRequest(BaseModel):
    """Email verification request."""
    email: str
    code: str


class PlanSelectionRequest(BaseModel):
    """Plan selection request."""
    plan_id: str  # free_trial, professional, vip_elite


class EmailVerificationResponse(BaseModel):
    """Email verification response."""
    success: bool
    message: str
    user: Optional[UserResponse] = None


@router.post("/register", response_model=dict)
async def register_user(
    request: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user and send verification email."""
    # Check if user already exists
    existing_user = await get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    existing_email = await get_user_by_email(db, request.email)
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user (not verified yet)
    hashed_password = get_password_hash(request.password)
    db_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_password,
        email_verified=False,
        subscription_status="inactive"
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # Send verification email
    await create_email_verification(db, db_user.id, request.email)
    
    return {
        "success": True,
        "message": "Registration successful. Please check your email for verification code.",
        "user_id": db_user.id
    }


@router.post("/verify-email", response_model=dict)
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify email with code and auto-login."""
    success = await verify_email_code(db, request.email, request.code)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code"
        )
    
    # Get verified user
    user = await get_user_by_email(db, request.email)
    
    # Send welcome email after successful verification
    try:
        await send_welcome_email_to_user(db, user.id, request.email)
    except Exception as e:
        # Log the error but don't fail the verification
        print(f"Warning: Failed to send welcome email: {e}")
    
    # Generate JWT token for auto-login
    from datetime import timedelta
    from .auth import create_access_token
    
    access_token_expires = timedelta(minutes=settings.api.jwt_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "message": "Email verified successfully! You are now logged in.",
        "user": UserResponse.from_orm(user).dict(),
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/select-plan", response_model=dict)
async def select_plan(
    request: PlanSelectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Select subscription plan."""
    # Get user by email (assuming they're logged in)
    # In a real implementation, you'd get this from JWT token
    
    valid_plans = ["free_trial", "professional", "vip_elite"]
    if request.plan_id not in valid_plans:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan selected"
        )
    
    # Check if user has already used free trial
    if request.plan_id == "free_trial":
        # This would need to be implemented with proper user identification
        # For now, we'll assume this check is done on the frontend
        pass
    
    return {
        "success": True,
        "message": f"Plan {request.plan_id} selected successfully",
        "next_step": "payment" if request.plan_id in ["professional", "vip_elite"] else "activate_trial"
    }


@router.get("/plans", response_model=dict)
async def get_available_plans():
    """Get available subscription plans."""
    return {
        "plans": [
            {
                "id": "free_trial",
                "name": "Free Trial",
                "price": 0,
                "currency": "USD",
                "duration": "7 days",
                "features": [
                    "Access to basic signals",
                    "Dashboard access",
                    "Email alerts"
                ],
                "description": "Try our service for free for 7 days"
            },
            {
                "id": "professional",
                "name": "Professional",
                "price": 14.99,
                "currency": "USD",
                "duration": "monthly",
                "features": [
                    "All Free Trial features",
                    "Real-time signals",
                    "Telegram group access",
                    "Priority support",
                    "Advanced analytics"
                ],
                "description": "Perfect for serious traders"
            },
            {
                "id": "vip_elite",
                "name": "VIP Elite",
                "price": 29.99,
                "currency": "USD",
                "duration": "monthly",
                "features": [
                    "All Professional features",
                    "Exclusive VIP signals",
                    "Personal account manager",
                    "Custom alerts",
                    "Early access to new features"
                ],
                "description": "Premium experience for elite traders"
            }
        ]
    }


@router.post("/create-checkout-session")
async def create_checkout_session(
    plan_id: str = Form(...),
    email: str = Form(...),
    success_url: str = Form(...),
    cancel_url: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Create Stripe checkout session for guest users during onboarding."""
    
    # Check if Stripe is configured
    stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
    if not stripe_secret_key:
        raise HTTPException(
            status_code=500,
            detail="Stripe is not configured. Please contact support."
        )
    
    # Define subscription plans
    PLANS = {
        "professional": {
            "name": "Professional",
            "price": 14.99
        },
        "vip_elite": {
            "name": "VIP Elite", 
            "price": 29.99
        }
    }
    
    plan = PLANS.get(plan_id)
    if not plan:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan ID"
        )
    
    try:
        # Initialize Stripe with the secret key
        stripe.api_key = stripe_secret_key
        
        # Debug: Check if Stripe is properly initialized
        print(f"Stripe API key set: {stripe.api_key[:10]}...")
        print(f"Stripe checkout available: {hasattr(stripe, 'checkout')}")
        
        # Use direct API call instead of checkout module
        import requests
        
        # Create Stripe checkout session using direct API call
        headers = {
            'Authorization': f'Bearer {stripe_secret_key}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'payment_method_types[]': 'card',
            'line_items[0][price_data][currency]': 'usd',
            'line_items[0][price_data][product_data][name]': plan['name'],
            'line_items[0][price_data][product_data][description]': f"Monthly subscription to {plan['name']} plan",
            'line_items[0][price_data][unit_amount]': int(plan['price'] * 100),
            'line_items[0][price_data][recurring][interval]': 'month',
            'line_items[0][quantity]': '1',
            'mode': 'subscription',
            'success_url': success_url,
            'cancel_url': cancel_url,
            'customer_email': email,
            'metadata[plan_id]': plan_id,
            'metadata[email]': email
        }
        
        response = requests.post(
            'https://api.stripe.com/v1/checkout/sessions',
            headers=headers,
            data=data
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Stripe API error: {response.text}"
            )
        
        checkout_data = response.json()
        
        return {
            "session_id": checkout_data['id'],
            "session_url": checkout_data['url'],
            "message": "Stripe checkout session created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/check-free-trial/{email}", response_model=dict)
async def check_free_trial_eligibility(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Check if user is eligible for free trial."""
    has_used = await has_used_free_trial(db, email)
    
    return {
        "email": email,
        "eligible": not has_used,
        "message": "Free trial available" if not has_used else "Free trial already used"
    }
