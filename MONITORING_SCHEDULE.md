# Winu Bot Automated Monitoring Schedule

## 📅 Overview

Your Winu Bot system now has comprehensive automated monitoring with scheduled reports and real-time alerts.

## ⏰ Automated Tasks

### 1. **Daily System Audit** 🌅
- **Schedule**: Every day at 7:00 AM
- **Script**: `/usr/local/bin/daily_system_audit.sh`
- **Cron**: `0 7 * * * /usr/local/bin/daily_system_audit.sh`
- **Log File**: `/var/log/winu_daily_audit.log`

**What's Included**:
- ✅ All container statuses (10 containers)
- 📊 Database statistics (signals, users, subscriptions)
- 🌐 API health check
- 💻 System resources (disk, memory, CPU)
- 📈 Trading bot activity
- ⚠️ Recent errors (if any)
- 📉 Signal generation stats (24h and 1h)

**Discord Report Shows**:
```
✅ System Audit - All Systems Operational
├─ 📦 Containers: 10/10 Running
├─ 📊 Signals (24h): Long vs Short breakdown
├─ 👥 Users: Total & Active Subscriptions
├─ 💻 Resources: Disk, Memory, CPU usage
├─ 🌐 API: Health status
└─ ⏰ Activity: Recent signal generation
```

---

### 2. **Health Monitoring** 🏥
- **Schedule**: Every 5 minutes
- **Script**: `/usr/local/bin/health_monitor_cron.sh`
- **Cron**: `*/5 * * * * /usr/local/bin/health_monitor_cron.sh`
- **Log File**: `/var/log/winu_health_monitor.log`

**What's Checked**:
- API responsiveness
- All container statuses
- Database connectivity
- Recent signal activity (last 2 hours)

**Alert Behavior**:
- ✅ **No alerts** when everything is healthy
- ⚠️ **Discord alert** sent only when issues are detected

---

### 3. **Real-Time Error Monitoring** 🚨
- **Schedule**: Continuous (event-driven)
- **Monitoring**: All worker tasks

**Monitored Processes**:
1. **Market Scanning** (`scan_markets`)
   - Asset-level failures → ERROR
   - Complete scan failure → CRITICAL

2. **Data Ingestion** (`ingest_market_data`)
   - Ingestion failures → CRITICAL

3. **Alert Sending** (`send_signal_alerts`)
   - Failed to send alerts → ERROR

4. **Trading Checks** (`trigger_trading_check`)
   - Trading bot errors → ERROR

**Alert Example**:
```
🚨 ERROR: DatabaseException
Context: Market Scan - Asset: BTC/USDT
Severity: ERROR
Impact: Signal generation affected
Traceback: [Full error trace included]
```

---

## 📊 What You'll Receive Daily (7:00 AM)

### ✅ When Everything is Healthy:
```
✅ System Audit - All Systems Operational

📦 Containers Status: 10/10 Running
✅ api     ✅ web       ✅ worker
✅ celery  ✅ trading   ✅ postgres
✅ redis   ✅ grafana   ✅ prometheus
✅ traefik

📊 Signal Statistics (24h):
Total: 61 | LONG: 33 | SHORT: 28

👥 User Statistics:
Total Users: 5 | Active Subs: 1

💻 System Resources:
Disk: 36% | Memory: 5.9GB/31GB
Containers: 12

🌐 API Health: ✅ Operational

⏰ Recent Activity (1h): 15 signals generated

📈 Trading Bot: Open Positions: 2
```

### ⚠️ When Issues are Detected:
Same report format but with:
- ❌ Red X marks for failed services
- Warning severity color (yellow)
- Additional error details section
- Specific failure descriptions

---

## 🔧 Manual Commands

### Run Audit Manually:
```bash
cd /home/ubuntu/winubotsignal
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1425290353992532028/YjgFYIiir_cHf04Es12Ah2VxgTIcCRqj2wz7JsKcc6CqhWdAJABDdw_KVbxtDrEaxIOu"
python3 system_audit.py
```

### Run Health Check Manually:
```bash
cd /home/ubuntu/winubotsignal
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1425290353992532028/YjgFYIiir_cHf04Es12Ah2VxgTIcCRqj2wz7JsKcc6CqhWdAJABDdw_KVbxtDrEaxIOu"
python3 health_monitor.py
```

### View Logs:
```bash
# Daily audit log
tail -f /var/log/winu_daily_audit.log

# Health monitor log
tail -f /var/log/winu_health_monitor.log

# Worker logs (for errors)
docker logs winu-bot-signal-worker --tail=100
```

### Check Cron Jobs:
```bash
crontab -l
```

---

## 📝 Current Cron Schedule

```bash
# System Health Checks - Every 5 minutes
*/5 * * * * /usr/local/bin/health_monitor_cron.sh

# Daily System Audit - Every morning at 7:00 AM
0 7 * * * /usr/local/bin/daily_system_audit.sh
```

---

## 🎯 Alert Severity Guide

| Severity | Color | Icon | When Used |
|----------|-------|------|-----------|
| SUCCESS | 🟢 Green | ✅ | System healthy, tasks completed |
| INFO | 🔵 Blue | ℹ️ | Informational updates |
| WARNING | 🟡 Yellow | ⚠️ | Non-critical issues, degraded service |
| ERROR | 🟠 Orange | 🚨 | Component failures, needs attention |
| CRITICAL | 🔴 Red | 🔥 | System-wide failures, immediate action |

---

## 🔔 Discord Channel: WinuBot

All monitoring alerts are sent to:
- **Webhook**: `https://discord.com/api/webhooks/1425290353992532028/...`
- **Channel ID**: 1424756631010279544
- **Bot Name**: WinuBot

---

## 📈 Expected Alert Frequency

### Daily (Fixed Time):
- 🌅 **7:00 AM**: Full system audit report

### Every 5 Minutes (Conditional):
- 🏥 Health check (only alerts on issues)

### Real-Time (Event-Driven):
- 🚨 Errors as they occur
- ⚠️ System failures immediately
- 🔥 Critical issues instantly

### Typical Day (If Healthy):
- **7:00 AM**: One audit report
- **Throughout day**: Zero to few alerts (only if issues occur)
- **5-minute checks**: Running silently, no alerts

### If Issues Occur:
- **Immediate**: Error alert with details
- **5 minutes later**: Health check confirms issue
- **Next 7:00 AM**: Audit shows historical context

---

## ✅ What's Been Fixed

### Issue Resolved:
1. ✅ **8:00 PM Signal Batch Failure** - numpy float64 conversion bug
2. ✅ **NowPayments Webhook** - subscription activation bug
3. ✅ **Email Verification** - JWT settings path error
4. ✅ **API Registration** - DNS resolution issue

### Monitoring Added:
1. ✅ Real-time error alerts to Discord
2. ✅ Automated health checks every 5 minutes
3. ✅ Daily system audit at 7:00 AM
4. ✅ Comprehensive error tracking

---

## 🚀 System Status

**As of**: October 7, 2025, 9:25 PM EDT

**All Systems**: ✅ **OPERATIONAL**

- 🟢 10/10 Containers Running
- 🟢 API Health: 200 OK
- 🟢 Database: Connected
- 🟢 Signal Generation: 15 signals in last hour
- 🟢 Trading Bot: Active
- 🟢 Resources: Healthy (36% disk, 19% memory)

---

**Next Scheduled Audit**: Tomorrow at 7:00 AM

**Monitoring**: Active and reporting to WinuBot Discord channel 🎯





