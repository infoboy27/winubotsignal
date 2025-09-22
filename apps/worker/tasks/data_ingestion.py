"""Data ingestion tasks for market data."""

import ccxt
import pandas as pd
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

sys.path.append('/packages')

from common.config import get_settings
from common.database import Asset, OHLCV
from common.schemas import TimeFrame
from common.utils import timestamp_to_datetime

settings = get_settings()


class DataIngestionTask:
    """Handle market data ingestion from various exchanges."""
    
    def __init__(self):
        self.exchanges = self._initialize_exchanges()
        self.timeframe_mapping = {
            '1m': '1m',
            '5m': '5m', 
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
    
    def _initialize_exchanges(self) -> dict:
        """Initialize exchange connections."""
        exchanges = {}
        
        try:
            # Binance
            if settings.exchange.binance_api_key and settings.exchange.binance_api_secret:
                exchanges['binance'] = ccxt.binance({
                    'apiKey': settings.exchange.binance_api_key,
                    'secret': settings.exchange.binance_api_secret,
                    'sandbox': False,
                    'rateLimit': 1200,
                    'enableRateLimit': True,
                })
            else:
                # Use public API only
                exchanges['binance'] = ccxt.binance({
                    'rateLimit': 1200,
                    'enableRateLimit': True,
                })
            
            # Gate.io
            if settings.exchange.gate_api_key and settings.exchange.gate_api_secret:
                exchanges['gate'] = ccxt.gate({
                    'apiKey': settings.exchange.gate_api_key,
                    'secret': settings.exchange.gate_api_secret,
                    'sandbox': False,
                    'rateLimit': 1000,
                    'enableRateLimit': True,
                })
            else:
                exchanges['gate'] = ccxt.gate({
                    'rateLimit': 1000,
                    'enableRateLimit': True,
                })
                
            logger.info(f"Initialized {len(exchanges)} exchanges")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchanges: {e}")
        
        return exchanges
    
    def update_asset_list(self, db: Session) -> int:
        """Update the list of available trading assets."""
        updated_count = 0
        
        for exchange_name, exchange in self.exchanges.items():
            try:
                logger.info(f"Updating assets from {exchange_name}")
                
                # Load markets
                markets = exchange.load_markets()
                
                for symbol, market in markets.items():
                    if not market.get('active', False):
                        continue
                    
                    # Focus on USDT pairs and major coins
                    if not (symbol.endswith('/USDT') or symbol.endswith('/USD')):
                        continue
                    
                    base = market['base']
                    quote = market['quote']
                    
                    # Check if asset already exists
                    existing_asset = db.execute(
                        select(Asset).where(
                            and_(Asset.symbol == symbol, Asset.exchange == exchange_name)
                        )
                    ).scalar_one_or_none()
                    
                    if existing_asset:
                        # Update existing asset
                        existing_asset.active = market.get('active', True)
                        existing_asset.name = market.get('id', symbol)
                    else:
                        # Create new asset
                        asset = Asset(
                            symbol=symbol,
                            name=market.get('id', symbol),
                            base=base,
                            quote=quote,
                            exchange=exchange_name,
                            active=market.get('active', True)
                        )
                        db.add(asset)
                        updated_count += 1
                
                db.commit()
                logger.info(f"Updated {updated_count} assets from {exchange_name}")
                
            except Exception as e:
                logger.error(f"Failed to update assets from {exchange_name}: {e}")
                db.rollback()
                continue
        
        return updated_count
    
    def ingest_ohlcv_data(
        self, 
        db: Session, 
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None
    ) -> dict:
        """Ingest OHLCV data for specified symbols and timeframes."""
        
        if timeframes is None:
            timeframes = settings.trading.timeframes
        
        # Get active assets if no symbols specified
        if not symbols:
            assets = db.execute(
                select(Asset).where(Asset.active == True).limit(settings.trading.top_coins_count)
            ).scalars().all()
            symbols = [asset.symbol for asset in assets]
        
        total_candles = 0
        errors = []
        
        for timeframe in timeframes:
            try:
                candles_ingested = self._ingest_timeframe_data(db, symbols, timeframe)
                total_candles += candles_ingested
                logger.info(f"Ingested {candles_ingested} candles for {timeframe}")
                
            except Exception as e:
                error_msg = f"Failed to ingest {timeframe} data: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "total_candles": total_candles,
            "symbols_processed": len(symbols),
            "timeframes_processed": len(timeframes),
            "errors": errors
        }
    
    def _ingest_timeframe_data(self, db: Session, symbols: List[str], timeframe: str) -> int:
        """Ingest data for a specific timeframe."""
        candles_ingested = 0
        
        # Determine how much historical data to fetch
        if timeframe in ['1m', '5m']:
            days_back = 7  # 1 week for minute data
            limit = 1000
        elif timeframe == '15m':
            days_back = 30  # 1 month
            limit = 1000
        elif timeframe == '1h':
            days_back = 90  # 3 months
            limit = 1000
        elif timeframe == '4h':
            days_back = 365  # 1 year
            limit = 1000
        else:  # 1d
            days_back = 730  # 2 years
            limit = 1000
        
        since = int((datetime.utcnow() - timedelta(days=days_back)).timestamp() * 1000)
        
        for symbol in symbols[:50]:  # Limit to prevent rate limiting
            for exchange_name, exchange in self.exchanges.items():
                try:
                    # Check if symbol exists on this exchange
                    if symbol not in exchange.markets:
                        continue
                    
                    # Get the last timestamp we have data for
                    last_candle = db.execute(
                        select(OHLCV)
                        .where(OHLCV.symbol == symbol)
                        .where(OHLCV.timeframe == timeframe)
                        .order_by(OHLCV.timestamp.desc())
                        .limit(1)
                    ).scalar_one_or_none()
                    
                    if last_candle:
                        # Fetch only new data
                        since = int(last_candle.timestamp.timestamp() * 1000)
                    
                    # Fetch OHLCV data
                    ohlcv_data = exchange.fetch_ohlcv(
                        symbol, 
                        timeframe, 
                        since=since, 
                        limit=limit
                    )
                    
                    if not ohlcv_data:
                        continue
                    
                    # Convert and save data
                    for candle_data in ohlcv_data:
                        timestamp = timestamp_to_datetime(candle_data[0])
                        
                        # Check if candle already exists
                        existing = db.execute(
                            select(OHLCV).where(
                                and_(
                                    OHLCV.symbol == symbol,
                                    OHLCV.timeframe == timeframe,
                                    OHLCV.timestamp == timestamp
                                )
                            )
                        ).scalar_one_or_none()
                        
                        if existing:
                            # Update existing candle
                            existing.open = candle_data[1]
                            existing.high = candle_data[2]
                            existing.low = candle_data[3]
                            existing.close = candle_data[4]
                            existing.volume = candle_data[5]
                        else:
                            # Create new candle
                            candle = OHLCV(
                                timestamp=timestamp,
                                symbol=symbol,
                                timeframe=timeframe,
                                open=candle_data[1],
                                high=candle_data[2],
                                low=candle_data[3],
                                close=candle_data[4],
                                volume=candle_data[5]
                            )
                            db.add(candle)
                            candles_ingested += 1
                    
                    db.commit()
                    
                    # Rate limiting
                    if exchange.rateLimit:
                        import time
                        time.sleep(exchange.rateLimit / 1000)
                    
                    # Only use first exchange that has the symbol
                    break
                    
                except Exception as e:
                    logger.error(f"Failed to fetch {symbol} {timeframe} from {exchange_name}: {e}")
                    db.rollback()
                    continue
        
        return candles_ingested
    
    def fetch_market_cap_data(self, db: Session) -> int:
        """Fetch market cap data from CoinGecko or CoinMarketCap."""
        try:
            import requests
            
            # Use CoinGecko API (free tier)
            url = f"{settings.market_data.coingecko_api_base}/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 250,
                'page': 1
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            updated_count = 0
            
            for coin in data:
                symbol = f"{coin['symbol'].upper()}/USDT"
                
                # Find matching asset
                asset = db.execute(
                    select(Asset).where(Asset.symbol == symbol)
                ).scalar_one_or_none()
                
                if asset:
                    asset.market_cap_rank = coin.get('market_cap_rank')
                    asset.price_usd = coin.get('current_price')
                    asset.volume_24h_usd = coin.get('total_volume')
                    updated_count += 1
            
            db.commit()
            logger.info(f"Updated market cap data for {updated_count} assets")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to fetch market cap data: {e}")
            db.rollback()
            return 0

