#!/usr/bin/env python3
"""Fix data ingestion for SYRUP/USDT and POKT/USDT."""

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
from common.database import OHLCV

settings = get_settings()

async def fetch_binance_data(symbol: str, timeframe: str, limit: int = 1000):
    """Fetch data from Binance API."""
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

async def fetch_gate_data(symbol: str, timeframe: str, limit: int = 1000):
    """Fetch data from Gate.io API."""
    try:
        # Convert symbol format
        gate_symbol = symbol.replace('/', '_')
        
        # Map timeframe
        tf_map = {
            '1m': '1m', '5m': '5m', '15m': '15m',
            '1h': '1h', '4h': '4h', '1d': '1d'
        }
        gate_tf = tf_map.get(timeframe, '1h')
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': gate_symbol,
                'interval': gate_tf,
                'limit': limit
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data:
                        return None
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'volume', 'close', 'high', 'low', 'open'
                    ])
                    
                    # Convert types
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                else:
                    logger.error(f"Failed to fetch {symbol} from Gate.io: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching {symbol} from Gate.io: {e}")
        return None

async def fetch_coingecko_data(symbol: str, days: int = 30):
    """Fetch data from CoinGecko API."""
    try:
        # Extract base symbol
        base_symbol = symbol.split('/')[0].lower()
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.coingecko.com/api/v3/coins/{base_symbol}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'hourly' if days <= 30 else 'daily'
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'prices' in data:
                        # Convert to DataFrame
                        df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        
                        # Create OHLCV data (simplified)
                        df['open'] = df['price']
                        df['high'] = df['price']
                        df['low'] = df['price']
                        df['close'] = df['price']
                        df['volume'] = 0  # Volume not available from CoinGecko
                        
                        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                    else:
                        return None
                else:
                    logger.error(f"Failed to fetch {symbol} from CoinGecko: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching {symbol} from CoinGecko: {e}")
        return None

async def populate_missing_data():
    """Populate missing data for SYRUP/USDT and POKT/USDT."""
    
    # Create database connection
    engine = create_engine(settings.database.sync_url)
    
    symbols = ['SYRUP/USDT']  # Focus on SYRUP first, POKT has no data sources
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
            
            # Try different data sources
            df = None
            
            # Try Binance first
            if not df:
                df = await fetch_binance_data(symbol, timeframe, 1000)
            
            # Try Gate.io if Binance failed
            if df is None or len(df) == 0:
                df = await fetch_gate_data(symbol, timeframe, 1000)
            
            # Try CoinGecko as last resort
            if df is None or len(df) == 0:
                days = 30 if timeframe in ['1m', '5m', '15m'] else 90
                df = await fetch_coingecko_data(symbol, days)
            
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
    
    logger.info("Data population completed!")

if __name__ == "__main__":
    asyncio.run(populate_missing_data())
