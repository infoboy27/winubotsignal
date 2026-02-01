# 🎯 Adding Multiple Binance Accounts via Environment Variables

## Overview
This guide shows you how to add multiple Binance trading accounts directly in `production.env`. The bot will automatically detect and trade on all configured accounts.

## ✅ How It Works

The bot now supports **two methods** for multi-account trading:

### **Method 1: Environment Variables (Recommended)** ⭐
- Add accounts directly in `production.env`
- Simple and straightforward
- No UI configuration needed
- Perfect for automation

### **Method 2: Database/UI System**
- Add accounts through the dashboard UI
- More features (per-account settings, verification, etc.)
- Best for complex setups

**The bot will try Method 1 first, then fallback to Method 2, then fallback to single-account execution.**

---

## 📝 Step-by-Step: Add Another Account

### **Step 1: Add API Keys to `production.env`**

Edit your `production.env` file and add the new account:

```bash
# Account 1 (Primary) - Already configured
BINANCE_API_KEY=SaF4OnvK1dhNMmeD8x08lDpucLOjBLCoV0FkcuKlQDOOjQUsBpQh1JtbKE0bL7FZ
BINANCE_API_SECRET=ujc2eBsOcy8OZyFLNIxUNV4cmnKcnJzYCZzUsFCHb5jkOexafwKmpXFAo01aM2dS

# Account 2 (New) - Add your second account here
BINANCE_API_KEY_2=your_second_api_key_here
BINANCE_API_SECRET_2=your_second_api_secret_here

# Account 3 (Optional) - Add more accounts as needed
BINANCE_API_KEY_3=your_third_api_key_here
BINANCE_API_SECRET_3=your_third_api_secret_here

# You can add as many as you want (4, 5, 6, etc.)
# Just increment the number: BINANCE_API_KEY_4, BINANCE_API_KEY_5, etc.
```

### **Step 2: Restart the Bot**

After adding the keys, restart the Docker containers:

```bash
cd /home/ubuntu/winubotsignal
docker-compose -f docker-compose.traefik.yml restart bot
```

Or restart the entire stack:

```bash
docker-compose -f docker-compose.traefik.yml down
docker-compose -f docker-compose.traefik.yml up -d
```

### **Step 3: Verify**

Check the bot logs to confirm accounts were loaded:

```bash
docker logs winu-bot-signal-bot -f
```

You should see:
```
✅ Loaded Account 1 from BINANCE_API_KEY
✅ Loaded Account 2 from BINANCE_API_KEY_2
✅ Loaded Account 3 from BINANCE_API_KEY_3
🎯 Total accounts loaded: 3
```

---

## 🔐 Getting Binance API Keys

### **For Each New Account:**

1. **Login to Binance**: https://www.binance.com/en/my/settings/api-management

2. **Create API Key**:
   - Click "Create API"
   - Label: "Winu Trading Bot - Account 2"
   - Click "Create"

3. **Set Permissions** (IMPORTANT!):
   - ✅ **Enable Spot & Margin Trading**
   - ✅ **Enable Futures**
   - ❌ **DO NOT enable withdrawals** (security!)
   - ✅ **Add IP Restriction**: Add your server IP (51.195.4.197)

