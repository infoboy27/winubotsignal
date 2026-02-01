#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - Populate Real Market Data
==============================================

This script fetches real market data from public APIs and populates the database.
"""

import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
import json

class RealDataPopulator:
    """Populate database with real market data."""
    
    def __init__(self):
        self.db_pool = None
        self.symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'DOT/USDT',
            'XRP/USDT', 'AVAX/USDT', 'BNB/USDT', 'ADA/USDT', 'MATIC/USDT'
        ]
        
    async def connect_db(self):
        """Connect to database."""
        self.db_pool = await asyncpg.create_pool(
            host='localhost',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb',
            min_size=1,
            max_size=10
        )
    
    def fetch_binance_data(self, symbol: str, start_time: int, end_time: int) -> list:
        """Fetch real OHLCV data from Binance API."""
        # Convert symbol format (BTC/USDT -> BTCUSDT)
        binance_symbol = symbol.replace('/', '')
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': binance_symbol,
            'interval': '1h',
            'startTime': start_time,
            'endTime': end_time,
            'limit': 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            ohlcv_data = []
            for candle in data:
                ohlcv_data.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            return ohlcv_data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return []
    
    def generate_realistic_signals(self, ohlcv_data: list, symbol: str) -> list:
        """Generate realistic signals based on price action."""
        signals = []
        
        if len(ohlcv_data) < 50:
            return signals
        
        df = pd.DataFrame(ohlcv_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Calculate technical indicators
        df['rsi_14'] = self.calculate_rsi(df['close'], 14)
        df['rsi_21'] = self.calculate_rsi(df['close'], 21)
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # Generate signals based on technical analysis
        for i in range(50, len(df)):
            current = df.iloc[i]
            
            # RSI signals
            rsi_signal = 0
            if current['rsi_14'] < 30 and current['rsi_21'] < 35:
                rsi_signal = 1  # Oversold - BUY
            elif current['rsi_14'] > 70 and current['rsi_21'] > 65:
                rsi_signal = -1  # Overbought - SELL
            
            # EMA trend signals
            ema_signal = 0
            if current['ema_12'] > current['ema_26']:
                ema_signal = 1  # Uptrend
            elif current['ema_12'] < current['ema_26']:
                ema_signal = -1  # Downtrend
            
            # Price momentum
            if i > 0:
                prev_close = df.iloc[i-1]['close']
                price_change = (current['close'] - prev_close) / prev_close
                momentum_signal = 1 if price_change > 0.01 else -1 if price_change < -0.01 else 0
            else:
                momentum_signal = 0
            
            # Combine signals
            total_signal = rsi_signal + ema_signal + momentum_signal
            
            # Generate signal if strong enough
            if abs(total_signal) >= 2:  # Strong signal
                direction = 'LONG' if total_signal > 0 else 'SHORT'
                score = min(0.95, 0.6 + abs(total_signal) * 0.1)
                
                # Calculate TP/SL levels
                if direction == 'LONG':
                    take_profit = current['close'] * 1.02  # 2% TP
                    stop_loss = current['close'] * 0.98   # 2% SL
                else:
                    take_profit = current['close'] * 0.98  # 2% TP
                    stop_loss = current['close'] * 1.02   # 2% SL
                
                signals.append({
                    'symbol': symbol,
                    'signal_type': 'ENTRY',
                    'direction': direction,
                    'entry_price': current['close'],
                    'take_profit_1': take_profit,
                    'stop_loss': stop_loss,
                    'score': score,
                    'is_active': True,
                    'created_at': current.name,
                    'realized_pnl': 0.0
                })
        
        return signals
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    async def populate_ohlcv_data(self):
        """Populate OHLCV data for all symbols."""
        print("📊 Fetching real market data...")
        
        # Get data for the last 6 months
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=180)).timestamp() * 1000)
        
        total_records = 0
        
        for symbol in self.symbols:
            print(f"📈 Fetching data for {symbol}...")
            
            # Fetch data in chunks to avoid API limits
            current_start = start_time
            all_data = []
            
            while current_start < end_time:
                current_end = min(current_start + 30 * 24 * 60 * 60 * 1000, end_time)  # 30 days
                
                data = self.fetch_binance_data(symbol, current_start, current_end)
                all_data.extend(data)
                
                current_start = current_end + 1
                time.sleep(0.1)  # Rate limiting
            
            if all_data:
                # Insert into database
                async with self.db_pool.acquire() as conn:
                    for record in all_data:
                        await conn.execute("""
                            INSERT INTO ohlcv (symbol, timeframe, timestamp, open, high, low, close, volume)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """, symbol, 'ONE_HOUR', record['timestamp'], record['open'], 
                        record['high'], record['low'], record['close'], record['volume'])
                
                total_records += len(all_data)
                print(f"✅ Inserted {len(all_data)} records for {symbol}")
            else:
                print(f"❌ No data fetched for {symbol}")
        
        print(f"📊 Total OHLCV records: {total_records}")
    
    async def populate_signals_data(self):
        """Populate signals data based on OHLCV data."""
        print("🎯 Generating realistic signals...")
        
        total_signals = 0
        
        for symbol in self.symbols:
            print(f"📈 Processing signals for {symbol}...")
            
            # Get OHLCV data for this symbol
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT timestamp, open, high, low, close, volume
                    FROM ohlcv 
                    WHERE symbol = $1 
                    ORDER BY timestamp
                """, symbol)
            
            if not rows:
                print(f"❌ No OHLCV data found for {symbol}")
                continue
            
            # Convert to list of dicts
            ohlcv_data = []
            for row in rows:
                ohlcv_data.append({
                    'timestamp': row['timestamp'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                })
            
            # Generate signals
            signals = self.generate_realistic_signals(ohlcv_data, symbol)
            
            if signals:
                # Insert signals into database
                async with self.db_pool.acquire() as conn:
                    for signal in signals:
                        await conn.execute("""
                            INSERT INTO signals (symbol, timeframe, signal_type, direction, entry_price, take_profit_1, stop_loss, score, is_active, created_at, realized_pnl)
                            VALUES ($1, 'ONE_HOUR', $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """, signal['symbol'], signal['signal_type'], signal['direction'],
                        signal['entry_price'], signal['take_profit_1'], signal['stop_loss'],
                        signal['score'], signal['is_active'], signal['created_at'], signal['realized_pnl'])
                
                total_signals += len(signals)
                print(f"✅ Generated {len(signals)} signals for {symbol}")
            else:
                print(f"❌ No signals generated for {symbol}")
        
        print(f"🎯 Total signals: {total_signals}")
    
    async def run(self):
        """Run the data population process."""
        print("🚀 Starting real data population...")
        
        await self.connect_db()
        
        # Populate OHLCV data
        await self.populate_ohlcv_data()
        
        # Populate signals data
        await self.populate_signals_data()
        
        # Show final statistics
        async with self.db_pool.acquire() as conn:
            ohlcv_count = await conn.fetchval("SELECT COUNT(*) FROM ohlcv")
            signals_count = await conn.fetchval("SELECT COUNT(*) FROM signals")
            
            print("\n" + "=" * 60)
            print("🎉 REAL DATA POPULATION COMPLETE!")
            print("=" * 60)
            print(f"📊 OHLCV Records: {ohlcv_count:,}")
            print(f"🎯 Signals: {signals_count:,}")
            print(f"📈 Symbols: {len(self.symbols)}")
            print("=" * 60)
        
        await self.db_pool.close()

async def main():
    """Run the data population."""
    populator = RealDataPopulator()
    await populator.run()

if __name__ == "__main__":
    asyncio.run(main())
