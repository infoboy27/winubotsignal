# Adding Trading Accounts for Bot Only (No Dashboard Tracking)

## 🎯 Overview

This guide shows how to add Binance accounts **directly for bot trading** without requiring dashboard UI tracking at bot.winu.app. The bot will automatically detect and trade on these accounts.

---

## ⚡ Quick Method: Use the Script

I've created a script that adds accounts directly for bot trading:

```bash
cd /home/ubuntu/winubotsignal
./add_trading_account.sh
```

This script will:
1. Ask for your Binance API credentials
2. Encrypt them securely
3. Add directly to database
4. Bot automatically picks it up and trades

**No dashboard access needed!**

---

## 🔧 Manual Method: Direct Database Insert

If you prefer to do it manually:

### Step 1: Encrypt Your API Credentials

```bash
# Run encryption script
docker exec winu-bot-signal-api python3 << 'PYTHON'
import sys
sys.path.append('/app')
sys.path.append('/bot')
from services.api_key_encryption import get_encryption_service

# Your credentials
API_KEY = "YOUR_BINANCE_API_KEY"
API_SECRET = "YOUR_BINANCE_API_SECRET"

# Encrypt
encryption = get_encryption_service()
key_enc, secret_enc = encryption.encrypt_key_pair(API_KEY, API_SECRET)

print(f"Encrypted API Key: {key_enc}")
print(f"Encrypted API Secret: {secret_enc}")
PYTHON
```

### Step 2: Insert into Database

```bash
docker exec winu-bot-signal-postgres psql -U winu -d winudb << 'SQL'
INSERT INTO user_api_keys (
    user_id,
    exchange,
    api_key_encrypted,
    api_secret_encrypted,
    api_name,
    account_type,
    test_mode,
    auto_trade_enabled,
    is_active,
    max_position_size_usd,
    leverage,
    max_daily_trades,
    max_risk_per_trade,
    max_daily_loss,
    stop_trading_on_loss,
    position_sizing_mode,
    position_size_value
) VALUES (
    1,                                    -- user_id (use your user ID)
    'binance',
    'YOUR_ENCRYPTED_API_KEY',            -- from step 1
    'YOUR_ENCRYPTED_API_SECRET',         -- from step 1
    'Trading Account 2',                 -- friendly name
    'futures',                           -- futures/spot/both
    false,                               -- test_mode (false = live)
    true,                                -- auto_trade_enabled ← KEY!
    true,                                -- is_active
    1000.0,                              -- max_position_size_usd
    10.0,                                -- leverage
    5,                                   -- max_daily_trades
    0.02,                                -- max_risk_per_trade (2%)
    0.05,                                -- max_daily_loss (5%)
    true,                                -- stop_trading_on_loss
    'fixed',                             -- position_sizing_mode
    100.0                                -- position_size_value
) RETURNING id, api_name;
SQL
```

---

## 🤖 How Bot Detects New Accounts

### **Automatic Detection:**
The bot queries the database every time a signal is generated:

```sql
SELECT * FROM user_api_keys 
WHERE auto_trade_enabled = true 
  AND is_active = true
```

**No restart required!** The bot will detect the new account on the next trading cycle.

### **Trading Flow:**
1. Signal generated
2. Bot queries for active accounts
3. Finds your new account (if auto_trade_enabled=true)
4. Executes trade on ALL active accounts in parallel
5. Stores order in multi_account_orders table
6. Sends Discord notification

---

## 📋 Required Fields for Bot Trading

### **Minimum Configuration:**
```
✓ api_key_encrypted       (Your Binance API key - encrypted)
✓ api_secret_encrypted    (Your Binance API secret - encrypted)
✓ api_name                (Any name for identification)
✓ auto_trade_enabled      (Set to TRUE for bot to trade)
✓ is_active               (Set to TRUE)
```

### **Important Trading Settings:**
```
✓ account_type            (futures/spot/both)
✓ max_position_size_usd   (Maximum position size)
✓ leverage                (1-125x)
✓ max_daily_trades        (Limit trades per day)
✓ max_risk_per_trade      (2% = 0.02)
```

