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

# Database session dependency
def get_db():
    """Get database session - placeholder function."""
    # This is a placeholder - actual implementation would be in the main app
    pass


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
    
    # Subscription fields
    subscription_status = Column(String(50), default="inactive", nullable=False)  # active, past_due, canceled, inactive
    subscription_tier = Column(String(20), default="free", nullable=False)  # free, professional, vip_elite
    current_period_end = Column(DateTime)
    plan_id = Column(String(100))  # Stripe plan ID
    stripe_customer_id = Column(String(255), unique=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    telegram_user_id = Column(String(100))  # Telegram user ID for group access
    subscription_created_at = Column(DateTime)
    subscription_updated_at = Column(DateTime)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # New subscription system fields
    trial_start_date = Column(DateTime)
    trial_used = Column(Boolean, default=False, nullable=False)
    trial_dashboard_access_count = Column(Integer, default=0, nullable=False)
    binance_pay_merchant_id = Column(String(50), default="287402909")
    payment_due_date = Column(DateTime)
    access_revoked_at = Column(DateTime)
    subscription_renewal_date = Column(DateTime)
    last_payment_date = Column(DateTime)
    payment_method = Column(String(50), default="binance_pay")  # binance_pay, stripe, etc.
    
    # Relationships
    email_verifications = relationship("EmailVerification", back_populates="user")
    subscription_events = relationship("SubscriptionEvent", back_populates="user")


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


class EmailVerification(Base, TimestampMixin):
    """Email verification model."""
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String(255), nullable=False)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="email_verifications")


class SubscriptionEvent(Base, TimestampMixin):
    """Subscription events for auditing and support."""
    __tablename__ = "subscription_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # subscription.created, subscription.updated, etc.
    stripe_event_id = Column(String(255), unique=True, index=True)
    event_data = Column(JSON, nullable=False, default=dict)
    processed = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User")


class SubscriptionPlan(Base, TimestampMixin):
    """Subscription plans configuration."""
    __tablename__ = "subscription_plans"
    
    id = Column(String(50), primary_key=True)  # free_trial, professional, vip_elite
    name = Column(String(100), nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)
    price_usdt = Column(Numeric(10, 2), nullable=False)
    interval = Column(String(20), nullable=False)  # monthly, yearly, trial
    duration_days = Column(Integer)  # NULL for unlimited
    dashboard_access_limit = Column(Integer)  # -1 for unlimited, 1 for trial
    features = Column(JSON, nullable=False, default=list)
    telegram_access = Column(Boolean, default=False, nullable=False)
    support_level = Column(String(20), default="none", nullable=False)  # none, priority, 24/7
    binance_pay_id = Column(String(50))  # Binance Pay merchant ID
    is_active = Column(Boolean, default=True, nullable=False)


class PaymentTransaction(Base, TimestampMixin):
    """Payment transactions tracking."""
    __tablename__ = "payment_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(String(50), ForeignKey("subscription_plans.id"), nullable=False)
    amount_usd = Column(Numeric(10, 2), nullable=False)
    amount_usdt = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)  # binance_pay, stripe, etc.
    transaction_id = Column(String(255), unique=True, index=True)  # External transaction ID
    status = Column(String(20), nullable=False)  # pending, completed, failed, refunded
    payment_data = Column(JSON)  # Store payment provider specific data
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User")
    plan = relationship("SubscriptionPlan")


class TelegramGroupAccess(Base, TimestampMixin):
    """Telegram group access management."""
    __tablename__ = "telegram_group_access"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    telegram_user_id = Column(String(100), index=True)
    telegram_username = Column(String(100))
    group_name = Column(String(100), nullable=False)  # professional_group, vip_group
    access_granted_at = Column(DateTime, default=func.now())
    access_revoked_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    user = relationship("User")




