"""Backtests router for Million Trader API."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import Backtest, User
from common.schemas import BacktestResult
from common.logging import get_logger
from .auth import get_current_active_user
from dependencies import get_db

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[BacktestResult])
async def get_backtests(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get backtest results."""
    query = (
        select(Backtest)
        .order_by(desc(Backtest.created_at))
        .limit(limit)
    )
    
    result = await db.execute(query)
    backtests = result.scalars().all()
    
    return backtests


@router.get("/{backtest_id}", response_model=BacktestResult)
async def get_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific backtest result."""
    result = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id)
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    return backtest



