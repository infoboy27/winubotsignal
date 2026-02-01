"""Comprehensive Celery worker for signal generation and alert processing."""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger

# Add packages to path
sys.path.append('/')
sys.path.append('/packages')

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select, and_, desc, create_engine

from common.config import get_settings
from common.database import Asset, OHLCV, Signal, Alert
from common.schemas import TimeFrame, SignalType, SignalDirection, AlertChannel
from packages.signals.signal_generator import SignalGenerator
from tasks.data_ingestion import DataIngestionTask
from tasks.alert_sender import AlertSenderTask
from tasks.trending_coins import TrendingCoinsAnalyzer

# Import error monitoring
sys.path.append('/packages')
from monitoring.error_monitor import error_monitor

# Initialize Celery
app = Celery('worker')

# Celery configuration
app.conf.update(
    broker_url='redis://redis:6379/0',
    result_backend='redis://redis:6379/1',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'scan-markets-six-times-daily': {
            'task': 'worker.scan_markets',
            'schedule': crontab(hour='8,12,14,16,20,0', minute=0),  # 8am, 12pm, 2pm, 4pm, 8pm, 12am
        },
        'trigger-trading-opportunities': {
            'task': 'worker.trigger_trading_check',
            'schedule': crontab(hour='8,12,14,16,20,0', minute=2),  # 2 minutes after signal generation
        },
        'ingest-data-every-5-minutes': {
            'task': 'worker.ingest_market_data',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
        'cleanup-old-signals': {
            'task': 'worker.cleanup_old_signals',
            'schedule': crontab(hour=0, minute=0),  # Daily at midnight
        },
        'analyze-trending-coins': {
            'task': 'worker.analyze_trending_coins',
            'schedule': crontab(minute='*/10'),  # Every 10 minutes
        },
    },
)

settings = get_settings()

# Create synchronous database engine for worker
sync_engine = create_engine(settings.database.sync_url, echo=False)
SessionLocal = sessionmaker(bind=sync_engine)

