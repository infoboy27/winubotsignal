#!/usr/bin/env python3
"""
🚀 Winu Bot Signal - Yearly Backtest Analysis
============================================

This script runs a comprehensive year-long backtest and provides profitability suggestions.
"""

import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import time

class YearlyBacktest:
    """Enhanced backtest for full year analysis with profitability suggestions."""
    
    def __init__(self):
        # Enhanced backtest parameters
        self.initial_balance = 10000.0
        self.risk_percent = 2.0
        self.max_positions = 5
        self.min_score = 0.7
        
        # Results tracking
        self.trades = []
        self.balance = self.initial_balance
        self.positions = {}
        self.equity_curve = []
        self.monthly_returns = []
        self.drawdown_periods = []
        
    def fetch_binance_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Fetch real OHLCV data from Binance API for a full year."""
        binance_symbol = symbol.replace('/', '')
        
        # Calculate timestamps for full year
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
    
    def calculate_enhanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate enhanced technical indicators for better signal quality."""
        if len(df) < 100:
            return df
            
        # RSI with multiple timeframes
        df['rsi_14'] = self.calculate_rsi(df['close'], 14)
        df['rsi_21'] = self.calculate_rsi(df['close'], 21)
        df['rsi_50'] = self.calculate_rsi(df['close'], 50)
        
        # MACD with different parameters
        macd_12_26 = self.calculate_macd(df['close'], 12, 26, 9)
        macd_5_35 = self.calculate_macd(df['close'], 5, 35, 5)
        
        df['macd'] = macd_12_26['macd']
        df['macd_signal'] = macd_12_26['signal']
        df['macd_histogram'] = macd_12_26['histogram']
        df['macd_fast'] = macd_5_35['macd']
        df['macd_fast_signal'] = macd_5_35['signal']
        
        # Bollinger Bands with different periods
        bb_20 = self.calculate_bollinger_bands(df['close'], 20, 2)
        bb_50 = self.calculate_bollinger_bands(df['close'], 50, 2.5)
        
        df['bb_upper'] = bb_20['upper']
        df['bb_middle'] = bb_20['middle']
        df['bb_lower'] = bb_20['lower']
        df['bb_width'] = bb_20['width']
        df['bb_upper_50'] = bb_50['upper']
        df['bb_lower_50'] = bb_50['lower']
        
        # Multiple EMAs
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Volatility indicators
        df['atr'] = self.calculate_atr(df['high'], df['low'], df['close'])
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
        
        # Trend strength
        df['adx'] = self.calculate_adx(df['high'], df['low'], df['close'])
        
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
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate ADX (Average Directional Index)."""
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
    
    def generate_enhanced_signal(self, df: pd.DataFrame, current_idx: int) -> Optional[Dict]:
        """Generate enhanced trading signal with multiple confirmations."""
        if current_idx < 100:  # Need more data for enhanced indicators
            return None
            
        current_data = df.iloc[current_idx]
        
        # Get all indicators
        rsi_14 = current_data.get('rsi_14', 50)
        rsi_21 = current_data.get('rsi_21', 50)
        rsi_50 = current_data.get('rsi_50', 50)
        macd = current_data.get('macd', 0)
        macd_signal = current_data.get('macd_signal', 0)
        macd_fast = current_data.get('macd_fast', 0)
        macd_fast_signal = current_data.get('macd_fast_signal', 0)
        bb_upper = current_data.get('bb_upper', current_data['close'])
        bb_lower = current_data.get('bb_lower', current_data['close'])
        bb_upper_50 = current_data.get('bb_upper_50', current_data['close'])
        bb_lower_50 = current_data.get('bb_lower_50', current_data['close'])
        ema_12 = current_data.get('ema_12', current_data['close'])
        ema_26 = current_data.get('ema_26', current_data['close'])
        ema_50 = current_data.get('ema_50', current_data['close'])
        ema_200 = current_data.get('ema_200', current_data['close'])
        volume_ratio = current_data.get('volume_ratio', 1)
        adx = current_data.get('adx', 0)
        volatility = current_data.get('volatility', 0)
        
        # Enhanced signal scoring system
        score = 0.0
        direction = None
        confidence = 0.0
        
        # RSI Multi-timeframe Analysis
        rsi_bullish = 0
        rsi_bearish = 0
        
        if rsi_14 < 30 and rsi_21 < 35 and rsi_50 < 40:
            rsi_bullish = 0.3
        elif rsi_14 > 70 and rsi_21 > 65 and rsi_50 > 60:
            rsi_bearish = 0.3
        elif rsi_14 < 40 and rsi_21 < 45:
            rsi_bullish = 0.2
        elif rsi_14 > 60 and rsi_21 > 55:
            rsi_bearish = 0.2
        
        # MACD Multi-timeframe Analysis
        macd_bullish = 0
        macd_bearish = 0
        
        if macd > macd_signal and macd_fast > macd_fast_signal and macd > 0:
            macd_bullish = 0.25
        elif macd < macd_signal and macd_fast < macd_fast_signal and macd < 0:
            macd_bearish = 0.25
        elif macd > macd_signal:
            macd_bullish = 0.15
        elif macd < macd_signal:
            macd_bearish = 0.15
        
        # Bollinger Bands Analysis
        bb_bullish = 0
        bb_bearish = 0
        
        if current_data['close'] <= bb_lower and current_data['close'] <= bb_lower_50:
            bb_bullish = 0.2
        elif current_data['close'] >= bb_upper and current_data['close'] >= bb_upper_50:
            bb_bearish = 0.2
        elif current_data['close'] <= bb_lower:
            bb_bullish = 0.1
        elif current_data['close'] >= bb_upper:
            bb_bearish = 0.1
        
        # EMA Trend Analysis
        ema_bullish = 0
        ema_bearish = 0
        
        if ema_12 > ema_26 > ema_50 > ema_200:
            ema_bullish = 0.2
        elif ema_12 < ema_26 < ema_50 < ema_200:
            ema_bearish = 0.2
        elif ema_12 > ema_26 > ema_50:
            ema_bullish = 0.1
        elif ema_12 < ema_26 < ema_50:
            ema_bearish = 0.1
        
        # Volume Confirmation
        volume_bonus = 0
        if volume_ratio > 1.5:  # High volume
            volume_bonus = 0.1
        
        # Trend Strength Confirmation
        trend_bonus = 0
        if adx > 25:  # Strong trend
            trend_bonus = 0.1
        
        # Volatility Filter
        volatility_penalty = 0
        if volatility > 0.05:  # High volatility
            volatility_penalty = -0.1
        
        # Calculate total score
        bullish_score = rsi_bullish + macd_bullish + bb_bullish + ema_bullish + volume_bonus + trend_bonus + volatility_penalty
        bearish_score = rsi_bearish + macd_bearish + bb_bearish + ema_bearish + volume_bonus + trend_bonus + volatility_penalty
        
        if bullish_score > bearish_score and bullish_score >= self.min_score:
            direction = 'LONG'
            score = bullish_score
            confidence = min(0.95, bullish_score)
        elif bearish_score > bullish_score and bearish_score >= self.min_score:
            direction = 'SHORT'
            score = bearish_score
            confidence = min(0.95, bearish_score)
        
        if direction and score >= self.min_score:
            # Dynamic TP/SL based on volatility
            atr = current_data.get('atr', current_data['close'] * 0.02)
            volatility_multiplier = max(1.0, min(3.0, volatility * 100))
            
            if direction == 'LONG':
                take_profit = current_data['close'] * (1 + (0.02 * volatility_multiplier))
                stop_loss = current_data['close'] * (1 - (0.015 * volatility_multiplier))
            else:
                take_profit = current_data['close'] * (1 - (0.02 * volatility_multiplier))
                stop_loss = current_data['close'] * (1 + (0.015 * volatility_multiplier))
            
            return {
                'symbol': 'BTC/USDT',
                'direction': direction,
                'score': score,
                'confidence': confidence,
                'timestamp': current_data.name,
                'price': float(current_data['close']),
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'volume_ratio': volume_ratio,
                'adx': adx,
                'volatility': volatility
            }
            
        return None
    
    def execute_trade(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """Execute a trade with enhanced position sizing."""
        if len(self.positions) >= self.max_positions:
            return None
            
        # Enhanced position sizing based on confidence and volatility
        confidence = signal.get('confidence', 0.7)
        volatility = signal.get('volatility', 0.02)
        
        # Adjust risk based on confidence
        adjusted_risk = self.risk_percent * confidence
        
        # Adjust for volatility
        if volatility > 0.03:  # High volatility
            adjusted_risk *= 0.7
        elif volatility < 0.01:  # Low volatility
            adjusted_risk *= 1.2
        
        risk_amount = self.balance * (adjusted_risk / 100)
        position_size = risk_amount / current_price
        
        if position_size <= 0:
            return None
            
        trade = {
            'entry_time': signal['timestamp'],
            'entry_price': current_price,
            'direction': signal['direction'],
            'size': position_size,
            'score': signal['score'],
            'confidence': confidence,
            'symbol': signal['symbol'],
            'take_profit': signal['take_profit'],
            'stop_loss': signal['stop_loss'],
            'volume_ratio': signal.get('volume_ratio', 1),
            'adx': signal.get('adx', 0)
        }
        
        trade_id = f"{signal['symbol']}_{signal['timestamp'].strftime('%Y%m%d_%H%M%S')}"
        self.positions[trade_id] = trade
        
        return trade
    
    def update_positions(self, current_price: float, current_time: datetime):
        """Update positions with enhanced exit logic."""
        positions_to_close = []
        
        for trade_id, trade in self.positions.items():
            # Enhanced exit logic
            if trade['direction'] == 'LONG':
                # Take profit
                if current_price >= trade['take_profit']:
                    pnl_pct = (trade['take_profit'] - trade['entry_price']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'TAKE_PROFIT'))
                # Stop loss
                elif current_price <= trade['stop_loss']:
                    pnl_pct = (trade['stop_loss'] - trade['entry_price']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'STOP_LOSS'))
                # Trailing stop (if price moves favorably)
                elif current_price > trade['entry_price'] * 1.01:  # 1% profit
                    new_stop = trade['entry_price'] * 1.005  # Trail to 0.5% profit
                    if current_price <= new_stop:
                        pnl_pct = (new_stop - trade['entry_price']) / trade['entry_price']
                        positions_to_close.append((trade_id, trade, pnl_pct, 'TRAILING_STOP'))
            else:  # SHORT
                # Take profit
                if current_price <= trade['take_profit']:
                    pnl_pct = (trade['entry_price'] - trade['take_profit']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'TAKE_PROFIT'))
                # Stop loss
                elif current_price >= trade['stop_loss']:
                    pnl_pct = (trade['entry_price'] - trade['stop_loss']) / trade['entry_price']
                    positions_to_close.append((trade_id, trade, pnl_pct, 'STOP_LOSS'))
                # Trailing stop
                elif current_price < trade['entry_price'] * 0.99:  # 1% profit
                    new_stop = trade['entry_price'] * 0.995  # Trail to 0.5% profit
                    if current_price >= new_stop:
                        pnl_pct = (trade['entry_price'] - new_stop) / trade['entry_price']
                        positions_to_close.append((trade_id, trade, pnl_pct, 'TRAILING_STOP'))
        
        # Close positions
        for trade_id, trade, pnl_pct, exit_reason in positions_to_close:
            self.close_position(trade_id, trade, current_price, current_time, pnl_pct, exit_reason)
    
    def close_position(self, trade_id: str, trade: Dict, exit_price: float, exit_time: datetime, pnl_pct: float, exit_reason: str):
        """Close position and record enhanced trade data."""
        if trade['direction'] == 'LONG':
            pnl_amount = trade['size'] * (exit_price - trade['entry_price'])
        else:
            pnl_amount = trade['size'] * (trade['entry_price'] - exit_price)
        
        self.balance += pnl_amount
        
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
            'duration_hours': (exit_time - trade['entry_time']).total_seconds() / 3600,
            'confidence': trade.get('confidence', 0.7),
            'volume_ratio': trade.get('volume_ratio', 1),
            'adx': trade.get('adx', 0)
        }
        
        self.trades.append(completed_trade)
        del self.positions[trade_id]
        
        print(f"✅ Trade closed: {trade['direction']} {trade['symbol']} | {exit_reason} | P&L: {pnl_pct:.2%} | Balance: ${self.balance:.2f}")
    
    def run_yearly_backtest(self, symbol: str, days: int = 365):
        """Run comprehensive yearly backtest."""
        print(f"🚀 Starting YEARLY backtest for {symbol}")
        print(f"📅 Period: Last {days} days (Full Year)")
        print(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
        print("=" * 80)
        
        # Fetch data
        df = self.fetch_binance_data(symbol, days)
        if df.empty:
            print(f"❌ No data found for {symbol}")
            return
        
        print(f"📊 Loaded {len(df)} real candles from Binance")
        print(f"📅 Date range: {df.index[0]} to {df.index[-1]}")
        
        # Calculate enhanced indicators
        df = self.calculate_enhanced_indicators(df)
        
        # Run backtest
        signal_count = 0
        trade_count = 0
        monthly_balance = self.initial_balance
        
        for i in range(100, len(df)):  # Start after indicators are calculated
            current_data = df.iloc[i]
            current_time = current_data.name
            current_price = current_data['close']
            
            # Track monthly performance
            if i % 720 == 0:  # Every 30 days (720 hours)
                monthly_return = (self.balance - monthly_balance) / monthly_balance * 100
                self.monthly_returns.append(monthly_return)
                monthly_balance = self.balance
                print(f"📅 Month {len(self.monthly_returns)}: Balance ${self.balance:.2f} | Return {monthly_return:.2f}%")
            
            # Update positions
            self.update_positions(current_price, current_time)
            
            # Generate signal
            signal = self.generate_enhanced_signal(df, i)
            if signal:
                signal_count += 1
                print(f"📈 Signal: {signal['direction']} {signal['symbol']} | Score: {signal['score']:.3f} | Confidence: {signal['confidence']:.3f} | Price: ${current_price:.2f}")
                
                # Execute trade
                trade = self.execute_trade(signal, current_price)
                if trade:
                    trade_count += 1
                    print(f"🎯 Trade opened: {trade['direction']} {trade['symbol']} | Size: {trade['size']:.4f} | Confidence: {trade['confidence']:.3f}")
            
            # Record equity curve
            self.equity_curve.append({
                'timestamp': current_time.isoformat(),
                'balance': self.balance,
                'price': current_price
            })
        
        # Close remaining positions
        for trade_id, trade in list(self.positions.items()):
            self.close_position(trade_id, trade, df.iloc[-1]['close'], df.index[-1], 0, 'END_OF_PERIOD')
        
        # Calculate comprehensive results
        self.calculate_yearly_results()
    
    def calculate_yearly_results(self):
        """Calculate comprehensive yearly results and provide suggestions."""
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
        
        # Advanced metrics
        avg_win = np.mean([t['pnl_pct'] for t in self.trades if t['pnl_pct'] > 0]) * 100 if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl_pct'] for t in self.trades if t['pnl_pct'] < 0]) * 100 if losing_trades > 0 else 0
        
        best_trade = max(self.trades, key=lambda x: x['pnl_pct'])['pnl_pct'] * 100
        worst_trade = min(self.trades, key=lambda x: x['pnl_pct'])['pnl_pct'] * 100
        
        # Risk metrics
        returns = [t['pnl_pct'] for t in self.trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Monthly analysis
        positive_months = len([r for r in self.monthly_returns if r > 0])
        monthly_win_rate = (positive_months / len(self.monthly_returns)) * 100 if self.monthly_returns else 0
        
        # Exit analysis
        take_profit_exits = len([t for t in self.trades if t['exit_reason'] == 'TAKE_PROFIT'])
        stop_loss_exits = len([t for t in self.trades if t['exit_reason'] == 'STOP_LOSS'])
        trailing_stop_exits = len([t for t in self.trades if t['exit_reason'] == 'TRAILING_STOP'])
        
        # Display results
        print("\n" + "=" * 80)
        print("🎉 YEARLY BACKTEST RESULTS")
        print("=" * 80)
        print(f"💰 Final Balance: ${self.balance:,.2f}")
        print(f"📈 Total Return: {total_return:.2f}%")
        print(f"💵 Total P&L: ${total_pnl:,.2f}")
        print(f"📊 Sharpe Ratio: {sharpe_ratio:.2f}")
        print()
        print(f"📊 Trading Statistics:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {winning_trades}")
        print(f"   Losing Trades: {losing_trades}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   Monthly Win Rate: {monthly_win_rate:.1f}%")
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
        print(f"   Trailing Stop Exits: {trailing_stop_exits}")
        print()
        
        # Monthly breakdown
        if self.monthly_returns:
            print("📅 Monthly Performance:")
            for i, monthly_return in enumerate(self.monthly_returns, 1):
                print(f"   Month {i}: {monthly_return:.2f}%")
            print()
        
        # Profitability suggestions
        self.provide_profitability_suggestions(total_return, win_rate, sharpe_ratio, avg_win, avg_loss)
    
    def provide_profitability_suggestions(self, total_return: float, win_rate: float, sharpe_ratio: float, avg_win: float, avg_loss: float):
        """Provide specific suggestions to improve profitability."""
        print("💡 PROFITABILITY SUGGESTIONS:")
        print("=" * 50)
        
        suggestions = []
        
        # Return analysis
        if total_return < 0:
            suggestions.append("🔴 NEGATIVE RETURNS: Consider reducing position sizes or improving signal quality")
        elif total_return < 10:
            suggestions.append("🟡 LOW RETURNS: Strategy needs optimization for better performance")
        elif total_return > 50:
            suggestions.append("🟢 GOOD RETURNS: Consider scaling up position sizes gradually")
        
        # Win rate analysis
        if win_rate < 40:
            suggestions.append("🔴 LOW WIN RATE: Focus on higher quality signals with multiple confirmations")
        elif win_rate < 55:
            suggestions.append("🟡 MODERATE WIN RATE: Improve entry timing and signal filtering")
        else:
            suggestions.append("🟢 GOOD WIN RATE: Consider increasing position sizes for winning trades")
        
        # Risk-reward analysis
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        if risk_reward_ratio < 1.5:
            suggestions.append("🔴 POOR RISK-REWARD: Improve take profit levels or reduce stop losses")
        elif risk_reward_ratio < 2.0:
            suggestions.append("🟡 MODERATE RISK-REWARD: Optimize TP/SL ratios for better profitability")
        else:
            suggestions.append("🟢 GOOD RISK-REWARD: Current risk management is effective")
        
        # Sharpe ratio analysis
        if sharpe_ratio < 1.0:
            suggestions.append("🔴 LOW SHARPE RATIO: High volatility relative to returns - consider position sizing")
        elif sharpe_ratio < 2.0:
            suggestions.append("🟡 MODERATE SHARPE RATIO: Good risk-adjusted returns")
        else:
            suggestions.append("🟢 EXCELLENT SHARPE RATIO: Excellent risk-adjusted performance")
        
        # Specific recommendations
        print("\n🎯 SPECIFIC RECOMMENDATIONS:")
        print("-" * 30)
        
        if win_rate < 50:
            print("1. 📈 IMPROVE SIGNAL QUALITY:")
            print("   - Increase minimum score threshold to 0.8+")
            print("   - Require multiple timeframe confirmations")
            print("   - Add volume and trend strength filters")
        
        if risk_reward_ratio < 2.0:
            print("2. 🎯 OPTIMIZE RISK MANAGEMENT:")
            print("   - Use dynamic TP/SL based on volatility")
            print("   - Implement trailing stops for winning trades")
            print("   - Consider partial position closing")
        
        if sharpe_ratio < 1.5:
            print("3. ⚖️ IMPROVE RISK-ADJUSTED RETURNS:")
            print("   - Reduce position sizes during high volatility")
            print("   - Add correlation filters to avoid similar trades")
            print("   - Implement maximum daily loss limits")
        
        print("4. 🔄 STRATEGY ENHANCEMENTS:")
        print("   - Add market regime detection (trending vs ranging)")
        print("   - Implement seasonal adjustments")
        print("   - Use multiple timeframes for confirmation")
        print("   - Add fundamental analysis filters")
        
        print("5. 📊 MONITORING IMPROVEMENTS:")
        print("   - Track performance by market conditions")
        print("   - Monitor drawdown periods closely")
        print("   - Implement performance attribution analysis")
        
        # Display all suggestions
        for suggestion in suggestions:
            print(suggestion)

def main():
    """Run the yearly backtest analysis."""
    backtest = YearlyBacktest()
    
    # Run yearly backtest for BTC/USDT
    backtest.run_yearly_backtest('BTC/USDT', days=365)

if __name__ == "__main__":
    main()

