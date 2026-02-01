#!/bin/bash
# Start Winu Trading Bot

echo "🚀 Starting Winu Trading Bot..."

# Change to bot directory
cd /home/ubuntu/winubotsignal/bot

# Set Python path
export PYTHONPATH=/home/ubuntu/winubotsignal/bot:/home/ubuntu/winubotsignal/packages

# Load environment variables (filter out comments)
export $(grep -v '^#' /home/ubuntu/winubotsignal/production.env | grep -v '^$' | xargs)

# Override database host to use localhost since we're running on host
export POSTGRES_HOST=localhost

# Start the bot
exec python3 core/trading_bot.py

