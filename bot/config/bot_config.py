"""
Bot Configuration
Centralized configuration for the automated trading bot
"""

import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class BotSettings(BaseSettings):
    """Bot-specific configuration."""
    
    # Bot operation
    test_mode: bool = Field(default=False, env="BOT_TEST_MODE")
    auto_start: bool = Field(default=False, env="BOT_AUTO_START")
    
    # Signal selection
    min_signal_score: float = Field(default=0.65, env="BOT_MIN_SIGNAL_SCORE")  # Medium confidence signals
    max_daily_signals: int = Field(default=6, env="BOT_MAX_DAILY_SIGNALS")  # 6 signals per day (8am, 12pm, 2pm, 4pm, 8pm, 12am)
    signal_cooldown_minutes: int = Field(default=120, env="BOT_SIGNAL_COOLDOWN")  # 2 hours cooldown
    enable_duplicate_prevention: bool = Field(default=True, env="BOT_ENABLE_DUPLICATE_PREVENTION")
    max_signals_per_pair_per_day: int = Field(default=1, env="BOT_MAX_SIGNALS_PER_PAIR_PER_DAY")
    
    # Risk management
    max_risk_per_trade: float = Field(default=0.02, env="BOT_MAX_RISK_PER_TRADE")
    max_daily_loss: float = Field(default=0.05, env="BOT_MAX_DAILY_LOSS")
    max_positions: int = Field(default=3, env="BOT_MAX_POSITIONS")
    max_correlation: float = Field(default=0.7, env="BOT_MAX_CORRELATION")
    emergency_stop_loss: float = Field(default=0.10, env="BOT_EMERGENCY_STOP_LOSS")
    max_drawdown: float = Field(default=0.15, env="BOT_MAX_DRAWDOWN")
    
    # Position sizing
    kelly_fraction_max: float = Field(default=0.25, env="BOT_KELLY_FRACTION_MAX")
    max_position_size_percent: float = Field(default=0.30, env="BOT_MAX_POSITION_SIZE_PERCENT")
    
    # Market filters
    min_volume_24h: float = Field(default=1000000, env="BOT_MIN_VOLUME_24H")
    max_volatility: float = Field(default=0.15, env="BOT_MAX_VOLATILITY")
    min_liquidity: float = Field(default=500000, env="BOT_MIN_LIQUIDITY")
    
    # Leverage management
    leverage: float = Field(default=20.0, env="BOT_LEVERAGE")
    max_leverage: float = Field(default=20.0, env="BOT_MAX_LEVERAGE")
    leverage_increase_threshold: float = Field(default=0.05, env="BOT_LEVERAGE_INCREASE_THRESHOLD")
    
    # Dual trading configuration
    enable_spot_trading: bool = Field(default=True, env="BOT_ENABLE_SPOT_TRADING")
    enable_futures_trading: bool = Field(default=True, env="BOT_ENABLE_FUTURES_TRADING")
    default_trading_type: str = Field(default="auto", env="BOT_DEFAULT_TRADING_TYPE")  # auto, spot, futures
    
    # Market selection criteria
    spot_trading_criteria: Dict = Field(default={
        "min_signal_score": 0.65,  # Medium confidence signals
        "max_volatility": 0.15,    # Conservative volatility limit
        "min_timeframe": "1h",     # Allow 1h+ timeframes
        "max_leverage": 1.0        # No leverage for spot
    }, env="BOT_SPOT_TRADING_CRITERIA")
    
    futures_trading_criteria: Dict = Field(default={
        "min_signal_score": 0.70,  # High confidence for futures
        "min_volatility": 0.03,    # Minimum volatility for futures
        "max_volatility": 0.12,    # Maximum volatility limit
        "min_timeframe": "1h",     # Allow 1h+ timeframes
        "max_leverage": 20.0       # 20x leverage
    }, env="BOT_FUTURES_TRADING_CRITERIA")
    
    # Market condition filters
    enable_volatility_filter: bool = Field(default=True, env="BOT_ENABLE_VOLATILITY_FILTER")
    enable_liquidity_filter: bool = Field(default=True, env="BOT_ENABLE_LIQUIDITY_FILTER")
    enable_trend_filter: bool = Field(default=True, env="BOT_ENABLE_TREND_FILTER")
    volatility_lookback_hours: int = Field(default=24, env="BOT_VOLATILITY_LOOKBACK_HOURS")
    
    # Monitoring
    position_update_interval: int = Field(default=60, env="BOT_POSITION_UPDATE_INTERVAL")
    stats_update_interval: int = Field(default=300, env="BOT_STATS_UPDATE_INTERVAL")
    
    # Notifications
    enable_telegram_alerts: bool = Field(default=True, env="BOT_ENABLE_TELEGRAM_ALERTS")  # Signals only
    enable_discord_alerts: bool = Field(default=True, env="BOT_ENABLE_DISCORD_ALERTS")  # Signals + Errors
    enable_email_alerts: bool = Field(default=False, env="BOT_ENABLE_EMAIL_ALERTS")
    enable_trading_signals_alerts: bool = Field(default=True, env="BOT_ENABLE_TRADING_SIGNALS_ALERTS")  # Enabled
    enable_error_alerts_only: bool = Field(default=False, env="BOT_ENABLE_ERROR_ALERTS_ONLY")  # Disabled
    signal_alert_min_score: float = Field(default=0.75, env="BOT_SIGNAL_ALERT_MIN_SCORE")  # MEDIUM-HIGH confidence (75%+) - Lowered to include more pairs
    telegram_signals_only: bool = Field(default=True, env="BOT_TELEGRAM_SIGNALS_ONLY")  # Telegram: signals only
    discord_signals_and_errors: bool = Field(default=True, env="BOT_DISCORD_SIGNALS_AND_ERRORS")  # Discord: signals + errors
    
    # Logging
    log_level: str = Field(default="INFO", env="BOT_LOG_LEVEL")
    log_file: str = Field(default="/app/logs/bot.log", env="BOT_LOG_FILE")
    
    class Config:
        env_file = ".env"