---

## 🚨 Key Field: auto_trade_enabled

This is THE critical field:

- **`auto_trade_enabled = true`** → Bot WILL trade on this account automatically
- **`auto_trade_enabled = false`** → Bot will IGNORE this account

### **Example:**
```sql
-- Enable trading on account
UPDATE user_api_keys SET auto_trade_enabled = true WHERE id = 1;

-- Disable trading on account
UPDATE user_api_keys SET auto_trade_enabled = false WHERE id = 1;
```

---

## 📊 Check Your Accounts

### **View all accounts configured for bot:**
```bash
docker exec winu-bot-signal-postgres psql -U winu -d winudb -c "
  SELECT 
    id,
    api_name,
    account_type,
    test_mode,
    auto_trade_enabled,
    is_active,
    leverage,
    max_position_size_usd
  FROM user_api_keys
  ORDER BY created_at DESC;
"
```

### **View only active trading accounts:**
```bash
docker exec winu-bot-signal-postgres psql -U winu -d winudb -c "
  SELECT 
    id,
    api_name,
    account_type,
    auto_trade_enabled,
    current_balance,
    total_pnl
  FROM user_api_keys
  WHERE auto_trade_enabled = true 
    AND is_active = true;
"
```

---

## 🔍 Verify Bot is Using Your Accounts

### **Check bot logs:**
```bash
# Look for multi-account execution messages
docker logs winu-bot-signal-trading-bot --tail 100 | grep -i "multi-account\|executing signal"
```

### **Check orders table:**
```bash
docker exec winu-bot-signal-postgres psql -U winu -d winudb -c "
  SELECT 
    COUNT(*) as total_orders,
    COUNT(DISTINCT account_id) as accounts_traded
  FROM multi_account_orders;
"
```

---

## 🎯 Simple Example: Add Second Account

```bash
# 1. Run the script
cd /home/ubuntu/winubotsignal
./add_trading_account.sh

# 2. When prompted, enter:
#    - Account Name: Trading Account 2
#    - API Key: [your key]
#    - API Secret: [your secret]
#    - Account Type: futures
#    - Testnet: false
#    - Max Position: 1000
#    - Leverage: 10
#    - Max Trades: 5
#    - Risk: 0.02
#    - Auto-Trade: true  ← This enables bot trading

# 3. Done! Bot will automatically trade on this account
```

---

## 💡 Key Points

1. **No Dashboard Needed**: You can add accounts without ever using bot.winu.app
2. **Bot Auto-Detects**: Bot queries database for active accounts on each signal
3. **No Restart Required**: Bot picks up new accounts automatically
4. **Parallel Execution**: Bot trades on ALL enabled accounts simultaneously
5. **Independent Settings**: Each account has its own risk limits and settings
6. **Order Tracking**: All orders stored in multi_account_orders table (for your records)

---

## 🔐 Security Notes

- API keys are encrypted using Fernet AES-128
- Keys never stored in plain text
- Encryption key: `API_KEY_ENCRYPTION_KEY` environment variable
- Only decrypted when executing trades

---

## ✅ Verification After Adding

```bash
# 1. Verify account was added
docker exec winu-bot-signal-postgres psql -U winu -d winudb -c "
  SELECT id, api_name, auto_trade_enabled 
  FROM user_api_keys 
  ORDER BY created_at DESC 
  LIMIT 1;
"

# 2. Wait for next signal and check bot logs
docker logs winu-bot-signal-trading-bot --tail 50 -f

# 3. You should see:
#    "🚀 Executing signal on multi-account system..."
#    "✅ Multi-account execution: X/Y accounts"
```

---

## 🎊 Summary

**To add another account for bot trading only:**

1. Run: `./add_trading_account.sh`
2. Enter your Binance API credentials
3. Set `auto_trade_enabled = true`
4. ✅ Done! Bot will trade on it automatically

**No dashboard tracking needed at bot.winu.app - the bot just trades in the background!**

---

*This approach adds accounts purely for bot trading services without requiring dashboard UI access.*





