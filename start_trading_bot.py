#!/usr/bin/env python3
"""
Start the trading bot with proper environment loading
"""
import os
import sys
from dotenv import load_dotenv

# Change to bot directory
os.chdir('/home/ubuntu/winubotsignal/bot')

# Load environment from production.env
load_dotenv('/home/ubuntu/winubotsignal/production.env')

# Set Python path
sys.path.insert(0, '/home/ubuntu/winubotsignal/bot')
sys.path.insert(0, '/home/ubuntu/winubotsignal/packages')

# Now run the trading bot script directly
import asyncio
import subprocess

if __name__ == "__main__":
    print("🚀 Starting Winu Trading Bot...")
    # Run the trading bot directly
    subprocess.run([sys.executable, '/home/ubuntu/winubotsignal/bot/core/trading_bot.py'])