def get_sync_db():
    """Get synchronous database session for worker."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize components
signal_generator = SignalGenerator(min_score=settings.trading.min_signal_score)
data_ingestion = DataIngestionTask()
alert_sender = AlertSenderTask()
trending_analyzer = TrendingCoinsAnalyzer()


@app.task
def debug_task():
    """Simple test task."""
    logger.info("Hello from Celery!")
    return "Task executed"


@app.task
def trigger_trading_check():
    """Trigger trading bot to check for new opportunities after signal generation."""
    logger.info("🎯 Triggering trading opportunity check...")
    
    try:
        # This task acts as a trigger for the trading bot
        # The actual trading logic is handled by the trading bot itself
        logger.info("✅ Trading opportunity check triggered")
        return {"status": "success", "message": "Trading check triggered"}
        
    except Exception as e:
        logger.error(f"❌ Error triggering trading check: {e}")
        # Send Discord alert for trading check failure
        error_monitor.send_error_alert(
            error=e,
            context="Trading Opportunity Check Failure",
            severity="ERROR",
            additional_info={"Task": "trigger_trading_check", "Impact": "Trading bot not analyzing signals"}
        )
        return {"status": "error", "error": str(e)}


@app.task
def scan_markets():
    """Scan markets for trading signals."""
    logger.info("Starting market scan...")
    
    try:
        # Get database session
        db = next(get_sync_db())
        
        # Get active assets
        assets = db.execute(
            select(Asset).where(Asset.active == True)
        ).scalars().all()
        
        if not assets:
            logger.warning("No active assets found for scanning")
            return {"status": "no_assets", "signals_generated": 0}
        
        signals_generated = 0
        
        for asset in assets:
            try:
                # Generate signals for each timeframe
                timeframes_list = ["1m", "5m", "15m", "1h", "4h", "1d"]  # Default timeframes
                for timeframe in timeframes_list:
                    signal = generate_signal_for_asset(db, asset, timeframe)
                    if signal:
                        signals_generated += 1
                        # Send alerts for new signals
                        send_signal_alerts.delay(signal.id)
                        
            except Exception as e:
                logger.error(f"Error scanning {asset.symbol}: {e}")
                # Send Discord alert for individual asset scan errors
                error_monitor.send_error_alert(
                    error=e,
                    context=f"Market Scan - Asset: {asset.symbol}",
                    severity="ERROR"
                )
                continue
        
        logger.info(f"Market scan completed. Generated {signals_generated} signals")
        return {"status": "success", "signals_generated": signals_generated}
        
    except Exception as e:
        logger.error(f"Market scan failed: {e}")
        # Send Discord alert for critical scan failure
        error_monitor.send_error_alert(
            error=e,
            context="Market Scan - Complete Failure",
            severity="CRITICAL",
            additional_info={"Task": "scan_markets", "Impact": "No signals generated"}
        )
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@app.task
def ingest_market_data():
    """Ingest fresh market data."""
    logger.info("Starting market data ingestion...")
    
    try:
        db = next(get_sync_db())
        result = data_ingestion.ingest_ohlcv_data(db)
        
        logger.info(f"Data ingestion completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {e}")
        # Send Discord alert for data ingestion failure
        error_monitor.send_error_alert(
            error=e,
            context="Market Data Ingestion Failure",
            severity="CRITICAL",
            additional_info={"Task": "ingest_market_data", "Impact": "No fresh market data available"}
        )
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@app.task
def send_signal_alerts(signal_id: int):
    """Send alerts for a specific signal."""
    logger.info(f"Sending alerts for signal {signal_id}")
    
    try:
        db = next(get_sync_db())
        
        # Get signal
        signal = db.execute(
            select(Signal).where(Signal.id == signal_id)
        ).scalar_one_or_none()
        
        if not signal:
            logger.error(f"Signal {signal_id} not found")
            return {"status": "error", "error": "Signal not found"}
        
        # Only send alerts for MEDIUM-HIGH confidence signals (score >= 0.75)
        # Lowered from 0.80 to 0.75 to include more trading pairs (DOT, SOL, BTC, etc.)
        if signal.score < 0.75:
            logger.info(f"⏭️ Skipping alert for signal {signal_id} - Score: {signal.score:.2f} (< 75% threshold)")
            return {"status": "skipped", "reason": "score_too_low", "score": signal.score}
        
        # Send Telegram alert
        telegram_sent = alert_sender.send_telegram_alert(signal)
        
        # Send Discord alert
        discord_sent = alert_sender.send_discord_alert(signal)
        
        # Create alert records
        if telegram_sent:
            alert = Alert(
                signal_id=signal.id,
                channel=AlertChannel.TELEGRAM,
                sent_at=datetime.utcnow(),
                success=True
            )
            db.add(alert)
        
        if discord_sent:
            alert = Alert(
                signal_id=signal.id,
                channel=AlertChannel.DISCORD,
                sent_at=datetime.utcnow(),
                success=True
            )
            db.add(alert)
        
        db.commit()
        
        logger.info(f"Alerts sent for signal {signal_id}: Telegram={telegram_sent}, Discord={discord_sent}")
        return {
            "status": "success",
            "telegram_sent": telegram_sent,
            "discord_sent": discord_sent
        }
        
    except Exception as e:
        logger.error(f"Failed to send alerts for signal {signal_id}: {e}")
        # Send Discord alert for alert sending failure
        error_monitor.send_error_alert(
            error=e,
            context=f"Alert Sending Failure - Signal {signal_id}",
            severity="ERROR",
            additional_info={"Signal ID": signal_id, "Impact": "Users didn't receive signal alert"}
        )
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@app.task
def cleanup_old_signals():
    """Clean up old signals and alerts."""
    logger.info("Starting cleanup of old signals...")
    
    try:
        db = next(get_sync_db())
        
        # Delete signals older than 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        old_signals = db.execute(
            select(Signal).where(Signal.created_at < cutoff_date)
        ).scalars().all()
        
        deleted_count = 0
        for signal in old_signals:
            db.delete(signal)
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} old signals")
        return {"status": "success", "deleted_signals": deleted_count}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
            db.close()


@app.task
def analyze_trending_coins():
    """Analyze trending coins for signals."""
    logger.info("Starting trending coins analysis...")
    
    try:
        # Get database session
        db = next(get_sync_db())
        
        # Run trending coins analysis
        result = trending_analyzer.analyze_trending_coins(db)
        
        logger.info(f"Trending coins analysis completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Trending coins analysis failed: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def generate_signal_for_asset(db: Session, asset: Asset, timeframe: str) -> Optional[Signal]:
    """Generate a signal for a specific asset and timeframe."""
    try:
        # Get recent OHLCV data
        ohlcv_data = db.execute(
            select(OHLCV)
            .where(
                and_(
                    OHLCV.symbol == asset.symbol,
                    OHLCV.timeframe == timeframe
                )
            )
            .order_by(desc(OHLCV.timestamp))
            .limit(500)  # Get last 500 candles
        ).scalars().all()
        
        if len(ohlcv_data) < 200:
            logger.warning(f"Insufficient data for {asset.symbol} {timeframe}: {len(ohlcv_data)} candles")
            return None
        
        # Convert to DataFrame
        import pandas as pd
        df = pd.DataFrame([{
            'timestamp': ohlcv.timestamp,
            'open': float(ohlcv.open),
            'high': float(ohlcv.high),
            'low': float(ohlcv.low),
            'close': float(ohlcv.close),
            'volume': float(ohlcv.volume)
        } for ohlcv in reversed(ohlcv_data)])
        
        # Generate signal
        signal_data = signal_generator.generate_signal(
            symbol=asset.symbol,
            timeframe=timeframe,
            df=df
        )
        
        if not signal_data:
            return None
        
        # Check if we already have a recent signal for this asset/timeframe (within the last hour)
        recent_signal = db.execute(
            select(Signal)
            .where(
                and_(
                    Signal.symbol == asset.symbol,
                    Signal.timeframe == timeframe,
                    Signal.created_at > datetime.utcnow() - timedelta(hours=1)
                )
            )
        ).scalar_one_or_none()
        
        if recent_signal:
            logger.info(f"Recent signal already exists for {asset.symbol} {timeframe} within the last hour")
            return None
        
        # Create signal record
        signal = Signal(
            symbol=asset.symbol,
            timeframe=timeframe,
            signal_type=SignalType.ENTRY,
            direction=SignalDirection(signal_data['direction']),
            score=signal_data['score'],
            entry_price=signal_data.get('entry_price'),
            stop_loss=signal_data.get('stop_loss'),
            take_profit_1=signal_data.get('take_profit_1'),
            take_profit_2=signal_data.get('take_profit_2'),
            take_profit_3=signal_data.get('take_profit_3'),
            risk_reward_ratio=signal_data.get('risk_reward_ratio'),
            confluences=signal_data.get('confluences', {}),
            context=signal_data.get('context', {})
        )
        
        db.add(signal)
        db.commit()
        db.refresh(signal)
        
        logger.info(f"Generated signal for {asset.symbol} {timeframe}: {signal.direction} (score: {signal.score:.2f})")
        return signal
        
    except Exception as e:
        logger.error(f"Error generating signal for {asset.symbol} {timeframe}: {e}")
        return None


if __name__ == '__main__':
    app.start()