#!/usr/bin/env python3
"""Populate historical data for all trading pairs."""

import sys
import os
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from loguru import logger

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings

settings = get_settings()

async def fetch_binance_historical_data(symbol: str, timeframe: str, limit: int = 1000):
    """Fetch historical data from Binance API."""
    try:
        # Convert symbol format
        binance_symbol = symbol.replace('/', '')
        
        # Map timeframe
        tf_map = {
            '1m': '1m', '5m': '5m', '15m': '15m',
            '1h': '1h', '4h': '4h', '1d': '1d'
        }
        binance_tf = tf_map.get(timeframe, '1h')
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': binance_symbol,
                'interval': binance_tf,
                'limit': limit
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                    
                    # Convert types
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                else:
                    logger.error(f"Failed to fetch {symbol} from Binance: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching {symbol} from Binance: {e}")
        return None

async def populate_all_historical_data():
    """Populate historical data for all trading pairs."""
    
    # Create database connection
    engine = create_engine(settings.database.sync_url)
    
    # Get all active assets
    with engine.connect() as conn:
        result = conn.execute(text("SELECT symbol FROM assets WHERE active = true"))
        symbols = [row[0] for row in result.fetchall()]
    
    timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    # Timeframe mapping to database enum values
    timeframe_mapping = {
        '1m': 'ONE_MINUTE',
        '5m': 'FIVE_MINUTES',
        '15m': 'FIFTEEN_MINUTES',
        '1h': 'ONE_HOUR',
        '4h': 'FOUR_HOURS',
        '1d': 'ONE_DAY'
    }
    
    for symbol in symbols:
        logger.info(f"Processing {symbol}...")
        
        for timeframe in timeframes:
            logger.info(f"Fetching {symbol} {timeframe} data...")
            
            # Fetch data from Binance
            df = await fetch_binance_historical_data(symbol, timeframe, 1000)
            
            if df is not None and len(df) > 0:
                logger.info(f"Successfully fetched {len(df)} candles for {symbol} {timeframe}")
                
                # Insert data into database
                with engine.connect() as conn:
                    for _, row in df.iterrows():
                        try:
                            # Check if candle already exists
                            result = conn.execute(text("""
                                SELECT id FROM ohlcv 
                                WHERE symbol = :symbol 
                                AND timeframe = :timeframe 
                                AND timestamp = :timestamp
                            """), {
                                'symbol': symbol,
                                'timeframe': timeframe_mapping[timeframe],
                                'timestamp': row['timestamp']
                            }).fetchone()
                            
                            if not result:
                                # Insert new candle
                                conn.execute(text("""
                                    INSERT INTO ohlcv (timestamp, symbol, timeframe, open, high, low, close, volume)
                                    VALUES (:timestamp, :symbol, :timeframe, :open, :high, :low, :close, :volume)
                                """), {
                                    'timestamp': row['timestamp'],
                                    'symbol': symbol,
                                    'timeframe': timeframe_mapping[timeframe],
                                    'open': float(row['open']),
                                    'high': float(row['high']),
                                    'low': float(row['low']),
                                    'close': float(row['close']),
                                    'volume': float(row['volume'])
                                })
                                conn.commit()
                        except Exception as e:
                            logger.error(f"Error inserting candle for {symbol} {timeframe}: {e}")
                            conn.rollback()
                            continue
            else:
                logger.warning(f"No data found for {symbol} {timeframe}")
    
    logger.info("Historical data population completed!")

if __name__ == "__main__":
    asyncio.run(populate_all_historical_data())