4. **Copy Keys**:
   - Copy API Key
   - Copy API Secret (you won't see it again!)
   - Save them securely

5. **Add to `production.env`**:
   ```bash
   BINANCE_API_KEY_2=paste_your_api_key_here
   BINANCE_API_SECRET_2=paste_your_api_secret_here
   ```

---

## ⚙️ Configuration Options

All accounts share the same settings from `production.env`:

```bash
# Leverage (applies to all accounts)
BOT_LEVERAGE=20.0
BOT_MAX_LEVERAGE=20.0

# Risk Management (applies to all accounts)
DEFAULT_RISK_PERCENT=1.0
MAX_DAILY_LOSS_PERCENT=5.0
MAX_POSITIONS=10
```

Each account will:
- Calculate position size based on **2% of its own balance** (or max $100)
- Use the same leverage setting
- Use the same risk management rules
- Execute trades independently

---

## 📊 What Happens When a Signal is Generated?

When the bot generates a signal:

1. **Environment-Based Multi-Account** (First Priority):
   ```
   → Reads all BINANCE_API_KEY_* from production.env
   → Executes signal on ALL accounts in parallel
   → Each account trades independently
   → Sends individual notification per account
   → Sends summary notification
   ```

2. **Database Multi-Account** (Second Priority):
   ```
   → If no environment accounts found
   → Checks database for UI-configured accounts
   → Executes on all active accounts
   ```

3. **Single-Account Fallback** (Last Resort):
   ```
   → If both multi-account methods fail
   → Uses primary BINANCE_API_KEY only
   ```

---

## 🎯 Example Setup

### **Conservative + Aggressive Strategy**

You can use different accounts for different strategies by managing them separately:

```bash
# Account 1 - Conservative (smaller balance, lower risk)
BINANCE_API_KEY=conservative_account_key
BINANCE_API_SECRET=conservative_account_secret

# Account 2 - Aggressive (larger balance, higher risk)
BINANCE_API_KEY_2=aggressive_account_key
BINANCE_API_SECRET_2=aggressive_account_secret
```

Both will trade the same signals, but:
- Account 1 will use 2% of its smaller balance
- Account 2 will use 2% of its larger balance

---

## 🔍 Testing Your Setup

### **Test with Testnet First**

Before using real accounts, test with Binance Testnet:

1. **Get Testnet Keys**: https://testnet.binance.vision/

2. **Add to `production.env`**:
   ```bash
   # Testnet Account 1
   BINANCE_API_KEY=testnet_key_1
   BINANCE_API_SECRET=testnet_secret_1
   
   # Testnet Account 2
   BINANCE_API_KEY_2=testnet_key_2
   BINANCE_API_SECRET_2=testnet_secret_2
   ```

3. **Set Test Mode**:
   ```bash
   BOT_TEST_MODE=true
   ```

4. **Restart and Monitor**:
   ```bash
   docker-compose -f docker-compose.traefik.yml restart bot
   docker logs winu-bot-signal-bot -f
   ```

---

## 📱 Discord Notifications

You'll receive two types of notifications:

### **Individual Account Notifications**:
```
🎯 Order Executed - Account 1
BTC/USDT LONG
Entry: $50,000
Position Size: $100
Stop Loss: $49,500
Take Profit: $51,000
```

### **Summary Notification**:
```
📊 Multi-Account Execution Summary
Signal: BTC/USDT LONG
Success Rate: 2/3

Successful:
✅ Account 1
✅ Account 2

Failed:
❌ Account 3: Insufficient balance: $5.00
```

---

## 🚨 Security Best Practices

- ✅ **Always set IP restrictions** on Binance API keys
- ✅ **NEVER enable withdrawals** on trading API keys
- ✅ **Start with small amounts** to test
- ✅ **Use testnet first** before live trading
- ✅ **Keep production.env secure** (never commit to git)
- ✅ **Regularly rotate API keys** for security
- ✅ **Monitor Discord alerts** for all trades

---

## 🔧 Troubleshooting

### **Bot only uses Account 1**

Check if `BINANCE_API_KEY_2` is properly set:
```bash
docker exec winu-bot-signal-bot env | grep BINANCE_API_KEY
```

You should see:
```
BINANCE_API_KEY=...
BINANCE_API_KEY_2=...
```

If not, restart containers after editing `production.env`:
```bash
docker-compose -f docker-compose.traefik.yml down
docker-compose -f docker-compose.traefik.yml up -d
```

### **Account shows "Insufficient balance"**

Each account needs at least $10 USDT balance. Deposit more funds or adjust position sizing.

### **"Invalid API key" error**

1. Verify API key is correct in `production.env`
2. Check API key permissions on Binance
3. Verify IP restriction includes your server IP (51.195.4.197)

### **Check Loaded Accounts**

View bot logs to see which accounts were loaded:
```bash
docker logs winu-bot-signal-bot 2>&1 | grep "Loaded Account"
```

---

## 📋 Quick Reference

### **Add Account 2**:
```bash
nano /home/ubuntu/winubotsignal/production.env

# Add these lines:
BINANCE_API_KEY_2=your_api_key_here
BINANCE_API_SECRET_2=your_api_secret_here

# Save and restart:
docker-compose -f docker-compose.traefik.yml restart bot
```

### **View Logs**:
```bash
# Real-time logs
docker logs winu-bot-signal-bot -f

# Check account loading
docker logs winu-bot-signal-bot 2>&1 | grep "account"
```

### **Check Environment Variables**:
```bash
docker exec winu-bot-signal-bot env | grep BINANCE
```

---

## ✅ Summary

| Task | Command/Action |
|------|----------------|
| **Edit environment** | `nano /home/ubuntu/winubotsignal/production.env` |
| **Add Account 2** | Add `BINANCE_API_KEY_2` and `BINANCE_API_SECRET_2` |
| **Add Account 3** | Add `BINANCE_API_KEY_3` and `BINANCE_API_SECRET_3` |
| **Restart bot** | `docker-compose -f docker-compose.traefik.yml restart bot` |
| **View logs** | `docker logs winu-bot-signal-bot -f` |
| **Test keys** | Get keys from https://testnet.binance.vision/ |
| **Live keys** | Get keys from https://www.binance.com/en/my/settings/api-management |

---

## 🎉 That's It!

Adding another account is now as simple as:
1. Add `BINANCE_API_KEY_2` and `BINANCE_API_SECRET_2` to `production.env`
2. Restart the bot
3. Done! The bot will automatically trade on both accounts

No database setup, no UI configuration, no complex scripts needed!

---

**Created:** October 9, 2025  
**System:** Environment-Based Multi-Account Executor  
**Status:** Production Ready ✅





