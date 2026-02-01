"""
Main Automated Trading Bot
Orchestrates signal selection, risk management, and execution
"""

import sys
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import time

# Add packages to path
sys.path.append('/packages')

from common.config import get_settings
from common.logging import get_logger

# Import bot components
from signal_selector import BestSignalSelector
from risk_manager import RiskManager
from execution.binance_executor import BinanceExecutor
from execution.dual_executor import DualTradingExecutor
from services.binance_position_sync import BinancePositionSync

settings = get_settings()
logger = get_logger(__name__)


class AutomatedTradingBot:
    """Main automated trading bot that orchestrates all components."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.is_running = False
        self.last_signal_time = None
        self.cooldown_minutes = 30  # Wait 30 minutes between signal checks to prevent rapid execution
        
        # Initialize components
        self.signal_selector = BestSignalSelector()
        self.risk_manager = RiskManager()
        # Use DualTradingExecutor for both spot and futures trading
        self.executor = DualTradingExecutor(test_mode=test_mode)
        
        # Initialize position sync service (only in live mode)
        self.position_sync = BinancePositionSync() if not test_mode else None
        self.sync_task = None
        
        # Bot statistics
        self.stats = {
            "signals_processed": 0,
            "trades_executed": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_pnl": 0.0,
            "start_time": None
        }
    
    async def connect_db(self):
        """Connect to database."""
        return await asyncpg.connect(
            host='winu-bot-signal-postgres',
            port=5432,
            user='winu',
            password='winu250420',
            database='winudb'
        )
    
    async def start_bot(self):
        """Start the automated trading bot."""
        try:
            logger.info("🤖 Starting Automated Trading Bot...")
            logger.info(f"🔧 Mode: {'TEST' if self.test_mode else 'LIVE'}")
            
            self.is_running = True
            self.stats["start_time"] = datetime.utcnow()
            
            # Initial system checks
            await self.perform_system_checks()
            
            # Start position sync in background (only in LIVE mode)
            if self.position_sync:
                self.sync_task = asyncio.create_task(
                    self.position_sync.run_continuous_sync(interval_seconds=300)  # Every 5 minutes
                )
                logger.info("🔄 Auto-sync started: Binance positions will sync every 5 minutes")
            
            # Start main trading loop
            await self.trading_loop()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            self.is_running = False
        finally:
            # Stop position sync
            if self.position_sync:
                self.position_sync.stop()
                if self.sync_task:
                    self.sync_task.cancel()
                    try:
                        await self.sync_task
                    except asyncio.CancelledError:
                        pass
                logger.info("⏹️ Auto-sync stopped")
            
            logger.info("🛑 Bot stopped")
    
    async def perform_system_checks(self):
        """Perform initial system checks."""
        logger.info("🔍 Performing system checks...")
        
        # Check database connection
        try:
            conn = await self.connect_db()
            await conn.close()
            logger.info("✅ Database connection: OK")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
        
        # Check account balance
        try:
            balance = await self.executor.get_account_balance()
            logger.info(f"✅ Account balance: {balance['free_balance']:.2f} {balance['currency']}")
        except Exception as e:
            logger.error(f"❌ Account balance check failed: {e}")
            raise
        
        # Check risk parameters
        try:
            daily_check = await self.risk_manager.check_daily_loss_limits()
            position_check = await self.risk_manager.check_position_limits()
            emergency_check = await self.risk_manager.check_emergency_conditions()
            
            if not daily_check.get('can_trade', False):
                logger.warning("⚠️ Daily loss limit reached")
            if not position_check.get('can_trade', False):
                logger.warning("⚠️ Position limit reached")
            if not emergency_check.get('can_trade', False):
                logger.warning("⚠️ Emergency conditions detected")
            
            logger.info("✅ Risk management: OK")
        except Exception as e:
            logger.error(f"❌ Risk management check failed: {e}")
            raise
        
        logger.info("🎉 All system checks passed!")
    
    async def trading_loop(self):
        """Main trading loop."""
        logger.info("🔄 Starting trading loop...")
        
        while self.is_running:
            try:
                # Check if we should look for new signals
                if self.should_check_for_signals():
                    await self.process_trading_cycle()
                else:
                    logger.info("⏳ Waiting for next signal check...")
                
                # Monitor existing positions
                await self.monitor_positions()
                
                # Update statistics
                await self.update_statistics()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    def should_check_for_signals(self) -> bool:
        """Check if we should look for new signals."""
        if not self.last_signal_time:
            return True
        
        time_since_last = datetime.utcnow() - self.last_signal_time
        return time_since_last.total_seconds() > (self.cooldown_minutes * 60)
    
    async def process_trading_cycle(self):
        """Process one complete trading cycle."""
        try:
            logger.info("🔍 Processing trading cycle...")
            
            # Select best signal
            best_signal = await self.signal_selector.select_best_signal()
            
            if not best_signal:
                logger.info("ℹ️ No suitable signals found")
                return
            
            logger.info(f"📊 Best signal selected: {best_signal['symbol']} {best_signal['direction']}")
            
            # Validate trade with risk management
            validation = await self.risk_manager.validate_trade(best_signal)
            
            # Override risk checks for exceptional signals
            if not validation.get('can_trade', False) and best_signal.get('quality_score', 0) > 0.95:
                logger.info("🎯 Exceptional signal detected (quality > 0.95) - overriding risk checks")
                validation = {"can_trade": True, "reason": "Exceptional quality override"}
            
            if not validation.get('can_trade', False):
                logger.warning(f"⚠️ Trade validation failed: {validation.get('reason', 'Unknown')}")
                return
            
            logger.info("✅ Trade validation passed")
            
            # Mark signal as being executed to prevent duplicates
            await self.signal_selector.mark_signal_for_execution(best_signal['id'])
            
            execution_success = False
            
            # ===== Multi-Account Trading Integration =====
            # First, try environment-based multi-account executor (production.env)
            multi_account_attempted = False
            try:
                logger.info("🚀 Executing signal on multi-account system (environment-based)...")
                from execution.env_multi_account_executor import get_env_multi_account_executor
                
                # Get environment-based multi-account executor
                env_executor = get_env_multi_account_executor(test_mode=self.test_mode)
                
                # Check if we have multiple accounts configured
                if env_executor.get_account_count() > 0:
                    # Execute on all accounts from environment
                    multi_result = await env_executor.execute_signal_on_all_accounts(best_signal)
                    multi_account_attempted = True  # Mark that we attempted multi-account execution
                    
                    if multi_result.get('success', False) or multi_result.get('successful_accounts', 0) > 0:
                        logger.info(f"✅ Multi-account execution: {multi_result['successful_accounts']}/{multi_result['total_accounts']} accounts")
                        
                        # Update bot stats
                        self.stats["signals_processed"] += 1
                        self.stats["trades_executed"] += multi_result['successful_accounts']
                        self.stats["successful_trades"] += multi_result['successful_accounts']
                        self.stats["failed_trades"] += multi_result['failed_accounts']
                        
                        self.last_signal_time = datetime.utcnow()
                        execution_success = True
                        
                        return multi_result
                    else:
                        logger.warning(f"⚠️ Multi-account execution failed: {multi_result.get('error', 'Unknown')}")
                        logger.warning(f"⚠️ Skipping fallback to prevent duplicate execution")
                        self.stats["failed_trades"] += 1
                        execution_success = True  # Mark as handled to prevent fallback
                        return multi_result
                else:
                    logger.info("No accounts found in environment, trying database multi-account system...")
                
            except Exception as env_error:
                logger.error(f"❌ Environment-based multi-account execution error: {env_error}")
                if not multi_account_attempted:
                    logger.info("Trying database multi-account system...")
                else:
                    logger.info("Multi-account was attempted but errored, skipping fallback to prevent duplicates")
                    execution_success = True
            
            # Second, try database-based multi-account system (UI configured)
            # Only try if environment-based multi-account was not attempted
            if not multi_account_attempted:
                try:
                    logger.info("🚀 Executing signal on multi-account system (database)...")
                    from execution.multi_account_manager import get_multi_account_manager
                    
                    # Get multi-account manager
                    manager = await get_multi_account_manager()
                    
                    # Execute on all active accounts
                    multi_result = await manager.execute_signal_on_all_accounts(best_signal)
                    multi_account_attempted = True  # Mark that we attempted multi-account execution
                    
                    if multi_result.get('success', False) or multi_result.get('successful_accounts', 0) > 0:
                        logger.info(f"✅ Multi-account execution: {multi_result['successful_accounts']}/{multi_result['total_accounts']} accounts")
                        
                        # Update bot stats
                        self.stats["signals_processed"] += 1
                        self.stats["trades_executed"] += multi_result['successful_accounts']
                        self.stats["successful_trades"] += multi_result['successful_accounts']
                        self.stats["failed_trades"] += multi_result['failed_accounts']
                        
                        self.last_signal_time = datetime.utcnow()
                        execution_success = True
                        
                        return multi_result
                    else:
                        logger.warning(f"⚠️ Multi-account execution failed: {multi_result.get('error', 'Unknown')}")
                        logger.warning(f"⚠️ Skipping fallback to prevent duplicate execution")
                        self.stats["failed_trades"] += 1
                        execution_success = True  # Mark as handled to prevent fallback
                        return multi_result
                    
                except Exception as multi_error:
                    logger.error(f"❌ Multi-account execution error: {multi_error}")
                    if multi_account_attempted:
                        logger.info("Multi-account was attempted but errored, skipping fallback to prevent duplicates")
                        execution_success = True
                    else:
                        logger.info("Falling back to single-account execution...")
            
            # ===== Fallback to Original Single-Account Execution =====
            # Only execute if multi-account systems failed
            if not execution_success:
                logger.info("🔄 Falling back to single-account execution...")
                execution_result = await self.executor.execute_signal(best_signal)
                
                if execution_result.get('success', False):
                    logger.info(f"🎉 Trade executed successfully: {execution_result['order_id']}")
                    self.stats["trades_executed"] += 1
                    self.stats["successful_trades"] += 1
                    
                else:
                    logger.error(f"❌ Trade execution failed: {execution_result.get('error', 'Unknown error')}")
                    self.stats["failed_trades"] += 1
            
            self.stats["signals_processed"] += 1
            self.last_signal_time = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    async def monitor_positions(self):
        """Monitor all open positions."""
        try:
            positions = await self.executor.monitor_positions()
            
            if positions:
                logger.info(f"📊 Monitoring {len(positions)} open positions")
                
                total_unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions)
                self.stats["total_pnl"] = total_unrealized_pnl
                
                for pos in positions:
                    pnl_status = "📈" if pos['unrealized_pnl'] > 0 else "📉"
                    logger.info(f"   {pnl_status} {pos['symbol']} {pos['side']}: {pos['unrealized_pnl']:.2f} USDT ({pos['pnl_percentage']:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    async def update_statistics(self):
        """Update bot statistics."""
        try:
            conn = await self.connect_db()
            
            # Get total realized PnL
            total_realized_pnl = await conn.fetchval("""
                SELECT COALESCE(SUM(realized_pnl), 0) 
                FROM paper_positions 
                WHERE is_open = false
            """)
            
            # Get win rate
            total_trades = await conn.fetchval("""
                SELECT COUNT(*) FROM paper_positions WHERE is_open = false
            """)
            
            winning_trades = await conn.fetchval("""
                SELECT COUNT(*) FROM paper_positions 
                WHERE is_open = false AND realized_pnl > 0
            """)
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            self.stats.update({
                "total_realized_pnl": float(total_realized_pnl),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": win_rate
            })
            
            await conn.close()
            
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
    
    async def get_bot_status(self) -> Dict:
        """Get current bot status."""
        return {
            "is_running": self.is_running,
            "test_mode": self.test_mode,
            "stats": self.stats,
            "last_signal_time": self.last_signal_time.isoformat() if self.last_signal_time else None,
            "uptime": (datetime.utcnow() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        }
    
    async def stop_bot(self):
        """Stop the trading bot."""
        logger.info("🛑 Stopping trading bot...")
        self.is_running = False
    
    async def emergency_stop(self):
        """Emergency stop - close all positions and stop trading."""
        logger.warning("🚨 EMERGENCY STOP ACTIVATED!")
        
        try:
            # Close all open positions
            conn = await self.connect_db()
            open_positions = await conn.fetch("""
                SELECT id FROM paper_positions WHERE is_open = true
            """)
            
            for position in open_positions:
                await self.executor.close_position(position['id'], "emergency_stop")
            
            await conn.close()
            
            # Stop the bot
            await self.stop_bot()
            
            logger.warning("🚨 Emergency stop completed - all positions closed")
            
        except Exception as e:
            logger.error(f"Error in emergency stop: {e}")


async def main():
    """Main function to run the trading bot."""
    import os
    test_mode = os.getenv('BOT_TEST_MODE', 'true').lower() == 'true'
    bot = AutomatedTradingBot(test_mode=test_mode)
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        await bot.stop_bot()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        await bot.emergency_stop()


if __name__ == "__main__":
    asyncio.run(main())






