#!/usr/bin/env python3
"""
Test script for trading history functionality
"""

import asyncio
import sys
sys.path.append('/packages')

from services.trading_history_service import TradingHistoryService

async def test_trading_history():
    """Test the trading history service."""
    print("🧪 Testing Trading History Service...")
    
    # Initialize service
    history_service = TradingHistoryService(test_mode=True)
    
    try:
        # Test fetching and storing futures trades
        print("\n📈 Testing futures trades fetch...")
        futures_result = await history_service.fetch_and_store_futures_trades(days=7)
        print(f"Futures result: {futures_result}")
        
        # Test fetching and storing spot trades
        print("\n💱 Testing spot trades fetch...")
        spot_result = await history_service.fetch_and_store_spot_trades(days=7)
        print(f"Spot result: {spot_result}")
        
        # Test storing account balance
        print("\n💰 Testing account balance storage...")
        balance_result = await history_service.store_account_balance()
        print(f"Balance result: {balance_result}")
        
        # Test calculating daily PNL
        print("\n📊 Testing daily PNL calculation...")
        from datetime import datetime, timedelta
        yesterday = datetime.now().date() - timedelta(days=1)
        pnl_result = await history_service.calculate_daily_pnl(yesterday)
        print(f"PNL result: {pnl_result}")
        
        # Test getting stored summary
        print("\n📋 Testing stored summary...")
        summary_result = await history_service.get_stored_pnl_summary(days=30)
        print(f"Summary result: {summary_result}")
        
        print("\n✅ Trading history service test completed!")
        
    except Exception as e:
        print(f"❌ Error testing trading history service: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_trading_history())












