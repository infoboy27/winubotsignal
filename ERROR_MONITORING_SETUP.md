# Error Monitoring System - Configuration Summary

## 🎯 Overview

Comprehensive error monitoring has been configured for the Winu Bot Signal system. All errors and system issues will now be automatically reported to your Discord channel.

## 📢 Discord Webhook

**Channel**: Spidey Bot (Discord)
**Webhook URL**: https://discord.com/api/webhooks/1425290353992532028/YjgFYIiir_cHf04Es12Ah2VxgTIcCRqj2wz7JsKcc6CqhWdAJABDdw_KVbxtDrEaxIOu

## 🔍 What's Being Monitored

### 1. **Signal Generation (scan_markets)**
- **Errors Tracked**: 
  - Individual asset scanning failures
  - Complete market scan failures
- **Severity Levels**: 
  - ERROR (individual asset)
  - CRITICAL (complete failure)
- **Impact Alert**: Shows when no signals are generated

### 2. **Market Data Ingestion**
- **Errors Tracked**: Data ingestion failures
- **Severity**: CRITICAL
- **Impact Alert**: No fresh market data available

### 3. **Alert Sending**
- **Errors Tracked**: Failed to send Telegram/Discord alerts to users
- **Severity**: ERROR
- **Impact Alert**: Users didn't receive signal notifications

### 4. **Trading Opportunity Checks**
- **Errors Tracked**: Trading bot analysis failures
- **Severity**: ERROR
- **Impact Alert**: Trading bot not analyzing signals

### 5. **System Health (Every 5 Minutes)**
- Checks all Docker containers
- Verifies API health
- Validates database connectivity
- Monitors signal generation activity
- Sends alerts only when issues detected

## 📊 Alert Types

### ✅ **SUCCESS** (Green)
- System activated
- Recovery notifications

### ℹ️ **INFO** (Blue)
- General system information
- Status updates

### ⚠️ **WARNING** (Yellow)
- Non-critical issues
- Service degradation

### 🚨 **ERROR** (Orange-Red)
- Failures that need attention
- Individual component errors

### 🔥 **CRITICAL** (Red)
- System-wide failures
- Data loss risk
- Complete service outage

## 📁 Files Created/Modified

### New Files:
1. `/packages/monitoring/error_monitor.py` - Core error monitoring system
2. `/packages/monitoring/__init__.py` - Package initialization
3. `/home/ubuntu/winubotsignal/health_monitor.py` - Health check script
4. `/usr/local/bin/health_monitor_cron.sh` - Cron wrapper script

### Modified Files:
1. `/production.env` - Updated Discord webhook URL
2. `/apps/worker/worker.py` - Added error monitoring to all critical tasks

## ⏰ Automated Monitoring

### Health Checks (Every 5 Minutes)
- **Cron Job**: `*/5 * * * * /usr/local/bin/health_monitor_cron.sh`
- **Log File**: `/var/log/winu_health_monitor.log`
- **Checks**:
  - ✅ API health
  - ✅ Web container
  - ✅ Worker container
  - ✅ Trading bot container
  - ✅ Database connectivity
  - ✅ Redis status
  - ✅ Recent signal activity

### Real-Time Error Monitoring
All worker tasks now automatically send Discord alerts when errors occur:
- Signal generation failures
- Data ingestion errors
- Alert sending failures
- Trading bot errors

## 🧪 Testing

You should have received **3 test messages** in your Discord channel:

1. **🎯 Error Monitoring System Activated** (SUCCESS - Green)
   - Confirms system is configured
   - Lists monitoring scope

2. **🚨 WARNING: Exception** (WARNING - Yellow)
   - Example of how error alerts look
   - Includes traceback and context

3. **No message** (All healthy)
   - Health check found no issues
   - Alerts only sent when problems detected

## 📖 Usage Examples

### Manually Run Health Check:
```bash
cd /home/ubuntu/winubotsignal
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1425290353992532028/YjgFYIiir_cHf04Es12Ah2VxgTIcCRqj2wz7JsKcc6CqhWdAJABDdw_KVbxtDrEaxIOu"
python3 health_monitor.py
```

### Send Custom Alert:
```python
from monitoring.error_monitor import error_monitor

error_monitor.send_custom_alert(
    title="Custom Alert",
    message="Something happened!",
    severity="INFO"
)
```

### Monitor Errors in Code:
```python
from monitoring.error_monitor import monitor_errors

@monitor_errors(context="My Function", severity="ERROR")
def my_function():
    # Your code here
    pass
```

## 🔧 Troubleshooting

### If you're not receiving alerts:

1. **Check Discord webhook is valid**:
   ```bash
   curl -X POST -H "Content-Type: application/json" \
     -d '{"content": "Test"}' \
     https://discord.com/api/webhooks/1425290353992532028/YjgFYIiir_cHf04Es12Ah2VxgTIcCRqj2wz7JsKcc6CqhWdAJABDdw_KVbxtDrEaxIOu
   ```

2. **Check worker logs**:
   ```bash
   docker logs winu-bot-signal-worker --tail=50
   ```

3. **Verify environment variable**:
   ```bash
   docker exec winu-bot-signal-worker printenv | grep DISCORD
   ```

4. **View health monitor logs**:
   ```bash
   tail -f /var/log/winu_health_monitor.log
   ```

## 🔄 Maintenance

### Restart Workers (Apply Changes):
```bash
docker restart winu-bot-signal-worker winu-bot-signal-celery-beat
```

### View Cron Jobs:
```bash
crontab -l
```

### Disable Health Checks (if needed):
```bash
crontab -l | grep -v health_monitor | crontab -
```

## ✨ Features

- ✅ Real-time error reporting
- ✅ Automatic health monitoring every 5 minutes
- ✅ Detailed error context and tracebacks
- ✅ Severity-based color coding
- ✅ Service-specific error tracking
- ✅ Impact assessment for each error
- ✅ Cooldown system (prevents spam)
- ✅ Comprehensive system status checks

## 📈 What to Expect

### During Normal Operation:
- Health checks run silently every 5 minutes
- No alerts sent when everything is healthy
- Errors immediately reported to Discord

### When Issues Occur:
- Instant Discord notification
- Clear error description
- Full traceback included
- Context and impact explained
- Severity level indicated by color

### After the 8:00pm batch issue:
- If scan_markets fails again, you'll get an alert
- Database errors will be reported
- Data ingestion problems flagged
- Signal generation tracked

## 🎉 Success!

Your error monitoring system is now **FULLY OPERATIONAL**. All system errors will be automatically reported to your Discord channel with detailed information to help you quickly identify and fix issues.

---
**Configured**: October 7, 2025, 9:19 PM EDT
**Status**: ✅ Active and Monitoring





