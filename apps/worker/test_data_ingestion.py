#!/usr/bin/env python3
"""
Simple test script to fetch real market data and store it in the database.
This bypasses the complex data ingestion logic to get real data flowing.
"""

import sys
import os
sys.path.append('/app')
sys.path.append('/packages')

import ccxt
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from common.config import get_settings

def get_db_connection():
    """Get database connection."""
    settings = get_settings()
    engine = create_engine(settings.database.sync_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def fetch_and_store_data():
    """Fetch real market data and store it in the database."""
    print("Starting data ingestion test...")
    
    # Initialize exchange
    exchange = ccxt.binance({
        'rateLimit': 1200,
        'enableRateLimit': True,
    })
    
    # Get database connection
    db = get_db_connection()
    
    try:
        # Test symbols - 10 popular trading pairs
        symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'DOT/USDT',
            'BNB/USDT', 'XRP/USDT', 'DOGE/USDT', 'MATIC/USDT', 'AVAX/USDT'
        ]
        timeframe_mapping = {
            'ONE_MINUTE': '1m',
            'FIVE_MINUTES': '5m',
            'FIFTEEN_MINUTES': '15m',
            'ONE_HOUR': '1h',
            'FOUR_HOURS': '4h', 
            'ONE_DAY': '1d'
        }
        
        total_candles = 0
        
        for symbol in symbols:
            print(f"Processing {symbol}...")
            
            for db_timeframe, api_timeframe in timeframe_mapping.items():
                try:
                    # Fetch data
                    ohlcv_data = exchange.fetch_ohlcv(symbol, api_timeframe, limit=100)
                    
                    if not ohlcv_data:
                        print(f"  No data for {db_timeframe}")
                        continue
                    
                    print(f"  Fetched {len(ohlcv_data)} candles for {db_timeframe}")
                    
                    # Store data
                    for candle_data in ohlcv_data:
                        timestamp = datetime.fromtimestamp(candle_data[0] / 1000)
                        
                        # Insert into database
                        db.execute(text("""
                            INSERT INTO ohlcv (timestamp, symbol, timeframe, open, high, low, close, volume)
                            VALUES (:timestamp, :symbol, :timeframe, :open, :high, :low, :close, :volume)
                        """), {
                            'timestamp': timestamp,
                            'symbol': symbol,
                            'timeframe': db_timeframe,
                            'open': candle_data[1],
                            'high': candle_data[2],
                            'low': candle_data[3],
                            'close': candle_data[4],
                            'volume': candle_data[5]
                        })
                        
                        total_candles += 1
                    
                    db.commit()
                    print(f"  Stored {len(ohlcv_data)} candles for {db_timeframe}")
                    
                except Exception as e:
                    print(f"  Error fetching {symbol} {db_timeframe}: {e}")
                    db.rollback()
                    continue
        
        print(f"Data ingestion completed! Total candles: {total_candles}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fetch_and_store_data()
