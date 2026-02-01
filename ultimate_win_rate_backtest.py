#!/usr/bin/env python3
"""
Ultimate Win Rate Improvement Backtest
Implements ALL 9 win rate improvement techniques for maximum performance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests

class UltimateWinRateBacktest:
    """Ultimate backtest with ALL win rate improvements."""
    
    def __init__(self):
        # Enhanced parameters for maximum win rate
        self.initial_balance = 10000.0
        self.risk_percent = 2.0
        self.max_positions = 5
        self.min_score = 0.7  # Balanced for more signals
        
        # ALL win rate improvement parameters
        self.multi_timeframe_required = True
        self.support_resistance_required = True
        self.momentum_confirmation_required = True
        self.sentiment_filter_required = True  # ENABLED
        self.entry_timing_required = True      # ENABLED
        self.volume_confirmation_required = True  # NEW
        self.risk_reward_optimization_required = True  # NEW
        self.position_sizing_optimization_required = True  # NEW
        self.exit_strategy_enhancement_required = True  # NEW
        
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
    
    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """Calculate volatility for risk-reward optimization."""
        returns = df['close'].pct_change()
        volatility = returns.rolling(period).std().iloc[-1]
        return volatility
    
    def check_multi_timeframe_trend(self, df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #1: Multi-timeframe confirmation."""
        if len(df_1h) < 50 or len(df_4h) < 20:
            return True
        
        # 1H trend
        ema_20_1h = df_1h['close'].ewm(span=20).mean()
        ema_50_1h = df_1h['close'].ewm(span=50).mean()
        trend_1h = ema_20_1h.iloc[-1] > ema_50_1h.iloc[-1]
        
        # 4H trend
        ema_20_4h = df_4h['close'].ewm(span=20).mean()
        ema_50_4h = df_4h['close'].ewm(span=50).mean()
        trend_4h = ema_20_4h.iloc[-1] > ema_50_4h.iloc[-1]
        
        return trend_1h or trend_4h
    
    def check_support_resistance(self, df: pd.DataFrame, current_price: float) -> bool:
        """WIN RATE IMPROVEMENT #2: Support/Resistance filtering."""
        if len(df) < 20:
            return True
        
        recent_highs = df['high'].rolling(20).max()
        recent_lows = df['low'].rolling(20).min()
        
        resistance_near = abs(current_price - recent_highs.iloc[-1]) / current_price < 0.03
        support_near = abs(current_price - recent_lows.iloc[-1]) / current_price < 0.03
        
        price_range = (recent_highs.iloc[-1] - recent_lows.iloc[-1]) / recent_lows.iloc[-1]
        in_middle_range = 0.3 < (current_price - recent_lows.iloc[-1]) / (recent_highs.iloc[-1] - recent_lows.iloc[-1]) < 0.7
        
        return resistance_near or support_near or in_middle_range
    
    def check_momentum_confirmation(self, df: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #3: Momentum confirmation."""
        if len(df) < 50:
            return True
        
        rsi = self.calculate_rsi(df['close'], 14)
        rsi_momentum = rsi.iloc[-1] > 45
        
        macd_line, signal_line, _ = self.calculate_macd(df['close'])
        macd_momentum = macd_line.iloc[-1] > signal_line.iloc[-1] * 0.95
        
        if len(df) >= 5:
            price_change = (df['close'].iloc[-1] - df['close'].iloc[-5]) / df['close'].iloc[-5]
            price_momentum = price_change > -0.005
        else:
            price_momentum = True
        
        positive_signals = sum([rsi_momentum, macd_momentum, price_momentum])
        return positive_signals >= 2
    
    def check_market_sentiment(self, df: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #4: Market sentiment filter."""
        if len(df) < 20:
            return True
        
        # Volatility filter (avoid high volatility periods)
        volatility = df['close'].pct_change().rolling(20).std()
        low_volatility = volatility.iloc[-1] < volatility.quantile(0.7)
        
        # Trend strength filter
        adx = self.calculate_adx(df['high'], df['low'], df['close'], 14)
        strong_trend = adx.iloc[-1] > 25  # Relaxed from 30
        
        return low_volatility and strong_trend
    
    def check_entry_timing(self, df: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #5: Entry timing optimization."""
        if len(df) < 2:
            return True
        
        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        # Bullish engulfing pattern
        bullish_engulfing = (current_candle['close'] > prev_candle['open'] and
                            current_candle['open'] < prev_candle['close'] and
                            current_candle['close'] > prev_candle['close'])
        
        # Hammer pattern
        hammer = (current_candle['close'] > current_candle['open'] and
                  (current_candle['close'] - current_candle['low']) > 
                  2 * (current_candle['high'] - current_candle['close']))
        
        # Doji pattern (indecision)
        doji = abs(current_candle['close'] - current_candle['open']) / current_candle['open'] < 0.001
        
        return bullish_engulfing or hammer or doji
    
    def check_volume_confirmation(self, df: pd.DataFrame) -> bool:
        """WIN RATE IMPROVEMENT #6: Volume confirmation."""
        if len(df) < 20:
            return True
        
        avg_volume = df['volume'].rolling(20).mean()
        current_volume = df['volume'].iloc[-1]
        
        # Volume should be 1.2x average (relaxed from 1.5x)
        return current_volume > avg_volume.iloc[-1] * 1.2
    
    def optimize_risk_reward(self, entry_price: float, direction: str, df: pd.DataFrame) -> Tuple[float, float]:
        """WIN RATE IMPROVEMENT #7: Risk-reward optimization."""
        volatility = self.calculate_volatility(df, 20)
        
        if direction == 'LONG':
            if volatility > 0.02:  # High volatility
                take_profit = entry_price * 1.01  # 1% TP
                stop_loss = entry_price * 0.99    # 1% SL
            else:  # Normal volatility
                take_profit = entry_price * 1.015  # 1.5% TP
                stop_loss = entry_price * 0.985   # 1.5% SL
        else:
            if volatility > 0.02:  # High volatility
                take_profit = entry_price * 0.99  # 1% TP
                stop_loss = entry_price * 1.01    # 1% SL
            else:  # Normal volatility
                take_profit = entry_price * 0.985  # 1.5% TP
                stop_loss = entry_price * 1.015   # 1.5% SL
        
        return take_profit, stop_loss
    
    def optimize_position_sizing(self, score: float, volatility: float) -> float:
        """WIN RATE IMPROVEMENT #8: Position sizing optimization."""
        base_risk = self.risk_percent / 100
        
        # Adjust based on confidence score
        confidence_multiplier = min(2.0, score / 0.5)  # Max 2x for high confidence
        
        # Adjust based on volatility
        volatility_multiplier = max(0.5, 1.0 - volatility * 10)  # Reduce size in high volatility
        
        adjusted_risk = base_risk * confidence_multiplier * volatility_multiplier
        return min(5.0, adjusted_risk)  # Cap at 5% risk
    
    def generate_ultimate_signals(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Generate signals with ALL win rate improvements."""
        signals = []
        
        if len(df) < 100:
            return signals
        
        # Create 4H timeframe data
        df_4h = df.resample('4h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        print(f"🚀 ULTIMATE WIN RATE IMPROVEMENT ANALYSIS:")
        print(f"   📊 1H Data Points: {len(df)}")
        print(f"   📊 4H Data Points: {len(df_4h)}")
        
        # Track ALL filter effectiveness
        total_candidates = 0
        filters_passed = {
            'multi_timeframe': 0,
            'support_resistance': 0,
            'momentum': 0,
            'sentiment': 0,
            'entry_timing': 0,
            'volume': 0
        }
        final_signals = 0
        
        for i in range(100, len(df)):
            current = df.iloc[i]
            total_candidates += 1
            
            # ALL WIN RATE IMPROVEMENTS
            if self.multi_timeframe_required:
                if not self.check_multi_timeframe_trend(df.iloc[:i+1], df_4h):
                    continue
                filters_passed['multi_timeframe'] += 1
            
            if self.support_resistance_required:
                if not self.check_support_resistance(df.iloc[:i+1], current['close']):
                    continue
                filters_passed['support_resistance'] += 1
            
            if self.momentum_confirmation_required:
                if not self.check_momentum_confirmation(df.iloc[:i+1]):
                    continue
                filters_passed['momentum'] += 1
            
            if self.sentiment_filter_required:
                if not self.check_market_sentiment(df.iloc[:i+1]):
                    continue
                filters_passed['sentiment'] += 1
            
            if self.entry_timing_required:
                if not self.check_entry_timing(df.iloc[:i+1]):
                    continue
                filters_passed['entry_timing'] += 1
            
            if self.volume_confirmation_required:
                if not self.check_volume_confirmation(df.iloc[:i+1]):
                    continue
                filters_passed['volume'] += 1
            
            # Enhanced signal generation
            rsi_14 = self.calculate_rsi(df['close'], 14)
            rsi_21 = self.calculate_rsi(df['close'], 21)
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            
            # Ultimate signal scoring
            score = 0.4  # Base score
            
            # RSI signals
            if rsi_14.iloc[i] < 35 and rsi_21.iloc[i] < 40:
                score += 0.15
            elif rsi_14.iloc[i] > 65 and rsi_21.iloc[i] > 60:
                score -= 0.15
            
            # EMA trend signals
            if ema_12.iloc[i] > ema_26.iloc[i]:
                score += 0.15
            elif ema_12.iloc[i] < ema_26.iloc[i]:
                score -= 0.15
            
            # Volume bonus
            avg_volume = df['volume'].rolling(20).mean()
            if df['volume'].iloc[i] > avg_volume.iloc[i] * 1.2:
                score += 0.1
            
            # Momentum bonus
            if len(df) >= 5:
                price_change = (df['close'].iloc[i] - df['close'].iloc[i-5]) / df['close'].iloc[i-5]
                if price_change > 0.005:
                    score += 0.1
            
            # Generate signal if score is high enough
            if score >= self.min_score:
                direction = 'LONG' if score > 0.5 else 'SHORT'
                
                # WIN RATE IMPROVEMENT #7: Optimized risk-reward
                take_profit, stop_loss = self.optimize_risk_reward(current['close'], direction, df.iloc[:i+1])
                
                signals.append({
                    'id': len(signals) + 1,
                    'symbol': symbol,
                    'signal_type': 'ULTIMATE_WIN_RATE',
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
                        'sentiment_filter': True,
                        'entry_timing': True,
                        'volume_confirmation': True,
                        'risk_reward_optimization': True,
                        'position_sizing_optimization': True,
                        'exit_strategy_enhancement': True
                    }
                })
                final_signals += 1
        
        # Display comprehensive filter effectiveness
        print(f"   📊 ULTIMATE FILTER EFFECTIVENESS:")
        print(f"      Total Candidates: {total_candidates}")
        for filter_name, passed in filters_passed.items():
            percentage = (passed / total_candidates * 100) if total_candidates > 0 else 0
            print(f"      {filter_name.replace('_', ' ').title()}: {passed} ({percentage:.1f}%)")
        print(f"   ✅ ULTIMATE signals generated: {final_signals}")
        
        return signals
    
    def run_ultimate_backtest(self, symbol: str, start_date: datetime, end_date: datetime):
        """Run ultimate backtest with ALL win rate improvements."""
        print(f"🚀 ULTIMATE WIN RATE BACKTEST STARTING")
        print(f"   📈 Symbol: {symbol}")
        print(f"   📅 Period: {start_date} to {end_date}")
        print(f"   🎯 Target Win Rate: 60-70% (vs. current 28.6%)")
        print(f"   🔧 Strategy: ALL 9 win rate improvements")
        
        # Fetch data
        days = (end_date - start_date).days
        df = self.fetch_binance_data(symbol, days)
        
        if df.empty:
            print(f"❌ No data available for {symbol}")
            return
        
        print(f"📊 Data fetched: {len(df)} candles")
        
        # Generate ultimate signals
        signals = self.generate_ultimate_signals(df, symbol)
        
        if not signals:
            print("❌ No ultimate signals generated")
            return
        
        print(f"🎯 Ultimate signals: {len(signals)}")
        
        # Execute trades with ALL improvements
        for signal in signals:
            self.execute_ultimate_trade(signal, df)
        
        # Calculate results
        self.calculate_performance()
        
        # Display results
        self.display_ultimate_results()
    
    def execute_ultimate_trade(self, signal: Dict, df: pd.DataFrame):
        """Execute trade with ALL win rate improvements."""
        trade_id = len(self.trades) + 1
        entry_price = signal['entry_price']
        direction = signal['direction']
        score = signal['score']
        
        # WIN RATE IMPROVEMENT #8: Optimized position sizing
        volatility = self.calculate_volatility(df, 20)
        optimized_risk = self.optimize_position_sizing(score, volatility)
        
        # Position sizing
        risk_amount = self.balance * optimized_risk
        stop_loss = signal['stop_loss']
        risk_per_trade = abs(entry_price - stop_loss) / entry_price
        position_size = risk_amount / (risk_per_trade * entry_price)
        
        # Find exit with enhanced strategy
        exit_price, exit_reason = self.find_enhanced_exit(signal, df)
        
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
            'optimized_risk': optimized_risk,
            'win_rate_improvements': signal['win_rate_improvements']
        }
        
        self.trades.append(trade)
        self.equity_curve.append(self.balance)
        
        print(f"   📊 Trade {trade_id}: {direction} {signal['symbol']} @ {entry_price:.2f} → {exit_price:.2f} ({pnl*100:+.2f}%) [Risk: {optimized_risk:.1f}%]")
    
    def find_enhanced_exit(self, signal: Dict, df: pd.DataFrame) -> Tuple[float, str]:
        """WIN RATE IMPROVEMENT #9: Enhanced exit strategy."""
        entry_price = signal['entry_price']
        take_profit = signal['take_profit_1']
        stop_loss = signal['stop_loss']
        direction = signal['direction']
        
        # Find the candle after signal
        signal_time = signal['created_at']
        future_data = df[df.index > signal_time]
        
        if future_data.empty:
            return entry_price, 'NO_DATA'
        
        # Enhanced exit logic with trailing stops
        best_price = entry_price
        trailing_stop_distance = abs(entry_price - stop_loss) * 0.5  # 50% of initial stop distance
        
        for _, candle in future_data.iterrows():
            if direction == 'LONG':
                # Update trailing stop
                if candle['close'] > best_price:
                    best_price = candle['close']
                    new_trailing_stop = best_price - trailing_stop_distance
                    if new_trailing_stop > stop_loss:
                        stop_loss = new_trailing_stop
                
                # Check exits
                if candle['high'] >= take_profit:
                    return take_profit, 'TAKE_PROFIT'
                elif candle['low'] <= stop_loss:
                    return stop_loss, 'TRAILING_STOP' if stop_loss != signal['stop_loss'] else 'STOP_LOSS'
            else:
                # Update trailing stop for SHORT
                if candle['close'] < best_price:
                    best_price = candle['close']
                    new_trailing_stop = best_price + trailing_stop_distance
                    if new_trailing_stop < stop_loss:
                        stop_loss = new_trailing_stop
                
                # Check exits
                if candle['low'] <= take_profit:
                    return take_profit, 'TAKE_PROFIT'
                elif candle['high'] >= stop_loss:
                    return stop_loss, 'TRAILING_STOP' if stop_loss != signal['stop_loss'] else 'STOP_LOSS'
        
        # If no TP/SL hit, use last price
        return future_data['close'].iloc[-1], 'TIME_EXIT'
    
    def calculate_performance(self):
        """Calculate ultimate performance metrics."""
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
    
    def display_ultimate_results(self):
        """Display ultimate backtest results."""
        print(f"\n🎉 ULTIMATE WIN RATE BACKTEST RESULTS")
        print(f"=" * 60)
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
        
        print(f"\n🚀 ALL 9 WIN RATE IMPROVEMENTS APPLIED:")
        print(f"   ✅ Multi-timeframe confirmation")
        print(f"   ✅ Support/Resistance filtering")
        print(f"   ✅ Momentum confirmation")
        print(f"   ✅ Market sentiment filter")
        print(f"   ✅ Entry timing optimization")
        print(f"   ✅ Volume confirmation")
        print(f"   ✅ Risk-reward optimization")
        print(f"   ✅ Position sizing optimization")
        print(f"   ✅ Exit strategy enhancement")
        
        # Ultimate win rate analysis
        if self.win_rate > 70:
            print(f"\n🎉 OUTSTANDING! Win rate: {self.win_rate:.1f}% (Target: 60-70%)")
        elif self.win_rate > 60:
            print(f"\n🎉 EXCELLENT! Win rate: {self.win_rate:.1f}% (Target: 60-70%)")
        elif self.win_rate > 50:
            print(f"\n✅ VERY GOOD! Win rate: {self.win_rate:.1f}% (Close to target)")
        elif self.win_rate > 40:
            print(f"\n⚠️ GOOD: Win rate: {self.win_rate:.1f}% (Improving)")
        else:
            print(f"\n❌ Win rate: {self.win_rate:.1f}% (Needs more optimization)")

def main():
    """Run the ultimate win rate backtest."""
    backtest = UltimateWinRateBacktest()
    
    # Run ultimate backtest for BTC/USDT
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # 30 days
    
    backtest.run_ultimate_backtest('BTC/USDT', start_date, end_date)

if __name__ == "__main__":
    main()

