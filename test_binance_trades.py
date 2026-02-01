#!/usr/bin/env python3
"""
Test to see what Binance API returns for trades
"""

import asyncio
import ccxt
import sys
sys.path.append('/packages')

from common.config import get_settings
from datetime import datetime, timedelta

settings = get_settings()

async def test_binance_trades():
    """Test what Binance API returns."""
    print("🧪 Testing Binance Trades...")
    
    try:
        # Test futures exchange
        futures_exchange = ccxt.binance({
            'apiKey': settings.exchange.binance_api_key,
            'secret': settings.exchange.binance_api_secret,
            'sandbox': False,
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        
        print("\n📈 Testing Futures Exchange...")
        
        # Test balance
        try:
            balance = futures_exchange.fetch_balance()
            print(f"✅ Futures balance keys: {list(balance.keys())}")
            for asset, amount in balance.get('total', {}).items():
                if float(amount) > 0:
                    print(f"  {asset}: {amount}")
        except Exception as e:
            print(f"❌ Futures balance error: {e}")
        
        # Test trades for BTCUSDT
        try:
            since = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
            trades = futures_exchange.fetch_my_trades(symbol='BTCUSDT', since=since, limit=10)
            print(f"✅ BTCUSDT futures trades: {len(trades)}")
            if trades:
                print(f"Sample trade: {trades[0]}")
        except Exception as e:
            print(f"❌ BTCUSDT futures trades error: {e}")
        
        # Test spot exchange
        spot_exchange = ccxt.binance({
            'apiKey': settings.exchange.binance_api_key,
            'secret': settings.exchange.binance_api_secret,
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        print("\n💱 Testing Spot Exchange...")
        
        # Test trades for BTCUSDT
        try:
            since = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
            trades = spot_exchange.fetch_my_trades(symbol='BTCUSDT', since=since, limit=10)
            print(f"✅ BTCUSDT spot trades: {len(trades)}")
            if trades:
                print(f"Sample trade: {trades[0]}")
        except Exception as e:
            print(f"❌ BTCUSDT spot trades error: {e}")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_binance_trades())












