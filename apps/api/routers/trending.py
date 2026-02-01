"""Trending coins API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger

from common.database import Asset, Signal
from common.schemas import TrendingCoinSchema, TrendingSignalSchema, TrendingStatsSchema
from dependencies import get_db

router = APIRouter(prefix="/trending", tags=["trending"])


@router.get("/coins", response_model=List[TrendingCoinSchema])
async def get_trending_coins(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get trending coins from the database."""
    try:
        # Get active assets that have been updated recently (trending)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.execute(
            select(Asset)
            .where(
                and_(
                    Asset.active == True,
                    Asset.updated_at > cutoff_time
                )
            )
            .order_by(desc(Asset.updated_at))
            .limit(limit)
        )
        
        assets = result.scalars().all()
        
        logger.info(f"Retrieved {len(assets)} trending coins")
        return assets
        
    except Exception as e:
        logger.error(f"Error fetching trending coins: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending coins")


@router.get("/signals", response_model=List[TrendingSignalSchema])
async def get_trending_signals(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get recent signals from trending coins."""
    try:
        # Get recent signals from trending coins
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.execute(
            select(Signal)
            .where(
                and_(
                    Signal.created_at > cutoff_time,
                    Signal.context.op('->>')('trending_analysis') == 'true'
                )
            )
            .order_by(desc(Signal.created_at))
            .limit(limit)
        )
        
        signals = result.scalars().all()
        
        logger.info(f"Retrieved {len(signals)} trending signals")
        return signals
        
    except Exception as e:
        logger.error(f"Error fetching trending signals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending signals")


@router.get("/stats")
async def get_trending_stats(db: AsyncSession = Depends(get_db)):
    """Get trending coins statistics."""
    try:
        # Count active trending assets
        assets_result = await db.execute(
            select(Asset).where(Asset.active == True)
        )
        total_assets = len(assets_result.scalars().all())
        
        # Count recent trending signals
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        signals_result = await db.execute(
            select(Signal).where(
                and_(
                    Signal.created_at > cutoff_time,
                    Signal.context.op('->>')('trending_analysis') == 'true'
                )
            )
        )
        trending_signals = len(signals_result.scalars().all())
        
        # Count total signals in last 24h
        total_signals_result = await db.execute(
            select(Signal).where(Signal.created_at > cutoff_time)
        )
        total_signals = len(total_signals_result.scalars().all())
        
        return {
            "total_assets": total_assets,
            "trending_signals_24h": trending_signals,
            "total_signals_24h": total_signals,
            "trending_percentage": (trending_signals / total_signals * 100) if total_signals > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error fetching trending stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch trending statistics")

