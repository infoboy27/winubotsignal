"""
Advanced Signal Selector for Automated Trading Bot
Selects only the highest quality signals for execution
"""

import sys
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class BestSignalSelector:
    """Selects only the best signals for automated trading."""
    
    def __init__(self):
        self.min_score = 0.80  # Only execute 80%+ confidence signals (HIGH confidence only)
        self.max_daily_signals = 6  # Maximum 6 trades per day (8am, 12pm, 2pm, 4pm, 8pm, 12am)
        self.cooldown_hours = 2  # Wait 2 hours between signals for same symbol
        self.min_volume_24h = 1000000  # Minimum 24h volume (USD)
        self.max_volatility = 0.15  # Maximum 15% daily volatility
        
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def get_recent_performance(self, symbol: str, days: int = 7) -> Dict:
        """Get recent performance for a symbol."""
        conn = None
        try:
            conn = await self.connect_db()
            
            since = datetime.utcnow() - timedelta(days=days)
            
            # Get performance metrics
            metrics = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades,
                    AVG(realized_pnl) as avg_pnl,
                    AVG(score) as avg_score
                FROM signals 
                WHERE symbol = $1 AND created_at >= $2 AND realized_pnl != 0
            """, symbol, since)
            
            if not metrics or metrics['total_trades'] < 3:
                return {"win_rate": 0, "avg_pnl": 0, "total_trades": 0}
            
            win_rate = (metrics['winning_trades'] / metrics['total_trades']) * 100
            
            return {
                "win_rate": win_rate,
                "avg_pnl": float(metrics['avg_pnl']) if metrics['avg_pnl'] else 0,
                "total_trades": metrics['total_trades'],
                "avg_score": float(metrics['avg_score']) if metrics['avg_score'] else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting performance for {symbol}: {e}")
            return {"win_rate": 0, "avg_pnl": 0, "total_trades": 0}
        finally:
            if conn:
                await conn.close()
    
    async def check_trading_limits(self) -> Dict:
        """Check if we can execute more trades today."""
        conn = None
        try:
            conn = await self.connect_db()
            
            today = datetime.utcnow().date()
            
            # Count signals executed today
            today_signals = await conn.fetchval("""
                SELECT COUNT(*) FROM signals 
                WHERE DATE(created_at) = $1 AND is_active = false
            """, today)
            
            # Count active positions
            active_positions = await conn.fetchval("""
                SELECT COUNT(*) FROM paper_positions 
                WHERE is_open = true
            """)
            
            return {
                "can_trade": today_signals < self.max_daily_signals and active_positions < 10,
                "today_signals": today_signals,
                "active_positions": active_positions,
                "max_daily": self.max_daily_signals,
                "max_positions": 10
            }
            
        except Exception as e:
            logger.error(f"Error checking trading limits: {e}")
            return {"can_trade": False, "error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def get_market_conditions(self, symbol: str) -> Dict:
        """Get current market conditions for a symbol."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get latest OHLCV data
            latest_data = await conn.fetchrow("""
                SELECT open, high, low, close, volume, timestamp
                FROM ohlcv 
                WHERE symbol = $1 AND timeframe = 'ONE_DAY'
                ORDER BY timestamp DESC 
                LIMIT 1
            """, symbol)
            
            if not latest_data:
                return {"volatility": 0, "volume_24h": 0, "trend": "unknown"}
            
            # Calculate volatility (simplified)
            high = float(latest_data['high'])
            low = float(latest_data['low'])
            volatility = (high - low) / low if low > 0 else 0
            
            # Get volume
            volume_24h = float(latest_data['volume']) * float(latest_data['close'])
            
            # Determine trend
            trend = "bullish" if high > low * 1.02 else "bearish" if low < high * 0.98 else "sideways"
            
            return {
                "volatility": volatility,
                "volume_24h": volume_24h,
                "trend": trend,
                "price": float(latest_data['close'])
            }
            
        except Exception as e:
            logger.error(f"Error getting market conditions for {symbol}: {e}")
            return {"volatility": 0, "volume_24h": 0, "trend": "unknown"}
        finally:
            if conn:
                await conn.close()
    
    def calculate_signal_quality_score(self, signal: Dict, performance: Dict, market: Dict) -> float:
        """Calculate overall quality score for a signal."""
        base_score = signal.get('score', 0)
        
        # Performance bonus
        performance_bonus = 0
        if performance['win_rate'] > 60:
            performance_bonus = 0.1
        elif performance['win_rate'] > 50:
            performance_bonus = 0.05
        
        # Market conditions bonus
        market_bonus = 0
        if market['volatility'] < 0.1 and market['volume_24h'] > self.min_volume_24h:
            market_bonus = 0.05
        
        # Trend alignment bonus
        trend_bonus = 0
        if signal.get('direction') == 'LONG' and market['trend'] == 'bullish':
            trend_bonus = 0.05
        elif signal.get('direction') == 'SHORT' and market['trend'] == 'bearish':
            trend_bonus = 0.05
        
        total_score = base_score + performance_bonus + market_bonus + trend_bonus
        return min(1.0, total_score)  # Cap at 1.0
    
    async def select_best_signal(self) -> Optional[Dict]:
        """Select the single best signal for execution."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Check trading limits
            limits = await self.check_trading_limits()
            if not limits.get('can_trade', False):
                logger.info(f"Trading limits reached: {limits}")
                return None
            
            # Get recent high-quality signals - avoid symbols with existing positions or recently executed
            # Handle both symbol formats: 'BTC/USDT' and 'BTC/USDT:USDT'
            recent_signals = await conn.fetch("""
                SELECT s.id, s.symbol, s.direction, s.score, s.entry_price, s.take_profit_1, s.stop_loss, 
                       s.created_at, s.confluences, s.context
                FROM signals s
                WHERE s.is_active = true 
                AND s.score >= $1
                AND s.created_at >= NOW() - INTERVAL '24 hours'
                AND s.symbol NOT IN (
                    SELECT DISTINCT REPLACE(symbol, ':USDT', '') 
                    FROM paper_positions 
                    WHERE is_open = true
                )
                AND s.symbol NOT IN (
                    SELECT DISTINCT symbol FROM signals 
                    WHERE is_executed = true 
                    AND created_at >= NOW() - INTERVAL '2 hours'
                )
                ORDER BY s.score DESC, s.created_at DESC
                LIMIT 10
            """, self.min_score)
            
            if not recent_signals:
                logger.info("No high-quality signals available")
                return None
            
            best_signal = None
            best_score = 0
            
            for signal in recent_signals:
                signal_dict = dict(signal)
                
                # Get performance data
                performance = await self.get_recent_performance(signal_dict['symbol'])
                
                # Get market conditions
                market = await self.get_market_conditions(signal_dict['symbol'])
                
                # Calculate quality score
                quality_score = self.calculate_signal_quality_score(
                    signal_dict, performance, market
                )
                
                # Check if this is the best signal so far
                if quality_score > best_score:
                    # Additional checks
                    if (market['volatility'] <= self.max_volatility and 
                        market['volume_24h'] >= self.min_volume_24h):
                        
                        best_signal = signal_dict
                        best_score = quality_score
                        best_signal['quality_score'] = quality_score
                        best_signal['performance'] = performance
                        best_signal['market'] = market
            
            if best_signal:
                logger.info(f"Selected best signal: {best_signal['symbol']} {best_signal['direction']}")
                logger.info(f"Quality score: {best_signal['quality_score']:.3f}")
                logger.info(f"Performance: {best_signal['performance']['win_rate']:.1f}% win rate")
                logger.info(f"Market: {best_signal['market']['trend']} trend, {best_signal['market']['volatility']:.1%} volatility")
            
            return best_signal
            
        except Exception as e:
            logger.error(f"Error selecting best signal: {e}")
            return None
        finally:
            if conn:
                await conn.close()
    
    async def mark_signal_for_execution(self, signal_id: int) -> bool:
        """Mark a signal as selected for execution."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Update signal with execution metadata
            # Fix: Use proper type casting for jsonb column
            await conn.execute("""
                UPDATE signals 
                SET context = COALESCE(context::jsonb, '{}'::jsonb) || '{"bot_selected": true}'::jsonb
                WHERE id = $1
            """, signal_id)
            
            logger.info(f"Marked signal {signal_id} for execution")
            return True
            
        except Exception as e:
            logger.error(f"Error marking signal for execution: {e}")
            return False
        finally:
            if conn:
                await conn.close()


async def main():
    """Test the signal selector."""
    selector = BestSignalSelector()
    
    print("🔍 Testing Best Signal Selector...")
    
    # Check trading limits
    limits = await selector.check_trading_limits()
    print(f"📊 Trading Limits: {limits}")
    
    # Select best signal
    best_signal = await selector.select_best_signal()
    
    if best_signal:
        print(f"\n✅ Best Signal Selected:")
        print(f"   Symbol: {best_signal['symbol']}")
        print(f"   Direction: {best_signal['direction']}")
        print(f"   Score: {best_signal['score']:.2f}")
        print(f"   Quality Score: {best_signal['quality_score']:.3f}")
        print(f"   Entry Price: ${best_signal['entry_price']:.2f}")
        print(f"   Take Profit: ${best_signal['take_profit_1']:.2f}")
        print(f"   Stop Loss: ${best_signal['stop_loss']:.2f}")
    else:
        print("\n❌ No suitable signals found")


if __name__ == "__main__":
    asyncio.run(main())
