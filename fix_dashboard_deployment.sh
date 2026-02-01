#!/bin/bash

echo "🔧 Fixing Dashboard Deployment..."

# Stop any running dashboard processes
pkill -f "dashboard/app.py" 2>/dev/null || true

# Kill any existing bot-dashboard container
docker stop winu-bot-signal-bot-dashboard 2>/dev/null || true
docker rm winu-bot-signal-bot-dashboard 2>/dev/null || true

# Build the bot dashboard image
echo "📦 Building bot dashboard image..."
docker build -t winu-bot-dashboard ./bot

# Start the bot dashboard service
echo "🚀 Starting bot dashboard service..."
docker-compose up -d bot-dashboard

# Check if the service is running
echo "🔍 Checking service status..."
sleep 5
docker ps | grep bot-dashboard

echo "✅ Dashboard deployment fixed!"
echo "🌐 Access at: https://bot.winu.app"
echo "🔑 Login: admin / admin123"

