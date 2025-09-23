"""Celery worker for Million Trader."""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import ccxt
import pandas as pd
import redis
from celery import Celery
from celery.schedules import crontab
from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.database import Asset, OHLCV, Signal, Alert
from common.logging import setup_logging
from common.schemas import TimeFrame, SignalDirection, AlertChannel
from signals import SignalGenerator
from tasks.data_ingestion import DataIngestionTask
from tasks.market_scanner import MarketScannerTask
from tasks.alert_sender import AlertSenderTask

# Setup logging
setup_logging()
logger = logger.bind(service="worker")

settings = get_settings()

# Initialize Celery
app = Celery('million-trader-worker')

# Celery configuration
app.conf.update(
    broker_url=settings.redis.broker_url,
    result_backend=settings.redis.result_backend,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'worker.ingest_market_data': {'queue': 'data_ingestion'},
        'worker.scan_market': {'queue': 'market_scanning'},
        'worker.send_alert': {'queue': 'alerts'},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
)

# Database setup
engine = create_engine(settings.database.sync_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# Redis setup
redis_client = redis.from_url(settings.redis.url, decode_responses=True)

# Initialize task classes
data_ingestion = DataIngestionTask()
market_scanner = MarketScannerTask()
alert_sender = AlertSenderTask()

# Signal generator
signal_generator = SignalGenerator(min_score=settings.trading.min_signal_score)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_market_data(self, symbols: List[str], timeframes: List[str]):
    """Ingest OHLCV market data for specified symbols and timeframes."""
    try:
        logger.info(f"Starting market data ingestion for {len(symbols)} symbols")
        
        with SessionLocal() as db:
            result = data_ingestion.ingest_ohlcv_data(db, symbols, timeframes)
            
        logger.info(f"Market data ingestion completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Market data ingestion failed: {e}")
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying in {self.default_retry_delay} seconds...")
            raise self.retry(countdown=self.default_retry_delay)
        raise


@app.task(bind=True, max_retries=2, default_retry_delay=30)
def scan_market(self, timeframes: Optional[List[str]] = None):
    """Scan market for trading signals."""
    try:
        if timeframes is None:
            timeframes = settings.trading.timeframes
            
        logger.info(f"Starting market scan for timeframes: {timeframes}")
        
        with SessionLocal() as db:
            # Get active assets
            assets = db.execute(
                select(Asset).where(Asset.active == True).limit(settings.trading.top_coins_count)
            ).scalars().all()
            
            total_signals = 0
            
            for asset in assets:
                try:
                    for timeframe in timeframes:
                        # Get recent OHLCV data
                        ohlcv_data = db.execute(
                            select(OHLCV)
                            .where(OHLCV.symbol == asset.symbol)
                            .where(OHLCV.timeframe == timeframe)
                            .order_by(OHLCV.timestamp.desc())
                            .limit(500)
                        ).scalars().all()
                        
                        if len(ohlcv_data) < 200:
                            continue
                        
                        # Convert to DataFrame
                        df = pd.DataFrame([
                            {
                                'timestamp': candle.timestamp,
                                'open': float(candle.open),
                                'high': float(candle.high),
                                'low': float(candle.low),
                                'close': float(candle.close),
                                'volume': float(candle.volume)
                            }
                            for candle in reversed(ohlcv_data)
                        ])
                        
                        df.set_index('timestamp', inplace=True)
                        
                        # Generate signal
                        signal_data = signal_generator.generate_signal(
                            symbol=asset.symbol,
                            timeframe=timeframe,
                            df=df
                        )
                        
                        if signal_data:
                            # Validate signal
                            if signal_generator.validate_signal(signal_data):
                                # Save signal to database
                                signal = Signal(
                                    symbol=signal_data['symbol'],
                                    timeframe=signal_data['timeframe'],
                                    signal_type=signal_data['signal_type'],
                                    direction=signal_data['direction'],
                                    score=signal_data['score'],
                                    entry_price=signal_data['entry_price'],
                                    stop_loss=signal_data['stop_loss'],
                                    take_profit_1=signal_data['take_profit_1'],
                                    take_profit_2=signal_data['take_profit_2'],
                                    take_profit_3=signal_data['take_profit_3'],
                                    risk_reward_ratio=signal_data['risk_reward_ratio'],
                                    confluences=signal_data['confluences'],
                                    context=signal_data['context']
                                )
                                
                                db.add(signal)
                                db.commit()
                                db.refresh(signal)
                                
                                total_signals += 1
                                
                                # Queue alert tasks
                                send_telegram_alert.delay(signal.id)
                                send_discord_alert.delay(signal.id)
                                
                                # Publish to Redis for real-time updates
                                redis_client.publish('signals', json.dumps({
                                    'id': signal.id,
                                    'symbol': signal.symbol,
                                    'direction': signal.direction,
                                    'score': signal.score,
                                    'timeframe': signal.timeframe,
                                    'timestamp': signal.created_at.isoformat()
                                }))
                                
                                logger.info(
                                    f"Generated signal: {signal.symbol} {signal.direction} "
                                    f"({signal.timeframe}) - Score: {signal.score}"
                                )
                        
                except Exception as e:
                    logger.error(f"Error scanning {asset.symbol}: {e}")
                    continue
            
            logger.info(f"Market scan completed: {total_signals} signals generated")
            return {"signals_generated": total_signals, "assets_scanned": len(assets)}
        
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        raise


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_telegram_alert(self, signal_id: int):
    """Send Telegram alert for a signal."""
    try:
        with SessionLocal() as db:
            signal = db.get(Signal, signal_id)
            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return
            
            success = alert_sender.send_telegram_alert(signal)
            
            # Save alert record
            alert = Alert(
                signal_id=signal_id,
                channel=AlertChannel.TELEGRAM,
                success=success,
                sent_at=datetime.utcnow() if success else None
            )
            
            db.add(alert)
            db.commit()
            
            return success
        
    except Exception as e:
        logger.error(f"Telegram alert failed for signal {signal_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        return False


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_discord_alert(self, signal_id: int):
    """Send Discord alert for a signal."""
    try:
        with SessionLocal() as db:
            signal = db.get(Signal, signal_id)
            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return
            
            success = alert_sender.send_discord_alert(signal)
            
            # Save alert record
            alert = Alert(
                signal_id=signal_id,
                channel=AlertChannel.DISCORD,
                success=success,
                sent_at=datetime.utcnow() if success else None
            )
            
            db.add(alert)
            db.commit()
            
            return success
        
    except Exception as e:
        logger.error(f"Discord alert failed for signal {signal_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=self.default_retry_delay)
        return False


@app.task
def update_asset_list():
    """Update the list of available trading assets."""
    try:
        logger.info("Updating asset list...")
        
        with SessionLocal() as db:
            updated_count = data_ingestion.update_asset_list(db)
            
        logger.info(f"Asset list updated: {updated_count} assets")
        return updated_count
        
    except Exception as e:
        logger.error(f"Asset list update failed: {e}")
        raise


@app.task
def cleanup_old_data():
    """Clean up old data to manage database size."""
    try:
        logger.info("Starting data cleanup...")
        
        with SessionLocal() as db:
            # Delete OHLCV data older than 6 months for minute timeframes
            cutoff_date = datetime.utcnow() - timedelta(days=180)
            
            deleted_count = db.execute(
                """
                DELETE FROM ohlcv 
                WHERE timestamp < :cutoff_date 
                AND timeframe IN ('1m', '5m')
                """,
                {"cutoff_date": cutoff_date}
            ).rowcount
            
            # Delete old alerts (keep for 30 days)
            alert_cutoff = datetime.utcnow() - timedelta(days=30)
            deleted_alerts = db.execute(
                """
                DELETE FROM alerts 
                WHERE created_at < :cutoff_date
                """,
                {"cutoff_date": alert_cutoff}
            ).rowcount
            
            db.commit()
            
        logger.info(f"Cleanup completed: {deleted_count} OHLCV records, {deleted_alerts} alerts deleted")
        return {"ohlcv_deleted": deleted_count, "alerts_deleted": deleted_alerts}
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        raise


# Periodic tasks
app.conf.beat_schedule = {
    # Market data ingestion every 1 minute
    'ingest-market-data-1m': {
        'task': 'worker.ingest_market_data',
        'schedule': crontab(minute='*'),
        'args': ([], ['1m']),
    },
    
    # Market data ingestion every 5 minutes
    'ingest-market-data-5m': {
        'task': 'worker.ingest_market_data',
        'schedule': crontab(minute='*/5'),
        'args': ([], ['5m']),
    },
    
    # Market data ingestion every 15 minutes
    'ingest-market-data-15m': {
        'task': 'worker.ingest_market_data',
        'schedule': crontab(minute='*/15'),
        'args': ([], ['15m']),
    },
    
    # Market data ingestion every hour
    'ingest-market-data-1h': {
        'task': 'worker.ingest_market_data',
        'schedule': crontab(minute=0),
        'args': ([], ['1h']),
    },
    
    # Market data ingestion every 4 hours
    'ingest-market-data-4h': {
        'task': 'worker.ingest_market_data',
        'schedule': crontab(minute=0, hour='*/4'),
        'args': ([], ['4h']),
    },
    
    # Market data ingestion daily
    'ingest-market-data-1d': {
        'task': 'worker.ingest_market_data',
        'schedule': crontab(minute=0, hour=0),
        'args': ([], ['1d']),
    },
    
    # Market scanning every 30 seconds (configurable)
    'scan-market': {
        'task': 'worker.scan_market',
        'schedule': settings.trading.scan_interval_seconds,
        'args': (),
    },
    
    # Update asset list daily
    'update-asset-list': {
        'task': 'worker.update_asset_list',
        'schedule': crontab(minute=0, hour=6),  # 6 AM UTC
    },
    
    # Cleanup old data weekly
    'cleanup-old-data': {
        'task': 'worker.cleanup_old_data',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2 AM
    },
}


if __name__ == '__main__':
    app.start()