class TradingPairs(BaseSettings):
    """Trading pairs configuration."""
    
    # Supported trading pairs - Top 10 cryptocurrencies + additional pairs
    supported_pairs: List[str] = Field(default=[
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", 
        "SOL/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT",
        "NEAR/USDT", "SUI/USDT", "TRX/USDT"
    ], env="BOT_SUPPORTED_PAIRS")
    
    # Pair-specific settings
    pair_settings: Dict[str, Dict] = Field(default={
        "BTC/USDT": {
            "min_quantity": 0.001,
            "max_quantity": 1.0,
            "price_precision": 2,
            "quantity_precision": 6
        },
        "ETH/USDT": {
            "min_quantity": 0.01,
            "max_quantity": 10.0,
            "price_precision": 2,
            "quantity_precision": 5
        },
        "ADA/USDT": {
            "min_quantity": 1.0,
            "max_quantity": 1000.0,
            "price_precision": 4,
            "quantity_precision": 2
        },
        "SOL/USDT": {
            "min_quantity": 0.1,
            "max_quantity": 100.0,
            "price_precision": 2,
            "quantity_precision": 3
        },
        "DOT/USDT": {
            "min_quantity": 0.1,
            "max_quantity": 100.0,
            "price_precision": 3,
            "quantity_precision": 3
        },
        "BNB/USDT": {
            "min_quantity": 0.01,
            "max_quantity": 10.0,
            "price_precision": 2,
            "quantity_precision": 4
        },
        "XRP/USDT": {
            "min_quantity": 1.0,
            "max_quantity": 1000.0,
            "price_precision": 4,
            "quantity_precision": 2
        },
        "DOGE/USDT": {
            "min_quantity": 10.0,
            "max_quantity": 10000.0,
            "price_precision": 5,
            "quantity_precision": 0
        },
        "AVAX/USDT": {
            "min_quantity": 0.1,
            "max_quantity": 100.0,
            "price_precision": 2,
            "quantity_precision": 3
        },
        "MATIC/USDT": {
            "min_quantity": 1.0,
            "max_quantity": 1000.0,
            "price_precision": 4,
            "quantity_precision": 2
        },
        "NEAR/USDT": {
            "min_quantity": 0.1,
            "max_quantity": 100.0,
            "price_precision": 3,
            "quantity_precision": 3
        },
        "SUI/USDT": {
            "min_quantity": 1.0,
            "max_quantity": 1000.0,
            "price_precision": 4,
            "quantity_precision": 2
        },
        "TRX/USDT": {
            "min_quantity": 10.0,
            "max_quantity": 10000.0,
            "price_precision": 5,
            "quantity_precision": 0
        }
    })
    
    class Config:
        env_file = ".env"


