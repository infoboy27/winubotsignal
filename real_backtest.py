#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - REAL Backtest System
========================================

This script runs a REAL backtest using your actual trading strategy
and historical OHLCV data from your database.
"""

import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import sys
import os

# Add packages to path
sys.path.append('/home/ubuntu/winubotsignal/packages')

from common.config import get_settings
from common.database import Asset, Signal, OHLCV
from packages.signals.modern_signal import ModernSignal, ModernSignalGenerator
from packages.signals.multi_source_analyzer import MultiSourceAnalyzer

class RealBacktest:
    """Real backtest using actual trading strategy and historical data."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_pool = None
        self.signal_generator = ModernSignalGenerator()
        self.analyzer = MultiSourceAnalyzer(
            binance_api_key=self.settings.exchange.binance_api_key,
            binance_secret=self.settings.exchange.binance_api_secret,
            gate_api_key=self.settings.exchange.gate_api_key,
            gate_secret=self.settings.exchange.gate_api_secret,
            cmc_api_key=self.settings.market_data.cmc_api_key
        )
        
        # Backtest parameters
        self.initial_balance = 10000.0
        self.risk_percent = 2.0
        self.max_positions = 5
        self.min_score = 0.7
        
        # Results tracking
        self.trades = []
        self.balance = self.initial_balance
        self.positions = {}
        self.equity_curve = []
        
    async def connect_db(self):
        """Connect to database."""
        self.db_pool = await asyncpg.create_pool(
            host=self.settings.database.host,
            port=self.settings.database.port,
            user=self.settings.database.user,
            password=self.settings.database.password,
            database=self.settings.database.name,
            min_size=1,
            max_size=10
        )
    
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol."""
        async with self.db_pool.acquire() as conn:
            query = """
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv 
            WHERE symbol = $1 
            AND timestamp BETWEEN $2 AND $3
            ORDER BY timestamp
            """
            rows = await conn.fetch(query, symbol, start_date, end_date)
            
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the dataframe."""
        if len(df) < 50:  # Need enough data for indicators
            return df
            
        # RSI
        df['rsi_14'] = self.calculate_rsi(df['close'], 14)
        df['rsi_21'] = self.calculate_rsi(df['close'], 21)
        
        # MACD
        macd_data = self.calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # Bollinger Bands
        bb_data = self.calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_width'] = bb_data['width']
        
        # ADX
        df['adx'] = self.calculate_adx(df['high'], df['low'], df['close'])
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        width = (upper - lower) / sma
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'width': width
        }
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate ADX indicator."""
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = minus_dm.abs()
        
        atr = self.calculate_atr(high, low, close, period)
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return adx
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        return atr
    
    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Optional[Dict]:
        """Generate trading signal using your actual strategy."""
        if current_idx < 50:  # Need enough data
            return None
            
        current_data = df.iloc[current_idx]
        historical_data = df.iloc[:current_idx+1]
        
        try:
            # Create market data object
            market_data = {
                'price': current_data['close'],
                'volume': current_data['volume'],
                'high': current_data['high'],
                'low': current_data['low'],
                'open': current_data['open'],
                'timestamp': current_data.name
            }
            
            # Generate signal using your actual logic
            signal = self.signal_generator.generate_signal(
                market_data=market_data,
                historical_data=historical_data,
                timeframe='1h'
            )
            
            if signal and signal.score >= self.min_score:
                return {
                    'symbol': 'BTC/USDT',  # We'll make this dynamic
                    'direction': signal.direction.value,
                    'score': signal.score,
                    'timestamp': current_data.name,
                    'price': current_data['close']
                }
                
        except Exception as e:
            print(f"Error generating signal: {e}")
            
        return None
    
    def execute_trade(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """Execute a trade based on signal."""
        if len(self.positions) >= self.max_positions:
            return None
            
        # Calculate position size
        risk_amount = self.balance * (self.risk_percent / 100)
        position_size = risk_amount / current_price
        
        if position_size <= 0:
            return None
            
        # Create trade
        trade = {
            'entry_time': signal['timestamp'],
            'entry_price': current_price,
            'direction': signal['direction'],
            'size': position_size,
            'score': signal['score'],
            'symbol': signal['symbol']
        }
        
        # Add to positions
        trade_id = f"{signal['symbol']}_{signal['timestamp'].strftime('%Y%m%d_%H%M%S')}"
        self.positions[trade_id] = trade
        
        return trade
    
    def update_positions(self, current_price: float, current_time: datetime):
        """Update open positions and check for exits."""
        positions_to_close = []
        
        for trade_id, trade in self.positions.items():
            # Simple exit strategy: 2% profit or 1% loss
            if trade['direction'] == 'LONG':
                pnl_pct = (current_price - trade['entry_price']) / trade['entry_price']
            else:  # SHORT
                pnl_pct = (trade['entry_price'] - current_price) / trade['entry_price']
            
            # Exit conditions
            if pnl_pct >= 0.02 or pnl_pct <= -0.01:  # 2% profit or 1% loss
                positions_to_close.append((trade_id, trade, pnl_pct))
        
        # Close positions
        for trade_id, trade, pnl_pct in positions_to_close:
            self.close_position(trade_id, trade, current_price, current_time, pnl_pct)
    
    def close_position(self, trade_id: str, trade: Dict, exit_price: float, exit_time: datetime, pnl_pct: float):
        """Close a position and update balance."""
        # Calculate P&L
        if trade['direction'] == 'LONG':
            pnl_amount = trade['size'] * (exit_price - trade['entry_price'])
        else:  # SHORT
            pnl_amount = trade['size'] * (trade['entry_price'] - exit_price)
        
        # Update balance
        self.balance += pnl_amount
        
        # Record trade
        completed_trade = {
            **trade,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'pnl_amount': pnl_amount,
            'duration_hours': (exit_time - trade['entry_time']).total_seconds() / 3600
        }
        
        self.trades.append(completed_trade)
        del self.positions[trade_id]
        
        print(f"✅ Trade closed: {trade['direction']} {trade['symbol']} | P&L: {pnl_pct:.2%} | Balance: ${self.balance:.2f}")
    
    async def run_backtest(self, symbol: str, start_date: datetime, end_date: datetime):
        """Run the backtest."""
        print(f"🚀 Starting REAL backtest for {symbol}")
        print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
        print("=" * 60)
        
        # Get historical data
        df = await self.get_historical_data(symbol, start_date, end_date)
        if df.empty:
            print(f"❌ No data found for {symbol}")
            return
        
        print(f"📊 Loaded {len(df)} candles")
        
        # Calculate technical indicators
        df = self.calculate_technical_indicators(df)
        
        # Run backtest
        signal_count = 0
        trade_count = 0
        
        for i in range(50, len(df)):  # Start after indicators are calculated
            current_data = df.iloc[i]
            current_time = current_data.name
            current_price = current_data['close']
            
            # Update existing positions
            self.update_positions(current_price, current_time)
            
            # Generate signal
            signal = self.generate_signal(df, i)
            if signal:
                signal_count += 1
                print(f"📈 Signal: {signal['direction']} {signal['symbol']} | Score: {signal['score']:.3f} | Price: ${current_price:.2f}")
                
                # Execute trade
                trade = self.execute_trade(signal, current_price)
                if trade:
                    trade_count += 1
                    print(f"🎯 Trade opened: {trade['direction']} {trade['symbol']} | Size: {trade['size']:.4f}")
            
            # Record equity curve
            self.equity_curve.append({
                'timestamp': current_time,
                'balance': self.balance,
                'price': current_price
            })
        
        # Close any remaining positions
        for trade_id, trade in list(self.positions.items()):
            self.close_position(trade_id, trade, df.iloc[-1]['close'], df.index[-1], 0)
        
        # Calculate results
        self.calculate_results()
    
    def calculate_results(self):
        """Calculate and display backtest results."""
        if not self.trades:
            print("❌ No trades executed")
            return
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = sum(t['pnl_amount'] for t in self.trades)
        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100
        
        # Average metrics
        avg_win = np.mean([t['pnl_pct'] for t in self.trades if t['pnl_pct'] > 0]) * 100 if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl_pct'] for t in self.trades if t['pnl_pct'] < 0]) * 100 if losing_trades > 0 else 0
        
        # Best and worst trades
        best_trade = max(self.trades, key=lambda x: x['pnl_pct'])['pnl_pct'] * 100
        worst_trade = min(self.trades, key=lambda x: x['pnl_pct'])['pnl_pct'] * 100
        
        # Display results
        print("\n" + "=" * 60)
        print("🎉 REAL BACKTEST RESULTS")
        print("=" * 60)
        print(f"💰 Final Balance: ${self.balance:,.2f}")
        print(f"📈 Total Return: {total_return:.2f}%")
        print(f"💵 Total P&L: ${total_pnl:,.2f}")
        print()
        print(f"📊 Trading Statistics:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {winning_trades}")
        print(f"   Losing Trades: {losing_trades}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print()
        print(f"🎯 Performance:")
        print(f"   Average Win: {avg_win:.2f}%")
        print(f"   Average Loss: {avg_loss:.2f}%")
        print(f"   Best Trade: {best_trade:.2f}%")
        print(f"   Worst Trade: {worst_trade:.2f}%")
        print()
        
        # Show recent trades
        print("📋 Recent Trades:")
        for trade in self.trades[-5:]:
            direction_emoji = "📈" if trade['direction'] == 'LONG' else "📉"
            pnl_emoji = "✅" if trade['pnl_pct'] > 0 else "❌"
            print(f"   {direction_emoji} {trade['symbol']} | {pnl_emoji} {trade['pnl_pct']:.2%} | ${trade['pnl_amount']:.2f}")

async def main():
    """Run the real backtest."""
    backtest = RealBacktest()
    await backtest.connect_db()
    
    # Run backtest for BTC/USDT for the last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    await backtest.run_backtest('BTC/USDT', start_date, end_date)
    
    await backtest.db_pool.close()

if __name__ == "__main__":
    asyncio.run(main())
