"""Database models and utilities for Million Trader."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, 
    JSON, Numeric, String, Text, func
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .schemas import AlertChannel, SignalDirection, SignalType, TimeFrame

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class Asset(Base, TimestampMixin):
    """Asset/trading pair model."""
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    base = Column(String(10), nullable=False)
    quote = Column(String(10), nullable=False)
    exchange = Column(String(50), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    
    # Market data
    market_cap_rank = Column(Integer)
    volume_24h_usd = Column(Numeric(20, 8))
    price_usd = Column(Numeric(20, 8))
    
    # Relationships
    ohlcv_data = relationship("OHLCV", back_populates="asset")
    signals = relationship("Signal", back_populates="asset")


class OHLCV(Base):
    """OHLCV candlestick data model (TimescaleDB hypertable)."""
    __tablename__ = "ohlcv"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), ForeignKey("assets.symbol"), nullable=False, index=True)
    timeframe = Column(Enum(TimeFrame), nullable=False, index=True)
    
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(20, 8), nullable=False)
    
    # Technical indicators (cached)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    bb_upper = Column(Numeric(20, 8))
    bb_lower = Column(Numeric(20, 8))
    ema_20 = Column(Numeric(20, 8))
    ema_50 = Column(Numeric(20, 8))
    ema_200 = Column(Numeric(20, 8))
    
    # Relationships
    asset = relationship("Asset", back_populates="ohlcv_data")


class Signal(Base, TimestampMixin):
    """Trading signal model."""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), ForeignKey("assets.symbol"), nullable=False, index=True)
    timeframe = Column(Enum(TimeFrame), nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False)
    direction = Column(Enum(SignalDirection), nullable=False)
    
    # Signal details
    score = Column(Float, nullable=False, index=True)
    entry_price = Column(Numeric(20, 8))
    stop_loss = Column(Numeric(20, 8))
    take_profit_1 = Column(Numeric(20, 8))
    take_profit_2 = Column(Numeric(20, 8))
    take_profit_3 = Column(Numeric(20, 8))
    risk_reward_ratio = Column(Float)
    
    # Analysis context
    confluences = Column(JSON, nullable=False, default=dict)
    context = Column(JSON, nullable=False, default=dict)
    
    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    filled_at = Column(DateTime)
    closed_at = Column(DateTime)
    realized_pnl = Column(Numeric(20, 8))
    
    # Relationships
    asset = relationship("Asset", back_populates="signals")
    alerts = relationship("Alert", back_populates="signal")


class Alert(Base, TimestampMixin):
    """Alert/notification model."""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    channel = Column(Enum(AlertChannel), nullable=False)
    
    # Alert details
    payload = Column(JSON, nullable=False, default=dict)
    sent_at = Column(DateTime)
    success = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    signal = relationship("Signal", back_populates="alerts")


class Backtest(Base, TimestampMixin):
    """Backtest run model."""
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy = Column(String(100), nullable=False)
    
    # Parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Numeric(20, 8), nullable=False)
    risk_percent = Column(Float, nullable=False)
    max_positions = Column(Integer, nullable=False)
    symbols = Column(JSON)
    timeframes = Column(JSON, nullable=False)
    min_score = Column(Float, nullable=False)
    
    # Results
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Numeric(20, 8), default=0)
    total_return_percent = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown_percent = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    expectancy = Column(Numeric(20, 8), default=0)
    
    # Additional metrics
    average_win = Column(Numeric(20, 8), default=0)
    average_loss = Column(Numeric(20, 8), default=0)
    largest_win = Column(Numeric(20, 8), default=0)
    largest_loss = Column(Numeric(20, 8), default=0)
    consecutive_wins = Column(Integer, default=0)
    consecutive_losses = Column(Integer, default=0)
    
    # Raw trade data
    trades_data = Column(JSON, nullable=False, default=list)


class PaperPosition(Base, TimestampMixin):
    """Paper trading position model."""
    __tablename__ = "paper_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(SignalDirection), nullable=False)
    
    # Position details
    entry_price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    stop_loss = Column(Numeric(20, 8))
    take_profit = Column(Numeric(20, 8))
    
    # Current status
    current_price = Column(Numeric(20, 8))
    unrealized_pnl = Column(Numeric(20, 8), default=0)
    realized_pnl = Column(Numeric(20, 8))
    
    # Timestamps
    opened_at = Column(DateTime, nullable=False, default=func.now())
    closed_at = Column(DateTime)
    is_open = Column(Boolean, default=True, nullable=False)
    
    # Related signal
    signal_id = Column(Integer, ForeignKey("signals.id"))


class User(Base, TimestampMixin):
    """User model for authentication and settings."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # User settings
    risk_percent = Column(Float, default=1.0, nullable=False)
    max_positions = Column(Integer, default=10, nullable=False)
    telegram_enabled = Column(Boolean, default=True, nullable=False)
    discord_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
    min_signal_score = Column(Float, default=0.65, nullable=False)
    preferred_timeframes = Column(JSON, default=["1h"])
    watchlist = Column(JSON, default=list)
    
    # API access
    api_key = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    api_key_created_at = Column(DateTime, default=func.now())


class MarketData(Base):
    """Market data cache for quick access."""
    __tablename__ = "market_data_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    data_type = Column(String(50), nullable=False)  # 'price', 'volume', 'market_cap', etc.
    value = Column(Numeric(20, 8), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    source = Column(String(50), nullable=False)  # 'binance', 'coingecko', etc.


class SystemMetrics(Base):
    """System performance and health metrics."""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    tags = Column(JSON, default=dict)
    
    # Common metrics: api_response_time, signal_generation_time, 
    # alert_send_success_rate, database_query_time, etc.




