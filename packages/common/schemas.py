"""Pydantic schemas for Million Trader."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class TimeFrame(str, Enum):
    """Available timeframes for analysis."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


class SignalDirection(str, Enum):
    """Signal direction."""
    LONG = "LONG"
    SHORT = "SHORT"


class SignalType(str, Enum):
    """Types of trading signals."""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class AlertChannel(str, Enum):
    """Available alert channels."""
    WEB = "WEB"
    TELEGRAM = "TELEGRAM"
    DISCORD = "DISCORD"
    EMAIL = "EMAIL"


class AssetBase(BaseModel):
    """Base asset schema."""
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTC/USDT)")
    name: str = Field(..., description="Asset name")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    exchange: str = Field(..., description="Exchange name")
    active: bool = Field(True, description="Whether the asset is active")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if '/' not in v:
            raise ValueError('Symbol must contain a slash (e.g., BTC/USDT)')
        return v.upper()


class Asset(AssetBase):
    """Asset with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class OHLCVBase(BaseModel):
    """Base OHLCV data schema."""
    symbol: str
    timeframe: TimeFrame
    timestamp: datetime
    open: Decimal = Field(..., decimal_places=8)
    high: Decimal = Field(..., decimal_places=8)
    low: Decimal = Field(..., decimal_places=8)
    close: Decimal = Field(..., decimal_places=8)
    volume: Decimal = Field(..., decimal_places=8)


class OHLCV(OHLCVBase):
    """OHLCV with database fields."""
    id: int
    
    class Config:
        from_attributes = True


class SignalConfluence(BaseModel):
    """Signal confluence data."""
    trend: bool = Field(False, description="Trend alignment")
    smooth_trail: bool = Field(False, description="Smooth trail support/resistance")
    liquidity: bool = Field(False, description="Liquidity validation")
    smart_money: bool = Field(False, description="Smart money flow")
    volume: bool = Field(False, description="Volume confirmation")


class SignalBase(BaseModel):
    """Base signal schema."""
    symbol: str
    timeframe: TimeFrame
    signal_type: SignalType
    direction: SignalDirection
    score: float = Field(..., ge=0.0, le=1.0, description="Signal confidence score")
    entry_price: Optional[Decimal] = Field(None, decimal_places=8)
    stop_loss: Optional[Decimal] = Field(None, decimal_places=8)
    take_profit_1: Optional[Decimal] = Field(None, decimal_places=8)
    take_profit_2: Optional[Decimal] = Field(None, decimal_places=8)
    take_profit_3: Optional[Decimal] = Field(None, decimal_places=8)
    risk_reward_ratio: Optional[float] = Field(None, description="Risk to reward ratio")
    confluences: SignalConfluence
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    @validator('risk_reward_ratio')
    def validate_risk_reward(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Risk reward ratio must be positive')
        return v


class Signal(SignalBase):
    """Signal with database fields."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertBase(BaseModel):
    """Base alert schema."""
    signal_id: int
    channel: AlertChannel
    payload: Dict[str, Any] = Field(default_factory=dict)
    sent_at: Optional[datetime] = None
    success: bool = Field(False, description="Whether alert was sent successfully")
    error_message: Optional[str] = None


class Alert(AlertBase):
    """Alert with database fields."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BacktestParams(BaseModel):
    """Backtesting parameters."""
    strategy: str
    start_date: datetime
    end_date: datetime
    initial_balance: Decimal = Field(default=Decimal("10000"))
    risk_percent: float = Field(default=1.0, ge=0.1, le=10.0)
    max_positions: int = Field(default=10, ge=1, le=100)
    symbols: Optional[List[str]] = None
    timeframes: List[TimeFrame] = Field(default=[TimeFrame.ONE_HOUR])
    min_score: float = Field(default=0.65, ge=0.0, le=1.0)


class BacktestMetrics(BaseModel):
    """Backtesting results metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: Decimal
    total_return_percent: float
    sharpe_ratio: float
    max_drawdown_percent: float
    profit_factor: float
    expectancy: Decimal
    average_win: Decimal
    average_loss: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    consecutive_wins: int
    consecutive_losses: int


class BacktestResult(BaseModel):
    """Complete backtest result."""
    id: int
    params: BacktestParams
    metrics: BacktestMetrics
    trades: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaperPositionBase(BaseModel):
    """Base paper trading position."""
    symbol: str
    side: SignalDirection
    entry_price: Decimal = Field(..., decimal_places=8)
    quantity: Decimal = Field(..., decimal_places=8)
    stop_loss: Optional[Decimal] = Field(None, decimal_places=8)
    take_profit: Optional[Decimal] = Field(None, decimal_places=8)
    current_price: Optional[Decimal] = Field(None, decimal_places=8)
    unrealized_pnl: Optional[Decimal] = Field(None, decimal_places=8)
    opened_at: datetime
    closed_at: Optional[datetime] = None
    is_open: bool = Field(True)


class PaperPosition(PaperPositionBase):
    """Paper position with database fields."""
    id: int
    realized_pnl: Optional[Decimal] = Field(None, decimal_places=8)
    
    class Config:
        from_attributes = True


class UserSettings(BaseModel):
    """User settings schema."""
    risk_percent: float = Field(default=1.0, ge=0.1, le=10.0)
    max_positions: int = Field(default=10, ge=1, le=100)
    telegram_enabled: bool = Field(default=True)
    discord_enabled: bool = Field(default=True)
    email_enabled: bool = Field(default=False)
    min_signal_score: float = Field(default=0.65, ge=0.0, le=1.0)
    preferred_timeframes: List[TimeFrame] = Field(default=[TimeFrame.ONE_HOUR])
    watchlist: List[str] = Field(default_factory=list)


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)


class APIResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Paginated response schema."""
    items: List[Any]
    total: int
    page: int = Field(default=1, ge=1)
    size: int = Field(default=50, ge=1, le=1000)
    pages: int
    has_next: bool
    has_prev: bool