class RiskLimits(BaseSettings):
    """Risk limits configuration."""
    
    # Daily limits
    max_daily_trades: int = Field(default=5, env="BOT_MAX_DAILY_TRADES")
    max_daily_volume: float = Field(default=10000, env="BOT_MAX_DAILY_VOLUME")
    
    # Position limits
    max_position_value: float = Field(default=5000, env="BOT_MAX_POSITION_VALUE")
    max_total_exposure: float = Field(default=15000, env="BOT_MAX_TOTAL_EXPOSURE")
    
    # Time limits
    max_position_duration_hours: int = Field(default=24, env="BOT_MAX_POSITION_DURATION")
    min_time_between_trades_minutes: int = Field(default=60, env="BOT_MIN_TIME_BETWEEN_TRADES")
    
    # Correlation limits
    max_correlated_positions: int = Field(default=2, env="BOT_MAX_CORRELATED_POSITIONS")
    correlation_threshold: float = Field(default=0.7, env="BOT_CORRELATION_THRESHOLD")
    
    class Config:
        env_file = ".env"


class NotificationSettings(BaseSettings):
    """Notification settings."""
    
    # Telegram
    telegram_enabled: bool = Field(default=True, env="BOT_TELEGRAM_ENABLED")
    telegram_chat_id: str = Field(default="-1002965656200", env="BOT_TELEGRAM_CHAT_ID")
    
    # Discord
    discord_enabled: bool = Field(default=True, env="BOT_DISCORD_ENABLED")
    discord_webhook: str = Field(default="", env="BOT_DISCORD_WEBHOOK")
    
    # Email
    email_enabled: bool = Field(default=False, env="BOT_EMAIL_ENABLED")
    email_recipients: List[str] = Field(default=[], env="BOT_EMAIL_RECIPIENTS")
    
    # Alert thresholds
    pnl_alert_threshold: float = Field(default=100, env="BOT_PNL_ALERT_THRESHOLD")
    loss_alert_threshold: float = Field(default=-50, env="BOT_LOSS_ALERT_THRESHOLD")
    
    class Config:
        env_file = ".env"


# Global configuration instances
bot_settings = BotSettings()
trading_pairs = TradingPairs()
risk_limits = RiskLimits()
notification_settings = NotificationSettings()


def get_bot_config() -> Dict:
    """Get complete bot configuration."""
    return {
        "bot": bot_settings.dict(),
        "trading_pairs": trading_pairs.dict(),
        "risk_limits": risk_limits.dict(),
        "notifications": notification_settings.dict()
    }


def validate_config() -> List[str]:
    """Validate bot configuration."""
    errors = []
    
    # Validate risk settings
    if bot_settings.max_risk_per_trade > 0.05:
        errors.append("Max risk per trade should not exceed 5%")
    
    if bot_settings.max_daily_loss > 0.10:
        errors.append("Max daily loss should not exceed 10%")
    
    if bot_settings.max_positions > 5:
        errors.append("Max positions should not exceed 5")
    
    # Validate leverage settings
    if bot_settings.leverage > bot_settings.max_leverage:
        errors.append("Leverage cannot exceed max leverage")
    
    if bot_settings.max_leverage > 10.0:
        errors.append("Max leverage should not exceed 10x for safety")
    
    # Validate market filters
    if bot_settings.max_volatility > 0.5:
        errors.append("Max volatility should not exceed 50%")
    
    # Validate trading pairs
    if not trading_pairs.supported_pairs:
        errors.append("At least one trading pair must be configured")
    
    # Validate notification settings
    if notification_settings.telegram_enabled and not notification_settings.telegram_chat_id:
        errors.append("Telegram chat ID is required when Telegram is enabled")
    
    if notification_settings.discord_enabled and not notification_settings.discord_webhook:
        errors.append("Discord webhook is required when Discord is enabled")
    
    return errors


if __name__ == "__main__":
    # Print configuration
    config = get_bot_config()
    print("Bot Configuration:")
    print(json.dumps(config, indent=2))
    
    # Validate configuration
    errors = validate_config()
    if errors:
        print("\nConfiguration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n✅ Configuration is valid")







