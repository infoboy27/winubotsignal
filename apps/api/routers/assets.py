"""Assets router for Million Trader API."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import Asset, User
from common.schemas import Asset as AssetSchema
from common.logging import get_logger
from .auth import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[AssetSchema])
async def get_assets(
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    active_only: bool = Query(True, description="Only return active assets"),
    limit: int = Query(100, ge=1, le=1000, description="Number of assets to return"),
    offset: int = Query(0, ge=0, description="Number of assets to skip"),
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get available trading assets/pairs."""
    query = select(Asset).order_by(Asset.symbol)
    
    if active_only:
        query = query.where(Asset.active == True)
    
    if exchange:
        query = query.where(Asset.exchange == exchange.lower())
    
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    assets = result.scalars().all()
    
    logger.info(f"Retrieved {len(assets)} assets for user {current_user.username}")
    return assets


@router.get("/top", response_model=List[AssetSchema])
async def get_top_assets(
    limit: int = Query(50, ge=1, le=200, description="Number of top assets to return"),
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get top assets by market cap or volume."""
    query = (
        select(Asset)
        .where(Asset.active == True)
        .order_by(desc(Asset.volume_24h_usd))
        .limit(limit)
    )
    
    result = await db.execute(query)
    assets = result.scalars().all()
    
    return assets


@router.get("/{symbol}", response_model=AssetSchema)
async def get_asset(
    symbol: str,
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific asset by symbol."""
    result = await db.execute(
        select(Asset).where(Asset.symbol == symbol.upper())
    )
    asset = result.scalar_one_or_none()
    
    if not asset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return asset

