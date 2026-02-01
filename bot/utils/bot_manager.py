"""
Bot Management Utilities
Provides commands to start, stop, and monitor the trading bot
"""

import sys
import asyncio
import asyncpg
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Optional

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class BotManager:
    """Manages the automated trading bot lifecycle."""
    
    def __init__(self):
        self.bot_process = None
        self.dashboard_process = None
    
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def start_bot(self, test_mode: bool = True):
        """Start the trading bot."""
        try:
            logger.info("🤖 Starting automated trading bot...")
            
            # Check if bot is already running
            if self.is_bot_running():
                logger.warning("⚠️ Bot is already running")
                return False
            
            # Start bot process
            cmd = ["python", "core/trading_bot.py"]
            env = {
                "BOT_TEST_MODE": str(test_mode).lower(),
                "PYTHONPATH": "/app:/packages"
            }
            
            self.bot_process = subprocess.Popen(
                cmd,
                env={**env, **subprocess.os.environ},
                cwd="/app"
            )
            
            logger.info(f"✅ Bot started with PID: {self.bot_process.pid}")
            logger.info(f"🔧 Test mode: {test_mode}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            return False
    
    async def stop_bot(self):
        """Stop the trading bot."""
        try:
            logger.info("🛑 Stopping automated trading bot...")
            
            if self.bot_process:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
                logger.info("✅ Bot stopped")
                return True
            else:
                logger.warning("⚠️ Bot process not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error stopping bot: {e}")
            return False
    
    async def restart_bot(self, test_mode: bool = True):
        """Restart the trading bot."""
        logger.info("🔄 Restarting automated trading bot...")
        
        await self.stop_bot()
        await asyncio.sleep(2)  # Wait for cleanup
        return await self.start_bot(test_mode)
    
    def is_bot_running(self) -> bool:
        """Check if bot is running."""
        if self.bot_process:
            return self.bot_process.poll() is None
        return False
    
    async def get_bot_status(self) -> Dict:
        """Get current bot status."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get bot statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades,
                    COALESCE(SUM(realized_pnl), 0) as total_pnl,
                    COUNT(CASE WHEN is_open = true THEN 1 END) as open_positions
                FROM paper_positions
            """)
            
            # Get recent activity
            recent_trades = await conn.fetch("""
                SELECT symbol, side, realized_pnl, created_at
                FROM paper_positions 
                WHERE is_open = false
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            # Get open positions
            open_positions = await conn.fetch("""
                SELECT symbol, side, entry_price, current_price, unrealized_pnl
                FROM paper_positions 
                WHERE is_open = true
                ORDER BY created_at DESC
            """)
            
            win_rate = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
            
            return {
                "is_running": self.is_bot_running(),
                "pid": self.bot_process.pid if self.bot_process else None,
                "stats": {
                    "total_trades": stats['total_trades'],
                    "winning_trades": stats['winning_trades'],
                    "win_rate": win_rate,
                    "total_pnl": float(stats['total_pnl']),
                    "open_positions": stats['open_positions']
                },
                "recent_trades": [dict(trade) for trade in recent_trades],
                "open_positions": [dict(pos) for pos in open_positions]
            }
            
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                await conn.close()
    
    async def emergency_stop(self):
        """Emergency stop - close all positions and stop bot."""
        logger.warning("🚨 EMERGENCY STOP ACTIVATED!")
        
        try:
            conn = await self.connect_db()
            
            # Close all open positions
            await conn.execute("""
                UPDATE paper_positions 
                SET is_open = false, closed_at = $1, updated_at = $2
                WHERE is_open = true
            """, datetime.utcnow(), datetime.utcnow())
            
            await conn.close()
            
            # Stop the bot
            await self.stop_bot()
            
            logger.warning("🚨 Emergency stop completed - all positions closed")
            return True
            
        except Exception as e:
            logger.error(f"Error in emergency stop: {e}")
            return False
    
    async def get_performance_report(self) -> Dict:
        """Generate performance report."""
        conn = None
        try:
            conn = await self.connect_db()
            
            # Get performance metrics
            performance = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as winning_trades,
                    COALESCE(SUM(realized_pnl), 0) as total_pnl,
                    COALESCE(AVG(realized_pnl), 0) as avg_pnl,
                    COALESCE(MAX(realized_pnl), 0) as best_trade,
                    COALESCE(MIN(realized_pnl), 0) as worst_trade,
                    COALESCE(STDDEV(realized_pnl), 0) as pnl_stddev
                FROM paper_positions 
                WHERE is_open = false
            """)
            
            # Get daily performance
            daily_performance = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as trades,
                    SUM(realized_pnl) as daily_pnl
                FROM paper_positions 
                WHERE is_open = false
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 7
            """)
            
            # Get symbol performance
            symbol_performance = await conn.fetch("""
                SELECT 
                    symbol,
                    COUNT(*) as trades,
                    SUM(realized_pnl) as total_pnl,
                    AVG(realized_pnl) as avg_pnl
                FROM paper_positions 
                WHERE is_open = false
                GROUP BY symbol
                ORDER BY total_pnl DESC
            """)
            
            win_rate = (performance['winning_trades'] / performance['total_trades'] * 100) if performance['total_trades'] > 0 else 0
            
            return {
                "overview": {
                    "total_trades": performance['total_trades'],
                    "winning_trades": performance['winning_trades'],
                    "win_rate": win_rate,
                    "total_pnl": float(performance['total_pnl']),
                    "avg_pnl": float(performance['avg_pnl']),
                    "best_trade": float(performance['best_trade']),
                    "worst_trade": float(performance['worst_trade']),
                    "pnl_volatility": float(performance['pnl_stddev'])
                },
                "daily_performance": [dict(day) for day in daily_performance],
                "symbol_performance": [dict(symbol) for symbol in symbol_performance]
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                await conn.close()


async def main():
    """Main function for bot management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trading Bot Manager")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "emergency-stop", "report"])
    parser.add_argument("--test-mode", action="store_true", default=True, help="Run in test mode")
    parser.add_argument("--live-mode", action="store_true", help="Run in live mode")
    
    args = parser.parse_args()
    
    manager = BotManager()
    
    if args.command == "start":
        test_mode = not args.live_mode
        await manager.start_bot(test_mode)
    elif args.command == "stop":
        await manager.stop_bot()
    elif args.command == "restart":
        test_mode = not args.live_mode
        await manager.restart_bot(test_mode)
    elif args.command == "status":
        status = await manager.get_bot_status()
        print(json.dumps(status, indent=2))
    elif args.command == "emergency-stop":
        await manager.emergency_stop()
    elif args.command == "report":
        report = await manager.get_performance_report()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
















