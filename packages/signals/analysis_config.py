"""Configuration for enhanced signal analysis."""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class AnalysisMode(Enum):
    """Analysis mode types."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SCALPING = "scalping"
    SWING = "swing"


@dataclass
class TechnicalAnalysisConfig:
    """Technical analysis configuration."""
    # RSI settings
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # MACD settings
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Moving Averages
    ema_periods: List[int] = None
    sma_periods: List[int] = None
    
    # ADX settings
    adx_period: int = 14
    adx_threshold: float = 25.0
    
    # Stochastic
    stoch_k: int = 14
    stoch_d: int = 3
    
    def __post_init__(self):
        if self.ema_periods is None:
            self.ema_periods = [20, 50, 200]
        if self.sma_periods is None:
            self.sma_periods = [50, 200]


@dataclass
class RiskManagementConfig:
    """Risk management configuration."""
    # Position sizing
    max_position_size: float = 0.02  # 2% of portfolio
    max_daily_risk: float = 0.05    # 5% daily risk
    
    # Stop loss settings
    default_stop_loss: float = 0.02  # 2% stop loss
    atr_stop_multiplier: float = 2.0
    
    # Take profit settings
    risk_reward_ratio: float = 2.0
    partial_profit_levels: List[float] = None
    
    # Volatility filters
    max_volatility: float = 0.10    # 10% max volatility
    min_volume: float = 1000000     # $1M min volume
    
    def __post_init__(self):
        if self.partial_profit_levels is None:
            self.partial_profit_levels = [0.5, 1.0, 2.0]


@dataclass
class ConfluenceConfig:
    """Multi-timeframe confluence configuration."""
    # Timeframes to analyze
    timeframes: List[str] = None
    
    # Confluence weights
    timeframe_weights: Dict[str, float] = None
    
    # Minimum confluence score
    min_confluence_score: float = 0.7
    
    # Critical timeframes
    critical_timeframes: List[str] = None
    
    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        if self.timeframe_weights is None:
            self.timeframe_weights = {
                '1m': 0.1, '5m': 0.15, '15m': 0.2,
                '1h': 0.25, '4h': 0.2, '1d': 0.1
            }
        if self.critical_timeframes is None:
            self.critical_timeframes = ['1h', '4h', '1d']


@dataclass
class SmartMoneyConfig:
    """Smart money analysis configuration."""
    # Order block settings
    order_block_lookback: int = 50
    order_block_min_size: float = 0.01
    
    # Fair value gap settings
    fvg_min_size: float = 0.005
    fvg_max_age: int = 100
    
    # Liquidity zone settings
    liquidity_zone_tolerance: float = 0.002
    liquidity_zone_min_touches: int = 2
    
    # Volume analysis
    volume_sma_period: int = 20
    volume_spike_threshold: float = 2.0


@dataclass
class DataSourceConfig:
    """Data source configuration."""
    # Primary exchanges
    primary_exchanges: List[str] = None
    
    # Data quality requirements
    min_price_agreement: float = 0.95  # 95% price agreement between exchanges
    max_price_variance: float = 0.01   # 1% max price variance
    
    # Update frequencies
    price_update_interval: int = 1     # seconds
    volume_update_interval: int = 5    # seconds
    indicator_update_interval: int = 60  # seconds
    
    # Data retention
    max_candles: int = 1000
    data_retention_days: int = 30
    
    def __post_init__(self):
        if self.primary_exchanges is None:
            self.primary_exchanges = ['binance', 'gate', 'coinmarketcap']


@dataclass
class AlertConfig:
    """Alert configuration."""
    # Alert channels
    telegram_enabled: bool = True
    discord_enabled: bool = True
    email_enabled: bool = False
    
    # Alert filters
    min_confidence_score: float = 0.65
    min_risk_reward_ratio: float = 1.5
    
    # Alert formatting
    include_charts: bool = True
    include_analysis: bool = True
    include_risk_metrics: bool = True
    
    # Rate limiting
    max_alerts_per_hour: int = 10
    max_alerts_per_symbol: int = 3


@dataclass
class AnalysisConfig:
    """Complete analysis configuration."""
    mode: AnalysisMode = AnalysisMode.MODERATE
    technical: TechnicalAnalysisConfig = None
    risk_management: RiskManagementConfig = None
    confluence: ConfluenceConfig = None
    smart_money: SmartMoneyConfig = None
    data_sources: DataSourceConfig = None
    alerts: AlertConfig = None
    
    def __post_init__(self):
        if self.technical is None:
            self.technical = TechnicalAnalysisConfig()
        if self.risk_management is None:
            self.risk_management = RiskManagementConfig()
        if self.confluence is None:
            self.confluence = ConfluenceConfig()
        if self.smart_money is None:
            self.smart_money = SmartMoneyConfig()
        if self.data_sources is None:
            self.data_sources = DataSourceConfig()
        if self.alerts is None:
            self.alerts = AlertConfig()
    
    def get_mode_config(self) -> Dict:
        """Get configuration based on analysis mode."""
        configs = {
            AnalysisMode.CONSERVATIVE: {
                'min_confidence': 0.8,
                'min_confluence': 0.8,
                'max_volatility': 0.05,
                'min_risk_reward': 2.5,
                'position_size': 0.01
            },
            AnalysisMode.MODERATE: {
                'min_confidence': 0.65,
                'min_confluence': 0.7,
                'max_volatility': 0.08,
                'min_risk_reward': 2.0,
                'position_size': 0.02
            },
            AnalysisMode.AGGRESSIVE: {
                'min_confidence': 0.55,
                'min_confluence': 0.6,
                'max_volatility': 0.12,
                'min_risk_reward': 1.5,
                'position_size': 0.03
            },
            AnalysisMode.SCALPING: {
                'min_confidence': 0.6,
                'min_confluence': 0.65,
                'max_volatility': 0.15,
                'min_risk_reward': 1.2,
                'position_size': 0.01,
                'timeframes': ['1m', '5m', '15m']
            },
            AnalysisMode.SWING: {
                'min_confidence': 0.7,
                'min_confluence': 0.75,
                'max_volatility': 0.06,
                'min_risk_reward': 3.0,
                'position_size': 0.025,
                'timeframes': ['4h', '1d', '1w']
            }
        }
        
        return configs.get(self.mode, configs[AnalysisMode.MODERATE])


# Predefined configurations
CONSERVATIVE_CONFIG = AnalysisConfig(mode=AnalysisMode.CONSERVATIVE)
MODERATE_CONFIG = AnalysisConfig(mode=AnalysisMode.MODERATE)
AGGRESSIVE_CONFIG = AnalysisConfig(mode=AnalysisMode.AGGRESSIVE)
SCALPING_CONFIG = AnalysisConfig(mode=AnalysisMode.SCALPING)
SWING_CONFIG = AnalysisConfig(mode=AnalysisMode.SWING)






