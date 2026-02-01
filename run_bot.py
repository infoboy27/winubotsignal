#!/usr/bin/env python3
"""
Proper startup wrapper for trading bot
"""
import os
import sys
from dotenv import load_dotenv

# Load environment first
print("📝 Loading environment from production.env...")
load_dotenv('/home/ubuntu/winubotsignal/production.env', override=True)

# Override database host to use localhost
os.environ['POSTGRES_HOST'] = 'localhost'

# Set Python path - add core to path so imports work
sys.path.insert(0, '/home/ubuntu/winubotsignal/bot/core')
sys.path.insert(0, '/home/ubuntu/winubotsignal/bot')
sys.path.insert(0, '/home/ubuntu/winubotsignal/packages')

# Change to core directory so relative imports work
os.chdir('/home/ubuntu/winubotsignal/bot/core')

# Verify environment
print(f"✅ BINANCE_API_KEY: {os.getenv('BINANCE_API_KEY', 'NOT SET')[:20]}...")
print(f"✅ BINANCE_API_KEY_2: {os.getenv('BINANCE_API_KEY_2', 'NOT SET')[:20]}...")
print(f"✅ JWT_SECRET: {os.getenv('JWT_SECRET', 'NOT SET')[:20]}...")
print(f"✅ POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
print()

# Now start the bot
print("🚀 Starting Trading Bot...")
print()

# Import and run
try:
    import asyncio
    from trading_bot import main
    asyncio.run(main())
except Exception as e:
    print(f"❌ Error starting bot: {e}")
    import traceback
    traceback.print_exc()

