#!/usr/bin/env python3
"""
Balanced Win Rate Improvement Backtest
Realistic filters that actually improve win rate without being too restrictive
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

class BalancedWinRateBacktest:
    """Balanced backtest with realistic win rate improvements."""
    
    def __init__(self):
        # Enhanced parameters for win rate improvement
        self.initial_balance = 10000.0
        self.risk_percent = 2.0
        self.max_positions = 5
        self.min_score = 0.7  # Slightly lower for more signals
        
        # Balanced win rate improvement parameters
        self.multi_timeframe_required = True
        self.support_resistance_required = True
        self.momentum_confirmation_required = True
        self.sentiment_filter_required = False  # Less restrictive
        self.entry_timing_required = False  # Less restrictive
        
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
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate ADX indicator."""
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        dm_plus = high.diff()
        dm_minus = -low.diff()
        dm_plus = dm_plus.where((dm_plus > dm_minus) & (dm_plus > 0), 0)
        dm_minus = dm_minus.where((dm_minus > dm_plus) & (dm_minus > 0), 0)
        
        # Smoothed values
        atr = tr.rolling(period).mean()
        di_plus = 100 * (dm_plus.rolling(period).mean() / atr)
        di_minus = 100 * (dm_minus.rolling(period).mean() / atr)
        
        # ADX calculation
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(period).mean()
        
        return adx
    
    def check_multi_timeframe_trend(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #1: Relaxed multi-timeframe confirmation."""
        if len(df_1h) < 50 or len(df_4h) < 20:
            return True  # Allow if not enough data
        
        # 1H trend (more lenient)
        ema_20_1h = df_1h['close'].ewm(span=20).mean()
        ema_50_1h = df_1h['close'].ewm(span=50).mean()
        trend_1h = ema_20_1h.iloc[-1] > ema_50_1h.iloc[-1]
        
        # 4H trend (more lenient)
        ema_20_4h = df_4h['close'].ewm(span=20).mean()
        ema_50_4h = df_4h['close'].ewm(span=50).mean()
        trend_4h = ema_20_4h.iloc[-1] > ema_50_4h.iloc[-1]
        
        # At least one timeframe should be bullish
        return trend_1h or trend_4h
    
    def check_support_resistance(self, df: pd.DataFrame, current_price: float) -> bool:
        """WIN RATE IMPROVEMENT #2: Relaxed support/resistance filtering."""
        if len(df) < 20:
            return True  # Allow if not enough data
        
        # Find recent highs and lows
        recent_highs = df['high'].rolling(20).max()
        recent_lows = df['low'].rolling(20).min()
        
        # Check if price is near key levels (within 3% - more lenient)
        resistance_near = abs(current_price - recent_highs.iloc[-1]) / current_price < 0.03
        support_near = abs(current_price - recent_lows.iloc[-1]) / current_price < 0.03
        
        # Allow if near any key level OR if price is in middle range
        price_range = (recent_highs.iloc[-1] - recent_lows.iloc[-1]) / recent_lows.iloc[-1]
        in_middle_range = 0.3 < (current_price - recent_lows.iloc[-1]) / (recent_highs.iloc[-1] - recent_lows.iloc[-1]) < 0.7
        
        return resistance_near or support_near or in_middle_range
    
    def check_momentum_confirmation(self, df: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #3: Relaxed momentum confirmation."""
        if len(df) < 50:
            return True  # Allow if not enough data
        
        # RSI momentum (more lenient)
        rsi = self.calculate_rsi(df['close'], 14)
        rsi_momentum = rsi.iloc[-1] > 45  # Less strict than 50
        
        # MACD momentum (more lenient)
        macd_line, signal_line, _ = self.calculate_macd(df['close'])
        macd_momentum = macd_line.iloc[-1] > signal_line.iloc[-1] * 0.95  # Allow small negative
        
        # Price momentum (more lenient)
        if len(df) >= 5:
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            price_momentum = price_change > -0.005  # Allow small negative momentum
        else:
            price_momentum = True
        
        # At least 2 out of 3 should be positive
        positive_signals = sum([rsi_momentum, macd_momentum, price_momentum])
        return positive_signals >= 2
    
    def generate_enhanced_signals(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Generate signals with balanced win rate improvements."""
        signals = []
        
        if len(df) < 100:
            return signals
        
        # Create 4H timeframe data for multi-timeframe analysis
        df_4h = df.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        print(f"🔍 BALANCED WIN RATE IMPROVEMENT ANALYSIS:")
        print(f"   📊 1H Data Points: {len(df)}")
        print(f"   📊 4H Data Points: {len(df_4h)}")
        
        # Track filter effectiveness
        total_candidates = 0
        multi_timeframe_passed = 0
        support_resistance_passed = 0
        momentum_passed = 0
        final_signals = 0
        
        for i in range(100, len(df)):
            current = df.iloc[i]
            total_candidates += 1
            
            # WIN RATE IMPROVEMENT #1: Multi-timeframe confirmation (relaxed)
            if self.multi_timeframe_required:
                if not self.check_multi_timeframe_trend(df.iloc[:i+1], df_4h):
                    continue
                multi_timeframe_passed += 1
            
            # WIN RATE IMPROVEMENT #2: Support/Resistance filtering (relaxed)
            if self.support_resistance_required:
                if not self.check_support_resistance(df.iloc[:i+1], current['close']):
                    continue
                support_resistance_passed += 1
            
            # WIN RATE IMPROVEMENT #3: Momentum confirmation (relaxed)
            if self.momentum_confirmation_required:
                if not self.check_momentum_confirmation(df.iloc[:i+1]):
                    continue
                momentum_passed += 1
            
            # Original signal generation with enhanced scoring
            rsi_14 = self.calculate_rsi(df['close'], 14)
            rsi_21 = self.calculate_rsi(df['close'], 21)
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            
            # Enhanced signal scoring
            score = 0.4  # Lower base score for more signals
            
            # RSI signals (enhanced but more lenient)
            if rsi_14.iloc[i] < 35 and rsi_21.iloc[i] < 40:  # More lenient oversold
                score += 0.15  # Oversold bonus
            elif rsi_14.iloc[i] > 65 and rsi_21.iloc[i] > 60:  # More lenient overbought
                score -= 0.15  # Overbought penalty
            
            # EMA trend signals (enhanced)
            if ema_12.iloc[i] > ema_26.iloc[i]:
                score += 0.15  # Uptrend bonus
            elif ema_12.iloc[i] < ema_26.iloc[i]:
                score -= 0.15  # Downtrend penalty
            
            # Volume confirmation (enhanced but more lenient)
            avg_volume = df['volume'].rolling(20).mean()
            if df['volume'].iloc[i] > avg_volume.iloc[i] * 1.2:  # Lower volume requirement
                score += 0.1  # Volume bonus
            
            # Additional momentum bonus
            if len(df) >= 5:
                price_change = (df['close'].iloc[i] - df['close'].iloc[i-5]) / df['close'].iloc[i-5]
                if price_change > 0.005:  # 0.5% positive momentum
                    score += 0.1
            
            # Only generate signal if score is high enough
            if score >= self.min_score:
                direction = 'LONG' if score > 0.5 else 'SHORT'
                
                # Calculate TP/SL levels (more conservative)
                if direction == 'LONG':
                    take_profit = current['close'] * 1.015  # 1.5% TP
                    stop_loss = current['close'] * 0.985   # 1.5% SL
                else:
                    take_profit = current['close'] * 0.985  # 1.5% TP
                    stop_loss = current['close'] * 1.015   # 1.5% SL
                
                signals.append({
                    'id': len(signals) + 1,
                    'symbol': symbol,
                    'signal_type': 'BALANCED_WIN_RATE',
                    'direction': direction,
                    'entry_price': current['close'],
                    'take_profit_1': take_profit,
                    'stop_loss': stop_loss,
                    'score': score,
                    'is_active': True,
                    'created_at': current.name,
                    'realized_pnl': 0.0,
                    'win_rate_improvements': {
                        'multi_timeframe': True,
                        'support_resistance': True,
                        'momentum_confirmation': True,
                        'sentiment_filter': False,
                        'entry_timing': False
                    }
                })
                final_signals += 1
        
        # Display filter effectiveness
        print(f"   📊 Filter Effectiveness:")
        print(f"      Total Candidates: {total_candidates}")
        print(f"      Multi-timeframe: {multi_timeframe_passed} ({multi_timeframe_passed/total_candidates*100:.1f}%)")
        print(f"      Support/Resistance: {support_resistance_passed} ({support_resistance_passed/total_candidates*100:.1f}%)")
        print(f"      Momentum: {momentum_passed} ({momentum_passed/total_candidates*100:.1f}%)")
        print(f"   ✅ Final signals generated: {final_signals}")
        return signals
    
    def run_enhanced_backtest(self, symbol: str, start_date: datetime, end_date: datetime):
        """Run enhanced backtest with balanced win rate improvements."""
        print(f"🚀 BALANCED WIN RATE BACKTEST STARTING")
        print(f"   📈 Symbol: {symbol}")
        print(f"   📅 Period: {start_date} to {end_date}")
        print(f"   🎯 Target Win Rate: 40-60% (vs. current 28.6%)")
        print(f"   🔧 Strategy: Balanced improvements (realistic filters)")
        
        # Fetch data
        days = (end_date - start_date).days
        df = self.fetch_binance_data(symbol, days)
        
        if df.empty:
            print(f"❌ No data available for {symbol}")
            return
        
        print(f"📊 Data fetched: {len(df)} candles")
        
        # Generate enhanced signals
        signals = self.generate_enhanced_signals(df, symbol)
        
        if not signals:
            print("❌ No enhanced signals generated")
            return
        
        print(f"🎯 Enhanced signals: {len(signals)}")
        
        # Execute trades
        for signal in signals:
            self.execute_trade(signal, df)
        
        # Calculate results
        self.calculate_performance()
        
        # Display results
        self.display_results()
    
    def execute_trade(self, signal: Dict, df: pd.DataFrame):
        """Execute a trade with enhanced risk management."""
        trade_id = len(self.trades) + 1
        entry_price = signal['entry_price']
        direction = signal['direction']
        
        # Position sizing
        risk_amount = self.balance * (self.risk_percent / 100)
        stop_loss = signal['stop_loss']
        risk_per_trade = abs(entry_price - stop_loss) / entry_price
        position_size = risk_amount / (risk_per_trade * entry_price)
        
        # Find exit
        exit_price, exit_reason = self.find_exit(signal, df)
        
        # Calculate P&L
        if direction == 'LONG':
            pnl = (exit_price - entry_price) / entry_price
        else:
            pnl = (entry_price - exit_price) / entry_price
        
        pnl_amount = pnl * position_size * entry_price
        
        # Update balance
        self.balance += pnl_amount
        
        # Record trade
        trade = {
            'id': trade_id,
            'symbol': signal['symbol'],
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_percent': pnl * 100,
            'pnl_amount': pnl_amount,
            'position_size': position_size,
            'score': signal['score'],
            'win_rate_improvements': signal['win_rate_improvements']
        }
        
        self.trades.append(trade)
        self.equity_curve.append(self.balance)
        
        print(f"   📊 Trade {trade_id}: {direction} {signal['symbol']} @ {entry_price:.2f} → {exit_price:.2f} ({pnl*100:+.2f}%)")
    
    def find_exit(self, signal: Dict, df: pd.DataFrame) -> Tuple[float, str]:
        """Find exit price and reason."""
        entry_price = signal['entry_price']
        take_profit = signal['take_profit_1']
        stop_loss = signal['stop_loss']
        direction = signal['direction']
        
        # Find the candle after signal
        signal_time = signal['created_at']
        future_data = df[df.index > signal_time]
        
        if future_data.empty:
            return entry_price, 'NO_DATA'
        
        # Check for TP/SL hits
        for _, candle in future_data.iterrows():
            if direction == 'LONG':
                if candle['high'] >= take_profit:
                    return take_profit, 'TAKE_PROFIT'
                elif candle['low'] <= stop_loss:
                    return stop_loss, 'STOP_LOSS'
            else:
                if candle['low'] <= take_profit:
                    return take_profit, 'TAKE_PROFIT'
                elif candle['high'] >= stop_loss:
                    return stop_loss, 'STOP_LOSS'
        
        # If no TP/SL hit, use last price
        return future_data['close'].iloc[-1], 'TIME_EXIT'
    
    def calculate_performance(self):
        """Calculate enhanced performance metrics."""
        if not self.trades:
            return
        
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_percent'] > 0])
        losing_trades = total_trades - winning_trades
        
        self.win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        self.total_return = ((self.balance - self.initial_balance) / self.initial_balance) * 100
        
        # Calculate additional metrics
        if winning_trades > 0:
            self.avg_win = np.mean([t['pnl_percent'] for t in self.trades if t['pnl_percent'] > 0])
        else:
            self.avg_win = 0
        
        if losing_trades > 0:
            self.avg_loss = np.mean([t['pnl_percent'] for t in self.trades if t['pnl_percent'] < 0])
        else:
            self.avg_loss = 0
        
        self.best_trade = max([t['pnl_percent'] for t in self.trades]) if self.trades else 0
        self.worst_trade = min([t['pnl_percent'] for t in self.trades]) if self.trades else 0
        
        # Risk metrics
        if self.equity_curve:
            peak = self.initial_balance
            max_dd = 0
            for value in self.equity_curve:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
            self.max_drawdown = max_dd * 100
        else:
            self.max_drawdown = 0
    
    def display_results(self):
        """Display enhanced backtest results."""
        print(f"\n🎉 BALANCED WIN RATE BACKTEST RESULTS")
        print(f"=" * 50)
        print(f"📊 PERFORMANCE METRICS:")
        print(f"   💰 Initial Balance: ${self.initial_balance:,.2f}")
        print(f"   💰 Final Balance: ${self.balance:,.2f}")
        print(f"   📈 Total Return: {self.total_return:+.2f}%")
        print(f"   📊 Total Trades: {len(self.trades)}")
        print(f"   🎯 Win Rate: {self.win_rate:.1f}%")
        print(f"   📈 Average Win: {self.avg_win:+.2f}%")
        print(f"   📉 Average Loss: {self.avg_loss:+.2f}%")
        print(f"   🏆 Best Trade: {self.best_trade:+.2f}%")
        print(f"   💥 Worst Trade: {self.worst_trade:+.2f}%")
        print(f"   📉 Max Drawdown: {self.max_drawdown:.2f}%")
        
        print(f"\n🚀 WIN RATE IMPROVEMENTS APPLIED:")
        print(f"   ✅ Multi-timeframe confirmation (relaxed)")
        print(f"   ✅ Support/Resistance filtering (relaxed)")
        print(f"   ✅ Momentum confirmation (relaxed)")
        print(f"   ⚪ Market sentiment filter (disabled)")
        print(f"   ⚪ Entry timing optimization (disabled)")
        
        # Win rate improvement analysis
        if self.win_rate > 50:
            print(f"\n🎉 EXCELLENT! Win rate improved to {self.win_rate:.1f}% (Target: 40-60%)")
        elif self.win_rate > 40:
            print(f"\n✅ GOOD! Win rate improved to {self.win_rate:.1f}% (Target: 40-60%)")
        elif self.win_rate > 30:
            print(f"\n⚠️ MODERATE: Win rate improved to {self.win_rate:.1f}% (Getting better)")
        else:
            print(f"\n❌ Win rate: {self.win_rate:.1f}% (Still needs improvement)")

def main():
    """Run the balanced win rate backtest."""
    backtest = BalancedWinRateBacktest()
    
    # Run enhanced backtest for BTC/USDT
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 30 days
    
    backtest.run_enhanced_backtest('BTC/USDT', start_date, end_date)

if __name__ == "__main__":
    main()

