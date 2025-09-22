"""Alerts router for Million Trader API."""

from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import Alert, Signal, User
from common.schemas import Alert as AlertSchema, AlertChannel
from common.logging import get_logger
from .auth import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)


@router.get("/recent", response_model=List[AlertSchema])
async def get_recent_alerts(
    channel: Optional[AlertChannel] = Query(None, description="Filter by alert channel"),
    success_only: bool = Query(False, description="Only return successful alerts"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=500, description="Number of alerts to return"),
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get recent alerts."""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = (
        select(Alert)
        .where(Alert.created_at >= start_time)
        .order_by(desc(Alert.created_at))
    )
    
    if channel:
        query = query.where(Alert.channel == channel)
    
    if success_only:
        query = query.where(Alert.success == True)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    logger.info(f"Retrieved {len(alerts)} alerts for user {current_user.username}")
    return alerts


@router.get("/stats")
async def get_alert_stats(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get alert statistics."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total alerts
    from sqlalchemy import func
    total_result = await db.execute(
        select(func.count(Alert.id))
        .where(Alert.created_at >= start_date)
    )
    total_alerts = total_result.scalar()
    
    # Success rate
    success_result = await db.execute(
        select(func.count(Alert.id))
        .where(and_(
            Alert.created_at >= start_date,
            Alert.success == True
        ))
    )
    successful_alerts = success_result.scalar()
    
    # By channel
    channel_result = await db.execute(
        select(Alert.channel, func.count(Alert.id))
        .where(Alert.created_at >= start_date)
        .group_by(Alert.channel)
    )
    channel_stats = {str(channel): count for channel, count in channel_result.all()}
    
    success_rate = (successful_alerts / total_alerts * 100) if total_alerts > 0 else 0
    
    return {
        "period_days": days,
        "total_alerts": total_alerts,
        "successful_alerts": successful_alerts,
        "failed_alerts": total_alerts - successful_alerts,
        "success_rate_percent": round(success_rate, 2),
        "by_channel": channel_stats
    }

