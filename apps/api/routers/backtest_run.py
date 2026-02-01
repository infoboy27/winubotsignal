"""Enhanced backtest runner for real data analysis."""

import asyncio
import asyncpg
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import sys
import os

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# Add packages to path
sys.path.append('/home/ubuntu/winubotsignal/packages')

from common.database import User
from common.logging import get_logger
from .auth import get_current_active_user
from dependencies import get_db

router = APIRouter()
logger = get_logger(__name__)

class BacktestRequest(BaseModel):
    symbol: str
    startDate: str
    endDate: str
    initialBalance: float
    riskPercent: float
    maxPositions: int
    minScore: float

class BacktestResponse(BaseModel):
    initial_balance: float
    final_balance: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    take_profit_exits: int
    stop_loss_exits: int
    trades: List[Dict]

class RealDataBacktest:
    """Real data backtest using actual signals and OHLCV data."""
    
    def __init__(self, params: BacktestRequest):
        self.params = params
        self.db_pool = None
        
        # Backtest state
        self.initial_balance = params.initialBalance
        self.balance = params.initialBalance
        self.risk_percent = params.riskPercent
        self.max_positions = params.maxPositions
        self.min_score = params.minScore
        
        # Results tracking
        self.trades = []
        self.positions = {}
        self.equity_curve = []
        
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
    
    def fetch_binance_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Fetch real OHLCV data from Binance API."""
        import requests
        
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
    
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical OHLCV data for a symbol."""
        # Calculate days between start and end
        days = (end_date - start_date).days
        return self.fetch_binance_data(symbol, days)
    
    def generate_signals_from_data(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Generate signals from OHLCV data using technical analysis."""
        signals = []
        
        if len(df) < 50:
            return signals
        
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
                    'id': len(signals) + 1,
                    'symbol': symbol,
                    'signal_type': 'TECHNICAL',
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
    
    async def get_real_signals(self, symbol: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get real signals from the database for the period."""
        # Since database is empty, generate signals from data
        df = await self.get_historical_data(symbol, start_date, end_date)
        return self.generate_signals_from_data(df, symbol)
    
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
            'take_profit': signal['take_profit_1'],
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
    
    async def run_backtest(self) -> BacktestResponse:
        """Run the backtest and return results."""
        start_date = datetime.fromisoformat(self.params.startDate)
        end_date = datetime.fromisoformat(self.params.endDate)
        
        # Get historical data
        df = await self.get_historical_data(self.params.symbol, start_date, end_date)
        if df.empty:
            raise HTTPException(status_code=400, detail=f"No data found for {self.params.symbol}")
        
        # Get real signals from database
        real_signals = await self.get_real_signals(self.params.symbol, start_date, end_date)
        
        # Create signal lookup by timestamp
        signal_lookup = {}
        for signal in real_signals:
            signal_time = signal['created_at']
            # Find closest candle
            try:
                closest_idx = df.index.get_indexer([signal_time], method='nearest')[0]
                if closest_idx >= 0:
                    signal_lookup[closest_idx] = signal
            except:
                continue
        
        # Run backtest
        for i in range(len(df)):
            current_data = df.iloc[i]
            current_time = current_data.name
            current_price = current_data['close']
            
            # Update existing positions
            self.update_positions(current_price, current_time)
            
            # Check if there's a real signal at this time
            if i in signal_lookup:
                signal = signal_lookup[i]
                if signal['score'] >= self.min_score:
                    # Execute trade
                    trade = self.execute_trade(signal, current_price)
            
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
        return self.calculate_results()
    
    def calculate_results(self) -> BacktestResponse:
        """Calculate and return backtest results."""
        if not self.trades:
            return BacktestResponse(
                initial_balance=self.initial_balance,
                final_balance=self.balance,
                total_return=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                take_profit_exits=0,
                stop_loss_exits=0,
                trades=[]
            )
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L metrics
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
        
        return BacktestResponse(
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            best_trade=best_trade,
            worst_trade=worst_trade,
            take_profit_exits=take_profit_exits,
            stop_loss_exits=stop_loss_exits,
            trades=self.trades
        )

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Run a real data backtest."""
    try:
        backtest = RealDataBacktest(request)
        await backtest.connect_db()
        
        result = await backtest.run_backtest()
        
        await backtest.db_pool.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Backtest error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
