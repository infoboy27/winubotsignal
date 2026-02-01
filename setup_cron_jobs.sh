#!/bin/bash
"""
Setup cron jobs for Winu Bot Signal automation.
"""

echo "🔧 Setting up Winu Bot Signal cron jobs..."

# Make scripts executable
chmod +x monitor_system.py
chmod +x data_ingestion_cron.py
chmod +x signal_analysis_cron.py

# Create cron jobs
echo "📅 Creating cron jobs..."

# Monitor system every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * cd /home/ubuntu/winubotsignal && python3 monitor_system.py >> /var/log/winu-monitor.log 2>&1") | crontab -

# Data ingestion every 10 minutes
(crontab -l 2>/dev/null; echo "*/10 * * * * cd /home/ubuntu/winubotsignal && python3 data_ingestion_cron.py >> /var/log/winu-data.log 2>&1") | crontab -

# Signal analysis every 1 hour
(crontab -l 2>/dev/null; echo "0 * * * * cd /home/ubuntu/winubotsignal && python3 signal_analysis_cron.py >> /var/log/winu-signals.log 2>&1") | crontab -

# Create log files
touch /var/log/winu-monitor.log
touch /var/log/winu-data.log
touch /var/log/winu-signals.log
chmod 666 /var/log/winu-*.log

echo "✅ Cron jobs configured:"
echo "  • System Monitor: Every 5 minutes"
echo "  • Data Ingestion: Every 10 minutes" 
echo "  • Signal Analysis: Every 1 hour"

echo "📋 Current cron jobs:"
crontab -l

echo "📊 Log files created:"
echo "  • /var/log/winu-monitor.log"
echo "  • /var/log/winu-data.log"
echo "  • /var/log/winu-signals.log"





