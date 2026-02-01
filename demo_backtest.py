#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - DEMO Backtest System
=========================================

This script demonstrates the backtest functionality with realistic mock data.
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class DemoBacktest:
    """Demo backtest with realistic mock data."""
    
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
        
    def generate_mock_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate realistic mock OHLCV data."""
        # Generate hourly data
        date_range = pd.date_range(start=start_date, end=end_date, freq='1H')
        
        # Start with a base price
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100
        
        # Generate realistic price movements
        np.random.seed(42)  # For reproducible results
        returns = np.random.normal(0, 0.02, len(date_range))  # 2% volatility
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, base_price * 0.5))  # Prevent negative prices
        
        # Create OHLCV data
        data = []
        for i, (timestamp, price) in enumerate(zip(date_range, prices)):
            # Generate realistic OHLC from close price
            volatility = np.random.uniform(0.005, 0.02)
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = prices[i-1] if i > 0 else price
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'timestamp': timestamp,
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    
    def generate_mock_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Generate realistic mock signals."""
        signals = []
        
        for i in range(50, len(df), 24):  # Signal every 24 hours
            current_data = df.iloc[i]
            
            # Generate signal based on price action
            if i > 0:
                prev_data = df.iloc[i-1]
                price_change = (current_data['close'] - prev_data['close']) / prev_data['close']
                
                # Generate signals based on price momentum
                if price_change > 0.01:  # 1% up
                    direction = 'LONG'
                    score = min(0.9, 0.6 + abs(price_change) * 10)
                elif price_change < -0.01:  # 1% down
                    direction = 'SHORT'
                    score = min(0.9, 0.6 + abs(price_change) * 10)
                else:
                    continue  # Skip sideways markets
                
                # Calculate realistic TP/SL levels
                if direction == 'LONG':
                    take_profit = current_data['close'] * 1.02  # 2% TP
                    stop_loss = current_data['close'] * 0.98   # 2% SL
                else:
                    take_profit = current_data['close'] * 0.98  # 2% TP
                    stop_loss = current_data['close'] * 1.02   # 2% SL
                
                signals.append({
                    'id': len(signals) + 1,
                    'symbol': 'BTC/USDT',
                    'direction': direction,
                    'entry_price': current_data['close'],
                    'take_profit': take_profit,
                    'stop_loss': stop_loss,
                    'score': score,
                    'created_at': current_data.name
                })
        
        return signals
    
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
            'entry_time': signal['created_at'],
            'entry_price': current_price,
            'direction': signal['direction'],
            'size': position_size,
            'score': signal['score'],
            'symbol': signal['symbol'],
            'take_profit': signal['take_profit'],
            'stop_loss': signal['stop_loss']
        }
        
        # Add to positions
        trade_id = f"{signal['symbol']}_{signal['id']}"
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
    
    def run_backtest(self, symbol: str, start_date: datetime, end_date: datetime):
        """Run the demo backtest."""
        print(f"🚀 Starting DEMO backtest for {symbol}")
        print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
        print("=" * 60)
        
        # Generate mock data
        df = self.generate_mock_data(symbol, start_date, end_date)
        print(f"📊 Generated {len(df)} candles")
        
        # Generate mock signals
        signals = self.generate_mock_signals(df)
        print(f"🎯 Generated {len(signals)} signals")
        
        # Calculate technical indicators
        df = self.calculate_technical_indicators(df)
        
        # Create signal lookup by timestamp
        signal_lookup = {}
        for signal in signals:
            signal_time = signal['created_at']
            # Find closest candle
            try:
                closest_idx = df.index.get_indexer([signal_time], method='nearest')[0]
                if closest_idx >= 0:
                    signal_lookup[closest_idx] = signal
            except:
                continue
        
        # Run backtest
        trade_count = 0
        
        for i in range(50, len(df)):  # Start after indicators are calculated
            current_data = df.iloc[i]
            current_time = current_data.name
            current_price = current_data['close']
            
            # Update existing positions
            self.update_positions(current_price, current_time)
            
            # Check if there's a signal at this time
            if i in signal_lookup:
                signal = signal_lookup[i]
                if signal['score'] >= self.min_score:
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
        print("🎉 DEMO BACKTEST RESULTS")
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
    """Run the demo backtest."""
    backtest = DemoBacktest()
    
    # Run backtest for BTC/USDT for the last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 3 months
    
    backtest.run_backtest('BTC/USDT', start_date, end_date)

if __name__ == "__main__":
    main()

