#!/bin/bash

echo "🤖 Setting up Winu Bot Signal Monitoring System"
echo "================================================"

# Make scripts executable
chmod +x background_monitor.py
chmod +x serve_status.py
chmod +x monitor_bot.py

# Install systemd service
echo "📋 Installing systemd service..."
sudo cp winu-bot-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable winu-bot-monitor.service

# Start the background monitor
echo "🔄 Starting background monitor..."
sudo systemctl start winu-bot-monitor.service

# Check status
echo "📊 Checking monitor status..."
sudo systemctl status winu-bot-monitor.service --no-pager

echo ""
echo "✅ Monitoring system setup complete!"
echo ""
echo "🔧 Available commands:"
echo "  - Check status: python3 monitor_bot.py status"
echo "  - Test Discord: python3 background_monitor.py test-discord"
echo "  - View logs: tail -f monitor.log"
echo "  - Service status: sudo systemctl status winu-bot-monitor"
echo "  - Service logs: sudo journalctl -u winu-bot-monitor -f"
echo ""
echo "🌐 Status page: http://localhost:8080 (run: python3 serve_status.py)"
echo "📱 Discord alerts are now active!"
echo ""
echo "🎯 The system will automatically:"
echo "  - Monitor system health every 60 seconds"
echo "  - Send Discord alerts for failures"
echo "  - Send Discord alerts for new data ingestion"
echo "  - Send Discord alerts for new trading signals"
echo "  - Auto-fix common issues (restart API, trigger data ingestion)"





