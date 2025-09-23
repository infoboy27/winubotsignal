"""Logging configuration for Million Trader."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    json_logs: bool = False
) -> None:
    """Configure application logging."""
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Determine log level
    if log_level is None:
        log_level = settings.monitoring.log_level
    
    # Console handler
    if json_logs or settings.is_production:
        # Structured logging for production
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=log_level,
            serialize=True
        )
    else:
        # Pretty logging for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=log_level,
            rotation="10 MB",
            retention="30 days",
            compression="gz"
        )
    
    # Add context to all logs
    logger.configure(
        extra={
            "service": "million-trader",
            "version": "1.0.0",
            "environment": settings.environment
        }
    )
    
    logger.info(f"Logging configured with level: {log_level}")


def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logger.bind(module=name)




