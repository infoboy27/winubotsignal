"""Configuration management for Million Trader."""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    host: str = Field(default="postgres", env="POSTGRES_HOST")
    port: int = Field(default=5432, env="POSTGRES_PORT")
    database: str = Field(default="million", env="POSTGRES_DB")
    username: str = Field(default="million", env="POSTGRES_USER")
    password: str = Field(default="changeme", env="POSTGRES_PASSWORD")
    
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
    url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
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
    timeframes: List[str] = Field(
        default=["1m", "5m", "15m", "1h", "4h", "1d"], 
        env="TIMEFRAMES"
    )
    top_coins_count: int = Field(default=200, env="TOP_COINS_COUNT")
    
    @validator('timeframes', pre=True)
    def validate_timeframes(cls, v):
        if isinstance(v, str):
            # Handle both comma-separated and space-separated values
            if ',' in v:
                return [tf.strip() for tf in v.split(',') if tf.strip()]
            else:
                return [tf.strip() for tf in v.split() if tf.strip()]
        elif isinstance(v, list):
            return v
        else:
            return ["1m", "5m", "15m", "1h", "4h", "1d"]  # Default fallback
    
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

