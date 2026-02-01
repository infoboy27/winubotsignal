#!/bin/bash

echo "🚀 Setting up permanent dashboard service..."

# Create systemd service file
sudo tee /etc/systemd/system/winu-bot-dashboard.service > /dev/null <<EOF
[Unit]
Description=Winu Bot Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/winubotsignal/bot
Environment=PYTHONPATH=/home/ubuntu/winubotsignal/packages:/home/ubuntu/winubotsignal/bot
ExecStart=/usr/bin/python3 /home/ubuntu/winubotsignal/bot/dashboard/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable winu-bot-dashboard
sudo systemctl start winu-bot-dashboard

# Check status
echo "📊 Service Status:"
sudo systemctl status winu-bot-dashboard --no-pager -l

echo ""
echo "✅ Dashboard service setup complete!"
echo "🌐 Access at: https://bot.winu.app"
echo "🔑 Login: admin / admin123"
echo ""
echo "📋 Useful commands:"
echo "  sudo systemctl status winu-bot-dashboard"
echo "  sudo systemctl restart winu-bot-dashboard"
echo "  sudo journalctl -u winu-bot-dashboard -f"

