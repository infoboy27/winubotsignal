#!/bin/bash

echo "🔧 Fixing Traefik Routing for Dashboard..."

# Stop the direct dashboard process
echo "🛑 Stopping direct dashboard process..."
pkill -f "dashboard/app.py" 2>/dev/null || true

# Stop any existing bot-dashboard container
echo "🛑 Stopping existing bot-dashboard container..."
docker stop winu-bot-signal-bot-dashboard 2>/dev/null || true
docker rm winu-bot-signal-bot-dashboard 2>/dev/null || true

# Build the dashboard image
echo "📦 Building dashboard image..."
docker build -t winu-bot-dashboard ./bot

# Start the bot-dashboard service with Traefik
echo "🚀 Starting bot-dashboard with Traefik routing..."
docker-compose up -d bot-dashboard

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Check if container is running
echo "🔍 Checking container status..."
if docker ps | grep -q "winu-bot-signal-bot-dashboard"; then
    echo "✅ Bot dashboard container is running"
    
    # Check Traefik routing
    echo "🔍 Checking Traefik routing..."
    docker logs winu-bot-signal-traefik 2>&1 | tail -10
    
    echo ""
    echo "🎉 Dashboard should now be accessible at:"
    echo "🌐 https://bot.winu.app"
    echo "🔑 Login: admin / admin123"
    echo ""
    echo "📋 If still 404, check:"
    echo "  - DNS: bot.winu.app points to this server"
    echo "  - Traefik logs: docker logs winu-bot-signal-traefik"
    echo "  - Container logs: docker logs winu-bot-signal-bot-dashboard"
    
else
    echo "❌ Bot dashboard container failed to start"
    echo "📋 Check logs: docker logs winu-bot-signal-bot-dashboard"
fi

