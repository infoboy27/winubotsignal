"""Signals router for Million Trader API."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys
sys.path.append('/packages')

from common.database import Signal, Asset, User
from common.schemas import (
    Signal as SignalSchema,
    SignalDirection,
    TimeFrame,
    BacktestParams,
    BacktestResult,
    PaginatedResponse
)
from common.logging import get_logger
from .auth import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)


class SignalFilter(BaseModel):
    """Signal filtering parameters."""
    symbol: Optional[str] = None
    timeframe: Optional[TimeFrame] = None
    direction: Optional[SignalDirection] = None
    min_score: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@router.get("/recent", response_model=List[SignalSchema])
async def get_recent_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC/USDT)"),
    timeframe: Optional[TimeFrame] = Query(None, description="Filter by timeframe"),
    direction: Optional[SignalDirection] = Query(None, description="Filter by direction"),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum signal score"),
    limit: int = Query(50, ge=1, le=1000, description="Number of signals to return"),
    offset: int = Query(0, ge=0, description="Number of signals to skip"),
    db: AsyncSession = Depends(lambda: None),  # Will be injected
    current_user: User = Depends(get_current_active_user)
):
    """Get recent trading signals with optional filtering."""
    query = select(Signal).order_by(desc(Signal.created_at))
    
    # Apply filters
    filters = []
    if symbol:
        filters.append(Signal.symbol == symbol.upper())
    if timeframe:
        filters.append(Signal.timeframe == timeframe)
    if direction:
        filters.append(Signal.direction == direction)
    if min_score is not None:
        filters.append(Signal.score >= min_score)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    logger.info(f"Retrieved {len(signals)} signals for user {current_user.username}")
    return signals


@router.get("/{signal_id}", response_model=SignalSchema)
async def get_signal(
    signal_id: int,
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific signal by ID."""
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return signal


@router.get("/stats/summary")
async def get_signal_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get signal statistics summary."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Total signals
    total_result = await db.execute(
        select(func.count(Signal.id))
        .where(Signal.created_at >= start_date)
    )
    total_signals = total_result.scalar()
    
    # Signals by direction
    direction_result = await db.execute(
        select(Signal.direction, func.count(Signal.id))
        .where(Signal.created_at >= start_date)
        .group_by(Signal.direction)
    )
    direction_stats = {direction: count for direction, count in direction_result.all()}
    
    # Average score
    avg_score_result = await db.execute(
        select(func.avg(Signal.score))
        .where(Signal.created_at >= start_date)
    )
    avg_score = avg_score_result.scalar() or 0.0
    
    # High confidence signals (score >= 0.8)
    high_confidence_result = await db.execute(
        select(func.count(Signal.id))
        .where(and_(
            Signal.created_at >= start_date,
            Signal.score >= 0.8
        ))
    )
    high_confidence = high_confidence_result.scalar()
    
    # Top symbols
    top_symbols_result = await db.execute(
        select(Signal.symbol, func.count(Signal.id).label('count'))
        .where(Signal.created_at >= start_date)
        .group_by(Signal.symbol)
        .order_by(desc('count'))
        .limit(10)
    )
    top_symbols = [
        {"symbol": symbol, "count": count}
        for symbol, count in top_symbols_result.all()
    ]
    
    return {
        "period_days": days,
        "total_signals": total_signals,
        "long_signals": direction_stats.get(SignalDirection.LONG, 0),
        "short_signals": direction_stats.get(SignalDirection.SHORT, 0),
        "average_score": round(float(avg_score), 3),
        "high_confidence_signals": high_confidence,
        "high_confidence_percentage": round(
            (high_confidence / total_signals * 100) if total_signals > 0 else 0, 2
        ),
        "top_symbols": top_symbols
    }


