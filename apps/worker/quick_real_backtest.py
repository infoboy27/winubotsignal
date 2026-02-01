#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - Quick Real Data Backtest
============================================

This script runs a backtest using real market data from Binance API.
"""

import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import time

class QuickRealBacktest:
    """Quick real data backtest using live market data."""
    
    def __init__(self):
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
        
    def fetch_binance_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Fetch real OHLCV data from Binance API."""
        # Convert symbol format (BTC/USDT -> BTCUSDT)
        binance_symbol = symbol.replace('/', '')
        
        # Calculate timestamps
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
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
            
            df = pd.DataFrame(ohlcv_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        if len(df) < 50:
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
    
    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> Optional[Dict]:
        """Generate trading signal using real technical analysis."""
        if current_idx < 50:  # Need enough data
            return None
            
        current_data = df.iloc[current_idx]
        
        # Get technical indicators
        rsi_14 = current_data.get('rsi_14', 50)
        rsi_21 = current_data.get('rsi_21', 50)
        macd = current_data.get('macd', 0)
        macd_signal = current_data.get('macd_signal', 0)
        bb_upper = current_data.get('bb_upper', current_data['close'])
        bb_lower = current_data.get('bb_lower', current_data['close'])
        ema_12 = current_data.get('ema_12', current_data['close'])
        ema_26 = current_data.get('ema_26', current_data['close'])
        
        # Calculate signal score (0-1)
        score = 0.0
        direction = None
        
        # RSI signals
        if rsi_14 < 30 and rsi_21 < 35:  # Oversold
            score += 0.3
            direction = 'LONG'
        elif rsi_14 > 70 and rsi_21 > 65:  # Overbought
            score += 0.3
            direction = 'SHORT'
        
        # MACD signals
        if macd > macd_signal and macd > 0:  # Bullish MACD
            score += 0.2
            if direction is None:
                direction = 'LONG'
        elif macd < macd_signal and macd < 0:  # Bearish MACD
            score += 0.2
            if direction is None:
                direction = 'SHORT'
        
        # Bollinger Bands signals
        if current_data['close'] <= bb_lower:  # Price at lower band
            score += 0.2
            if direction is None:
                direction = 'LONG'
        elif current_data['close'] >= bb_upper:  # Price at upper band
            score += 0.2
            if direction is None:
                direction = 'SHORT'
        
        # EMA trend signals
        if ema_12 > ema_26:  # Uptrend
            score += 0.1
            if direction == 'LONG':
                score += 0.1
        elif ema_12 < ema_26:  # Downtrend
            score += 0.1
            if direction == 'SHORT':
                score += 0.1
        
        # Only return signal if score is high enough
        if score >= self.min_score and direction:
            return {
                'symbol': 'BTC/USDT',
                'direction': direction,
                'score': score,
                'timestamp': current_data.name,
                'price': float(current_data['close']),
                'take_profit': current_data['close'] * (1.02 if direction == 'LONG' else 0.98),
                'stop_loss': current_data['close'] * (0.98 if direction == 'LONG' else 1.02)
            }
            
        return None
    
    def execute_trade(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """Execute a trade based on signal."""
        if len(self.positions) >= self.max_positions:
            return None
            
        # Calculate position size based on risk
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
            'symbol': signal['symbol'],
            'take_profit': signal['take_profit'],
            'stop_loss': signal['stop_loss']
        }
        
        # Add to positions
        trade_id = f"{signal['symbol']}_{signal['timestamp'].strftime('%Y%m%d_%H%M%S')}"
        self.positions[trade_id] = trade
        
        return trade
    
    def update_positions(self, current_price: float, current_time: datetime):
        """Update open positions and check for exits."""
        positions_to_close = []
        
        for trade_id, trade in self.positions.items():
            # Use real take profit and stop loss levels
            if trade['direction'] == 'LONG':
                # Check take profit
                if current_price >= trade['take_profit']:
                    pnl_pct = (trade['take_profit'] - trade['entry_price']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'TAKE_PROFIT'))
                # Check stop loss
                elif current_price <= trade['stop_loss']:
                    pnl_pct = (trade['stop_loss'] - trade['entry_price']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'STOP_LOSS'))
            else:  # SHORT
                # Check take profit
                if current_price <= trade['take_profit']:
                    pnl_pct = (trade['entry_price'] - trade['take_profit']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'TAKE_PROFIT'))
                # Check stop loss
                elif current_price >= trade['stop_loss']:
                    pnl_pct = (trade['entry_price'] - trade['stop_loss']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'STOP_LOSS'))
        
        # Close positions
        for trade_id, trade, pnl_pct, exit_reason in positions_to_close:
            self.close_position(trade_id, trade, current_price, current_time, pnl_pct, exit_reason)
    
    def close_position(self, trade_id: str, trade: Dict, exit_price: float, exit_time: datetime, pnl_pct: float, exit_reason: str):
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
            'symbol': trade['symbol'],
            'direction': trade['direction'],
            'entry_time': trade['entry_time'].isoformat(),
            'exit_time': exit_time.isoformat(),
            'entry_price': trade['entry_price'],
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'pnl_amount': pnl_amount,
            'exit_reason': exit_reason,
            'duration_hours': (exit_time - trade['entry_time']).total_seconds() / 3600
        }
        
        self.trades.append(completed_trade)
        del self.positions[trade_id]
        
        print(f"✅ Trade closed: {trade['direction']} {trade['symbol']} | {exit_reason} | P&L: {pnl_pct:.2%} | Balance: ${self.balance:.2f}")
    
    def run_backtest(self, symbol: str, days: int = 30):
        """Run the real data backtest."""
        print(f"🚀 Starting REAL backtest for {symbol}")
        print(f"📅 Period: Last {days} days")
        print(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
        print("=" * 60)
        
        # Fetch real market data
        df = self.fetch_binance_data(symbol, days)
        if df.empty:
            print(f"❌ No data found for {symbol}")
            return
        
        print(f"📊 Loaded {len(df)} real candles from Binance")
        print(f"📅 Date range: {df.index[0]} to {df.index[-1]}")
        
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
                'timestamp': current_time.isoformat(),
                'balance': self.balance,
                'price': current_price
            })
        
        # Close any remaining positions
        for trade_id, trade in list(self.positions.items()):
            self.close_position(trade_id, trade, df.iloc[-1]['close'], df.index[-1], 0, 'END_OF_PERIOD')
        
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
        
        # Exit reason analysis
        take_profit_exits = len([t for t in self.trades if t['exit_reason'] == 'TAKE_PROFIT'])
        stop_loss_exits = len([t for t in self.trades if t['exit_reason'] == 'STOP_LOSS'])
        
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
        print(f"🚪 Exit Analysis:")
        print(f"   Take Profit Exits: {take_profit_exits}")
        print(f"   Stop Loss Exits: {stop_loss_exits}")
        print()
        
        # Show recent trades
        print("📋 Recent Trades:")
        for trade in self.trades[-5:]:
            direction_emoji = "📈" if trade['direction'] == 'LONG' else "📉"
            pnl_emoji = "✅" if trade['pnl_pct'] > 0 else "❌"
            print(f"   {direction_emoji} {trade['symbol']} | {pnl_emoji} {trade['pnl_pct']:.2%} | ${trade['pnl_amount']:.2f} | {trade['exit_reason']}")

def main():
    """Run the real data backtest."""
    backtest = QuickRealBacktest()
    
    # Run backtest for BTC/USDT for the last 30 days
    backtest.run_backtest('BTC/USDT', days=30)

if __name__ == "__main__":
    main()

