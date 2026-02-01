"""
Direct API data ingestion to replace problematic CCXT library.
"""

import sys
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.database import Asset, OHLCV
from common.schemas import TimeFrame
from common.utils import timestamp_to_datetime

settings = get_settings()


class DirectDataIngestion:
    """Direct API data ingestion using requests instead of CCXT."""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.rate_limit_delay = 0.1  # 100ms between requests
        
    def fetch_klines(self, symbol: str, interval: str, limit: int = 1000) -> Optional[List]:
        """Fetch klines data directly from Binance API."""
        try:
            # Convert symbol format (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace('/', '')
            
            url = f"{self.base_url}/klines"
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return None
                
            # Convert to our format: [timestamp, open, high, low, close, volume]
            klines = []
            for kline in data:
                klines.append([
                    int(kline[0]),      # timestamp
                    float(kline[1]),   # open
                    float(kline[2]),   # high
                    float(kline[3]),   # low
                    float(kline[4]),   # close
                    float(kline[5])    # volume
                ])
            
            return klines
            
        except Exception as e:
            print(f"❌ Error fetching {symbol} {interval}: {e}")
            return None
    
    def ingest_symbol_data(self, db: Session, symbol: str, timeframes: List[str]) -> int:
        """Ingest data for a specific symbol across multiple timeframes."""
        total_candles = 0
        
        for timeframe in timeframes:
            try:
                print(f"📊 Fetching {symbol} {timeframe}...")
                
                # Map timeframe to Binance format
                interval_map = {
                    '1m': '1m',
                    '5m': '5m', 
                    '15m': '15m',
                    '1h': '1h',
                    '4h': '4h',
                    '1d': '1d'
                }
                
                interval = interval_map.get(timeframe, timeframe)
                
                # Fetch data
                klines = self.fetch_klines(symbol, interval, limit=1000)
                
                if not klines:
                    print(f"⚠️ No data for {symbol} {timeframe}")
                    continue
                
                # Save to database
                candles_saved = 0
                for kline in klines:
                    timestamp = timestamp_to_datetime(kline[0])
                    
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
                        continue
                    
                    # Create new candle
                    candle = OHLCV(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,
                        open=kline[1],
                        high=kline[2],
                        low=kline[3],
                        close=kline[4],
                        volume=kline[5]
                    )
                    
                    db.add(candle)
                    candles_saved += 1
                
                db.commit()
                total_candles += candles_saved
                print(f"✅ Saved {candles_saved} candles for {symbol} {timeframe}")
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"❌ Error processing {symbol} {timeframe}: {e}")
                db.rollback()
                continue
        
        return total_candles
    
    def ingest_all_data(self, db: Session) -> Dict:
        """Ingest data for all symbols and timeframes."""
        try:
            print("🚀 Starting direct API data ingestion...")
            
            # Get all assets
            assets = db.execute(select(Asset)).scalars().all()
            
            if not assets:
                print("⚠️ No assets found in database")
                return {"status": "error", "message": "No assets found"}
            
            symbols = [asset.symbol for asset in assets]
            timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
            
            print(f"📊 Processing {len(symbols)} symbols: {symbols}")
            print(f"⏰ Timeframes: {timeframes}")
            
            total_candles = 0
            
            for symbol in symbols:
                candles = self.ingest_symbol_data(db, symbol, timeframes)
                total_candles += candles
                print(f"📈 {symbol}: {candles} candles")
            
            print(f"🎉 Data ingestion completed: {total_candles} total candles")
            
            return {
                "status": "success",
                "total_candles": total_candles,
                "symbols_processed": len(symbols),
                "timeframes_processed": len(timeframes)
            }
            
        except Exception as e:
            print(f"❌ Data ingestion failed: {e}")
            return {"status": "error", "error": str(e)}


def test_direct_ingestion():
    """Test the direct ingestion system."""
    print("🧪 Testing direct API ingestion...")
    
    ingestion = DirectDataIngestion()
    
    # Test with a single symbol
    test_symbol = "BTC/USDT"
    test_timeframes = ['1h', '4h', '1d']
    
    print(f"📊 Testing {test_symbol} with {test_timeframes}")
    
    for timeframe in test_timeframes:
        interval_map = {
            '1h': '1h',
            '4h': '4h', 
            '1d': '1d'
        }
        interval = interval_map.get(timeframe, timeframe)
        
        klines = ingestion.fetch_klines(test_symbol, interval, limit=10)
        if klines:
            print(f"✅ {test_symbol} {timeframe}: {len(klines)} candles")
        else:
            print(f"❌ {test_symbol} {timeframe}: Failed")


if __name__ == "__main__":
    test_direct_ingestion()
