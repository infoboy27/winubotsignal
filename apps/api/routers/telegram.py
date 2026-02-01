"""Telegram bot integration for user validation."""

import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User
from common.logging import get_logger
from dependencies import get_db
from routers.auth import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)


class TelegramLinkRequest(BaseModel):
    """Request to link Telegram account."""
    telegram_username: str


class TelegramLinkResponse(BaseModel):
    """Response with Telegram linking instructions."""
    verification_code: str
    instructions: str
    expires_at: datetime


class TelegramStatus(BaseModel):
    """Telegram account status."""
    is_linked: bool
    telegram_user_id: Optional[str]
    telegram_username: Optional[str]
    linked_at: Optional[datetime]


@router.post("/link", response_model=TelegramLinkResponse, tags=["Telegram"])
async def link_telegram_account(
    request: TelegramLinkRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate verification code for Telegram account linking."""
    
    # Check if user already has Telegram linked
    if current_user.telegram_user_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram account already linked"
        )
    
    # Generate verification code
    verification_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes expiry
    
    # Store verification code in user's settings (temporary)
    if not current_user.watchlist:
        current_user.watchlist = {}
    
    current_user.watchlist['telegram_verification'] = {
        'code': verification_code,
        'username': request.telegram_username,
        'expires_at': expires_at.isoformat()
    }
    
    await db.commit()
    
    logger.info(f"Generated Telegram verification code for user {current_user.id}")
    
    return TelegramLinkResponse(
        verification_code=verification_code,
        instructions=f"""
To link your Telegram account:

1. Open Telegram and search for @WinuBotSignal
2. Start a conversation with the bot
3. Send the command: /link {verification_code}
4. The bot will verify your account and link it to your subscription

Your verification code expires in 10 minutes.
        """.strip(),
        expires_at=expires_at
    )


@router.post("/verify", tags=["Telegram"])
async def verify_telegram_code(
    code: str = Query(..., description="Verification code from Telegram bot"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify Telegram linking code."""
    
    # Check if user has pending verification
    if not current_user.watchlist or 'telegram_verification' not in current_user.watchlist:
        raise HTTPException(
            status_code=400,
            detail="No pending Telegram verification found"
        )
    
    verification_data = current_user.watchlist['telegram_verification']
    
    # Check if code matches
    if verification_data['code'] != code:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification code"
        )
    
    # Check if code is expired
    expires_at = datetime.fromisoformat(verification_data['expires_at'])
    if datetime.utcnow() > expires_at:
        # Clean up expired verification
        del current_user.watchlist['telegram_verification']
        await db.commit()
        
        raise HTTPException(
            status_code=400,
            detail="Verification code has expired"
        )
    
    # Link Telegram account
    current_user.telegram_user_id = f"@{verification_data['username']}"
    
    # Clean up verification data
    del current_user.watchlist['telegram_verification']
    
    await db.commit()
    
    logger.info(f"Telegram account linked for user {current_user.id}: {current_user.telegram_user_id}")
    
    return {
        "message": "Telegram account successfully linked!",
        "telegram_user_id": current_user.telegram_user_id
    }


@router.get("/status", response_model=TelegramStatus, tags=["Telegram"])
async def get_telegram_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get current Telegram account status."""
    
    return TelegramStatus(
        is_linked=bool(current_user.telegram_user_id),
        telegram_user_id=current_user.telegram_user_id,
        telegram_username=current_user.telegram_user_id.replace('@', '') if current_user.telegram_user_id else None,
        linked_at=current_user.subscription_created_at if current_user.telegram_user_id else None
    )


@router.delete("/unlink", tags=["Telegram"])
async def unlink_telegram_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlink Telegram account."""
    
    if not current_user.telegram_user_id:
        raise HTTPException(
            status_code=400,
            detail="No Telegram account linked"
        )
    
    current_user.telegram_user_id = None
    await db.commit()
    
    logger.info(f"Telegram account unlinked for user {current_user.id}")
    
    return {"message": "Telegram account unlinked successfully"}


# Mock Telegram bot webhook endpoint (for testing)
@router.post("/webhook", tags=["Telegram"])
async def telegram_webhook(
    update: dict,
    current_user: User = Depends(get_current_active_user)
):
    """
    Mock Telegram bot webhook for testing.
    In production, this would be handled by a separate Telegram bot service.
    """
    
    # This is a mock implementation
    # In production, you would:
    # 1. Set up a separate Telegram bot service
    # 2. Handle /start, /link, /help commands
    # 3. Verify users against your database
    # 4. Send confirmation messages
    
    logger.info(f"Mock Telegram webhook received: {update}")
    
    return {"status": "received"}
