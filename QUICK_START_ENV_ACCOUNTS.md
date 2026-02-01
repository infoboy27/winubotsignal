# 🚀 Environment-Based Multi-Account Trading - Quick Start

## ✅ What Was Implemented

A simple environment-based multi-account trading system that reads Binance accounts directly from `production.env`.

### Key Features:
- ✅ Add accounts directly in `production.env`
- ✅ No UI configuration needed
- ✅ Automatic detection of all accounts
- ✅ Parallel execution on all accounts
- ✅ Individual + summary Discord notifications
- ✅ Works alongside existing database multi-account system

---

## 📝 How to Add Another Account

### **Step 1: Edit `production.env`**

```bash
nano /home/ubuntu/winubotsignal/production.env
```

Find the "Exchange APIs" section and uncomment/add:

```bash
# Account 1 (Primary) - Already configured
BINANCE_API_KEY=SaF4OnvK1dhNMmeD8x08lDpucLOjBLCoV0FkcuKlQDOOjQUsBpQh1JtbKE0bL7FZ
BINANCE_API_SECRET=ujc2eBsOcy8OZyFLNIxUNV4cmnKcnJzYCZzUsFCHb5jkOexafwKmpXFAo01aM2dS

# Account 2 (New) - Add your second account
BINANCE_API_KEY_2=your_second_api_key_here
BINANCE_API_SECRET_2=your_second_api_secret_here
```

Save with `Ctrl+O`, exit with `Ctrl+X`.

### **Step 2: Get Binance API Keys**

1. Go to: https://www.binance.com/en/my/settings/api-management
2. Create new API key
3. **Set permissions**:
   - ✅ Enable Spot & Margin Trading
   - ✅ Enable Futures
   - ❌ **DO NOT enable withdrawals**
   - ✅ Add IP restriction: `51.195.4.197`
4. Copy the API Key and Secret

### **Step 3: Test Configuration**

```bash
cd /home/ubuntu/winubotsignal
python3 test_multi_account_env.py
```

This will show:
- ✅ Which accounts were detected
- 📊 How many accounts are configured
- ⚙️ Current trading settings

### **Step 4: Restart Bot**

```bash
cd /home/ubuntu/winubotsignal
docker-compose -f docker-compose.traefik.yml restart bot
```

### **Step 5: Verify**

Check logs to confirm accounts were loaded:

```bash
docker logs winu-bot-signal-bot -f
```

Look for:
```
✅ Loaded Account 1 from BINANCE_API_KEY
✅ Loaded Account 2 from BINANCE_API_KEY_2
🎯 Total accounts loaded: 2
```

---

## 🔍 What Happens When a Signal is Generated?

```
1. Signal Generated (e.g., BTC/USDT LONG)
         ↓
2. Bot reads all BINANCE_API_KEY_* from environment
         ↓
3. Executes on ALL accounts in parallel:
   • Account 1: $100 position
   • Account 2: $100 position
         ↓
4. Sends Discord notification for each account
         ↓
5. Sends summary: "2/2 accounts filled successfully"
```

---

## 📁 Files Created/Modified

### **New Files:**
- `bot/execution/env_multi_account_executor.py` - Main executor
- `HOW_TO_ADD_ACCOUNT_ENV.md` - Detailed guide
- `test_multi_account_env.py` - Test script
- `QUICK_START_ENV_ACCOUNTS.md` - This file

### **Modified Files:**
- `bot/core/trading_bot.py` - Added environment-based multi-account support
- `production.env` - Added placeholders for Account 2 and 3
- `env.example` - Added multi-account template

---

## 🎯 Examples

### **Add Account 2:**
```bash
# In production.env
BINANCE_API_KEY_2=abc123def456...
BINANCE_API_SECRET_2=xyz789uvw012...
```

### **Add Account 3:**
```bash
# In production.env
BINANCE_API_KEY_3=ghi345jkl678...
BINANCE_API_SECRET_3=mno901pqr234...
```

### **Add More Accounts:**
```bash
# Just keep incrementing the number
BINANCE_API_KEY_4=...
BINANCE_API_SECRET_4=...

BINANCE_API_KEY_5=...
BINANCE_API_SECRET_5=...
```

---

## 🔧 Configuration

All accounts share these settings from `production.env`:

```bash
BOT_LEVERAGE=20.0              # Leverage for all accounts
DEFAULT_RISK_PERCENT=1.0       # Risk per trade
MAX_DAILY_LOSS_PERCENT=5.0     # Max daily loss
```

Each account calculates position size based on:
- **2% of its own balance** (or max $100, whichever is smaller)
- Its own available balance
- Same leverage setting

---

## 🚨 Important Notes

### **Security:**
- ✅ Always set IP restrictions
- ✅ NEVER enable withdrawals
- ✅ Keep production.env secure (never commit to git)

### **Testing:**
- ✅ Test with Binance Testnet first: https://testnet.binance.vision/
- ✅ Start with small amounts
- ✅ Monitor Discord alerts

### **Fallback System:**
The bot tries methods in this order:
1. **Environment-based** (production.env) - FIRST
2. **Database-based** (UI configured) - SECOND
3. **Single account** (original executor) - FALLBACK

---

## 🆘 Troubleshooting

### **Only Account 1 is trading:**
```bash
# Check if Account 2 is loaded
docker exec winu-bot-signal-bot env | grep BINANCE_API_KEY_2

# If empty, restart containers
docker-compose -f docker-compose.traefik.yml down
docker-compose -f docker-compose.traefik.yml up -d
```

### **"Insufficient balance" error:**
Each account needs at least $10 USDT. Deposit more or adjust position sizing.

### **"Invalid API key" error:**
1. Verify keys in production.env
2. Check Binance API permissions
3. Verify IP restriction matches your server IP

---

## 📊 Monitoring

### **View Real-time Logs:**
```bash
docker logs winu-bot-signal-bot -f
```

### **Check Loaded Accounts:**
```bash
docker logs winu-bot-signal-bot 2>&1 | grep "Loaded Account"
```

### **View Environment Variables:**
```bash
docker exec winu-bot-signal-bot env | grep BINANCE
```

---

## ✅ Summary

**Adding another account is now super simple:**

1. **Edit** `production.env`
2. **Add** `BINANCE_API_KEY_2` and `BINANCE_API_SECRET_2`
3. **Restart** the bot
4. **Done!** Bot trades on both accounts automatically

No database, no UI, no complex setup! 🎉

---

## 📖 More Information

- **Detailed Guide:** See `HOW_TO_ADD_ACCOUNT_ENV.md`
- **Test Script:** Run `python3 test_multi_account_env.py`
- **Get API Keys:** https://www.binance.com/en/my/settings/api-management
- **Testnet Keys:** https://testnet.binance.vision/

---

**Status:** ✅ Production Ready  
**Date:** October 9, 2025  
**System:** Environment-Based Multi-Account Executor





