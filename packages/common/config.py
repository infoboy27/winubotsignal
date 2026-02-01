"""Configuration management for Million Trader."""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    host: str = Field(default="winu-bot-signal-postgres", env="POSTGRES_HOST")
    port: int = Field(default=5432, env="POSTGRES_PORT")
    database: str = Field(default="winudb", env="POSTGRES_DB")
    username: str = Field(default="winu", env="POSTGRES_USER")
    password: str = Field(default="winu250420", env="POSTGRES_PASSWORD")
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def sync_url(self) -> str:
        """Get synchronous database URL."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisSettings(BaseSettings):
    """Redis configuration."""
    url: str = Field(default="redis://winu-bot-signal-redis:6379/0", env="REDIS_URL")
    
    @property
    def broker_url(self) -> str:
        """Get Celery broker URL."""
        return os.getenv("CELERY_BROKER_URL", self.url)
    
    @property
    def result_backend(self) -> str:
        """Get Celery result backend URL."""
        return os.getenv("CELERY_RESULT_BACKEND", self.url.replace("/0", "/1"))


class ExchangeSettings(BaseSettings):
    """Exchange API configuration."""
    binance_api_key: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    binance_api_secret: Optional[str] = Field(default=None, env="BINANCE_API_SECRET")
    gate_api_key: Optional[str] = Field(default=None, env="GATE_API_KEY")
    gate_api_secret: Optional[str] = Field(default=None, env="GATE_API_SECRET")
    
    @validator('binance_api_key', 'binance_api_secret', 'gate_api_key', 'gate_api_secret')
    def validate_api_credentials(cls, v):
        if v == "your_api_key_here" or v == "your_api_secret_here":
            return None
        return v


class MarketDataSettings(BaseSettings):
    """Market data API configuration."""
    cmc_api_key: Optional[str] = Field(default=None, env="CMC_API_KEY")
    coingecko_api_base: str = Field(
        default="https://api.coingecko.com/api/v3", 
        env="COINGECKO_API_BASE"
    )
    
    @validator('cmc_api_key')
    def validate_cmc_key(cls, v):
        if v == "your_coinmarketcap_api_key_here":
            return None
        return v


class MessagingSettings(BaseSettings):
    """Messaging and alerts configuration."""
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, env="TELEGRAM_CHAT_ID")
    discord_webhook_url: Optional[str] = Field(default=None, env="DISCORD_WEBHOOK_URL")
    
    @validator('telegram_bot_token', 'telegram_chat_id', 'discord_webhook_url')
    def validate_messaging_credentials(cls, v):
        if v and ("your_" in v or "_here" in v):
            return None
        return v


class EmailSettings(BaseSettings):
    """Email configuration."""
    sender_email: str = Field(default="noreply@winu.app", env="EMAIL_SENDER")
    sender_password: str = Field(default="", env="EMAIL_PASSWORD")
    smtp_server: str = Field(default="smtp.gmail.com", env="EMAIL_SMTP_SERVER")
    smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")


class StripeSettings(BaseSettings):
    """Stripe payment configuration."""
    secret_key: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    publishable_key: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    webhook_secret: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")


class APISettings(BaseSettings):
    """API server configuration."""
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    jwt_secret: str = Field(default="supersecret", env="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    @validator('jwt_secret')
    def validate_jwt_secret(cls, v):
        if v == "supersecret" or len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long and not use default value")
        return v


class TradingSettings(BaseSettings):
    """Trading and risk management configuration."""
    default_risk_percent: float = Field(default=1.0, env="DEFAULT_RISK_PERCENT")
    max_daily_loss_percent: float = Field(default=5.0, env="MAX_DAILY_LOSS_PERCENT")
    max_positions: int = Field(default=10, env="MAX_POSITIONS")
    scan_interval_seconds: int = Field(default=30, env="SCAN_INTERVAL_SECONDS")
    min_signal_score: float = Field(default=0.65, env="MIN_SIGNAL_SCORE")
    min_volume_usd: float = Field(default=100000, env="MIN_VOLUME_USD")
    # timeframes: str = Field(
    #     default="1m,5m,15m,1h,4h,1d"
    # )
    top_coins_count: int = Field(default=200, env="TOP_COINS_COUNT")
    
    # Enhanced analysis settings
    analysis_mode: str = Field(default="moderate", env="ANALYSIS_MODE")
    min_confidence_score: float = Field(default=0.65, env="MIN_CONFIDENCE_SCORE")
    min_confluence_score: float = Field(default=0.70, env="MIN_CONFLUENCE_SCORE")
    min_risk_reward_ratio: float = Field(default=2.0, env="MIN_RISK_REWARD_RATIO")
    max_position_size: float = Field(default=0.02, env="MAX_POSITION_SIZE")
    max_volatility: float = Field(default=0.08, env="MAX_VOLATILITY")
    primary_exchange: str = Field(default="binance", env="PRIMARY_EXCHANGE")
    secondary_exchange: str = Field(default="gate", env="SECONDARY_EXCHANGE")
    market_data_source: str = Field(default="coinmarketcap", env="MARKET_DATA_SOURCE")
    
    # Trending coins settings
    trending_coins_count: int = Field(default=10, env="TRENDING_COINS_COUNT")
    include_syrup_usdt: bool = Field(default=True, env="INCLUDE_SYRUP_USDT")
    
    
    @validator('default_risk_percent', 'max_daily_loss_percent')
    def validate_percentages(cls, v):
        if not 0.1 <= v <= 100:
            raise ValueError("Percentage must be between 0.1 and 100")
        return v


class BacktestSettings(BaseSettings):
    """Backtesting configuration."""
    start_date: str = Field(default="2024-01-01", env="BACKTEST_START_DATE")
    initial_balance: float = Field(default=10000, env="BACKTEST_INITIAL_BALANCE")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    grafana_port: int = Field(default=3001, env="GRAFANA_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class Settings(BaseSettings):
    """Main application settings."""
    # Environment
    environment: str = Field(default="development", env="NODE_ENV")
    
    # Sub-configurations
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    exchange: ExchangeSettings = ExchangeSettings()
    market_data: MarketDataSettings = MarketDataSettings()
    messaging: MessagingSettings = MessagingSettings()
    email: EmailSettings = EmailSettings()
    stripe: StripeSettings = StripeSettings()
    api: APISettings = APISettings()
    trading: TradingSettings = TradingSettings()
    backtest: BacktestSettings = BacktestSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings

