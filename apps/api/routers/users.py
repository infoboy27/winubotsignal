"""Users router for Million Trader API."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import User
from common.logging import get_logger
from .auth import get_current_active_user, UserResponse

router = APIRouter()
logger = get_logger(__name__)


class UserSettingsUpdate(BaseModel):
    """User settings update schema."""
    risk_percent: float
    max_positions: int
    telegram_enabled: bool
    discord_enabled: bool
    email_enabled: bool
    min_signal_score: float


@router.put("/settings", response_model=UserResponse)
async def update_user_settings(
    settings: UserSettingsUpdate,
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Update user settings."""
    current_user.risk_percent = settings.risk_percent
    current_user.max_positions = settings.max_positions
    current_user.telegram_enabled = settings.telegram_enabled
    current_user.discord_enabled = settings.discord_enabled
    current_user.email_enabled = settings.email_enabled
    current_user.min_signal_score = settings.min_signal_score
    
    await db.commit()
    await db.refresh(current_user)
    
    logger.info(f"Updated settings for user {current_user.username}")
    return current_user