@router.get("/performance/{symbol}")
async def get_symbol_performance(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Get performance statistics for a specific symbol."""
    symbol = symbol.upper()
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get signals for the symbol
    signals_result = await db.execute(
        select(Signal)
        .where(and_(
            Signal.symbol == symbol,
            Signal.created_at >= start_date
        ))
        .order_by(Signal.created_at)
    )
    signals = signals_result.scalars().all()
    
    if not signals:
        raise HTTPException(status_code=404, detail=f"No signals found for {symbol}")
    
    total_signals = len(signals)
    long_signals = sum(1 for s in signals if s.direction == SignalDirection.LONG)
    short_signals = total_signals - long_signals
    avg_score = sum(s.score for s in signals) / total_signals
    
    # Calculate realized PnL if available
    realized_signals = [s for s in signals if s.realized_pnl is not None]
    total_pnl = sum(float(s.realized_pnl) for s in realized_signals)
    winning_signals = sum(1 for s in realized_signals if s.realized_pnl > 0)
    win_rate = (winning_signals / len(realized_signals) * 100) if realized_signals else 0
    
    return {
        "symbol": symbol,
        "period_days": days,
        "total_signals": total_signals,
        "long_signals": long_signals,
        "short_signals": short_signals,
        "average_score": round(avg_score, 3),
        "realized_signals": len(realized_signals),
        "total_pnl": round(total_pnl, 2),
        "winning_signals": winning_signals,
        "win_rate_percent": round(win_rate, 2),
        "first_signal": signals[0].created_at,
        "last_signal": signals[-1].created_at
    }


@router.post("/backtest", response_model=dict)
async def run_backtest(
    params: BacktestParams,
    db: AsyncSession = Depends(lambda: None),
    current_user: User = Depends(get_current_active_user)
):
    """Run a backtest with specified parameters."""
    # This is a simplified backtest implementation
    # In production, this would trigger a Celery task for heavy computation
    
    logger.info(f"Starting backtest for user {current_user.username}: {params.strategy}")
    
    # Get historical signals within the date range
    query = select(Signal).where(and_(
        Signal.created_at >= params.start_date,
        Signal.created_at <= params.end_date,
        Signal.score >= params.min_score
    ))
    
    if params.symbols:
        query = query.where(Signal.symbol.in_([s.upper() for s in params.symbols]))
    
    if params.timeframes:
        query = query.where(Signal.timeframe.in_(params.timeframes))
    
    query = query.order_by(Signal.created_at)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    if not signals:
        return {
            "error": "No signals found for the specified parameters",
            "signals_count": 0
        }
    
    # Simple backtest simulation
    balance = float(params.initial_balance)
    initial_balance = balance
    trades = []
    winning_trades = 0
    losing_trades = 0
    max_drawdown = 0.0
    peak_balance = balance
    
    for signal in signals[:100]:  # Limit for demo
        if len(trades) >= params.max_positions:
            continue
        
        # Simulate trade based on signal
        risk_amount = balance * (params.risk_percent / 100)
        
        # Simple PnL simulation (this would use actual price data in production)
        if signal.realized_pnl is not None:
            pnl = float(signal.realized_pnl)
        else:
            # Simulate based on score and direction
            success_probability = signal.score
            import random
            random.seed(signal.id)  # Deterministic for consistent results
            
            if random.random() < success_probability:
                pnl = risk_amount * (1.5 + random.random())  # 1.5x to 2.5x return
                winning_trades += 1
            else:
                pnl = -risk_amount
                losing_trades += 1
        
        balance += pnl
        
        # Track drawdown
        if balance > peak_balance:
            peak_balance = balance
        
        drawdown = (peak_balance - balance) / peak_balance * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        
        trades.append({
            "signal_id": signal.id,
            "symbol": signal.symbol,
            "direction": signal.direction,
            "score": signal.score,
            "pnl": round(pnl, 2),
            "balance": round(balance, 2),
            "timestamp": signal.created_at.isoformat()
        })
    
    total_trades = len(trades)
    total_return = ((balance - initial_balance) / initial_balance) * 100
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate additional metrics
    if total_trades > 0:
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [t['pnl'] for t in trades if t['pnl'] < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)
    else:
        avg_win = avg_loss = profit_factor = expectancy = 0
    
    metrics = {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate_percent": round(win_rate, 2),
        "total_return_percent": round(total_return, 2),
        "final_balance": round(balance, 2),
        "max_drawdown_percent": round(max_drawdown, 2),
        "profit_factor": round(profit_factor, 2),
        "average_win": round(avg_win, 2),
        "average_loss": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "sharpe_ratio": 0.0,  # Would need daily returns to calculate properly
        "signals_analyzed": len(signals)
    }
    
    logger.info(f"Backtest completed for user {current_user.username}: {total_trades} trades, {total_return:.2f}% return")
    
    return {
        "params": params.dict(),
        "metrics": metrics,
        "trades": trades[-20:],  # Return last 20 trades
        "trade_count": len(trades)
    }

