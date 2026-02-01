"""
Trading History Scheduler
Scheduled tasks to fetch and store trading history from Binance
"""

import asyncio
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Add packages to path
sys.path.append('/packages')

from services.trading_history_service import TradingHistoryService
from common.logging import get_logger

logger = get_logger(__name__)


class TradingHistoryScheduler:
    """Scheduler for trading history tasks."""
    
    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.scheduler = AsyncIOScheduler()
        self.history_service = TradingHistoryService(test_mode=test_mode)
    
    async def fetch_and_store_all_data(self):
        """Fetch and store all trading data."""
        try:
            logger.info("🔄 Starting scheduled trading history fetch...")
            
            # Fetch and store futures trades (last 3 days)
            futures_result = await self.history_service.fetch_and_store_futures_trades(days=3)
            logger.info(f"📈 Futures trades result: {futures_result}")
            
            # Fetch and store spot trades (last 3 days)
            spot_result = await self.history_service.fetch_and_store_spot_trades(days=3)
            logger.info(f"💱 Spot trades result: {spot_result}")
            
            # Store current account balance
            balance_result = await self.history_service.store_account_balance()
            logger.info(f"💰 Account balance result: {balance_result}")
            
            # Calculate daily PNL for yesterday and today
            yesterday = datetime.now().date() - timedelta(days=1)
            today = datetime.now().date()
            
            yesterday_pnl = await self.history_service.calculate_daily_pnl(yesterday)
            today_pnl = await self.history_service.calculate_daily_pnl(today)
            
            logger.info(f"📊 Yesterday PNL: {yesterday_pnl}")
            logger.info(f"📊 Today PNL: {today_pnl}")
            
            logger.info("✅ Scheduled trading history fetch completed!")
            
        except Exception as e:
            logger.error(f"❌ Error in scheduled trading history fetch: {e}")
    
    async def hourly_balance_update(self):
        """Update account balances every hour."""
        try:
            logger.info("🔄 Updating account balances...")
            result = await self.history_service.store_account_balance()
            logger.info(f"💰 Balance update result: {result}")
        except Exception as e:
            logger.error(f"❌ Error updating balances: {e}")
    
    async def daily_pnl_calculation(self):
        """Calculate daily PNL every day at midnight."""
        try:
            logger.info("🔄 Calculating daily PNL...")
            yesterday = datetime.now().date() - timedelta(days=1)
            result = await self.history_service.calculate_daily_pnl(yesterday)
            logger.info(f"📊 Daily PNL calculation result: {result}")
        except Exception as e:
            logger.error(f"❌ Error calculating daily PNL: {e}")
    
    def start_scheduler(self):
        """Start the scheduler with all tasks."""
        try:
            # Fetch trading data every 4 hours
            self.scheduler.add_job(
                self.fetch_and_store_all_data,
                CronTrigger(hour='0,4,8,12,16,20', minute=0),
                id='fetch_trading_data',
                name='Fetch and store trading data',
                replace_existing=True
            )
            
            # Update balances every hour
            self.scheduler.add_job(
                self.hourly_balance_update,
                CronTrigger(minute=0),
                id='update_balances',
                name='Update account balances',
                replace_existing=True
            )
            
            # Calculate daily PNL at midnight
            self.scheduler.add_job(
                self.daily_pnl_calculation,
                CronTrigger(hour=0, minute=1),
                id='calculate_daily_pnl',
                name='Calculate daily PNL',
                replace_existing=True
            )
            
            # Run initial data fetch
            asyncio.create_task(self.fetch_and_store_all_data())
            
            self.scheduler.start()
            logger.info("🚀 Trading history scheduler started successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading history scheduler: {e}")
            raise
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 Trading history scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {e}")


async def main():
    """Main function to run the scheduler."""
    scheduler = TradingHistoryScheduler(test_mode=True)
    
    try:
        scheduler.start_scheduler()
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal")
    finally:
        scheduler.stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())












