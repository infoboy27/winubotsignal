#!/bin/bash
# Script to add a Binance account directly to the trading bot
# This adds the account for bot trading without requiring dashboard access

echo "🤖 Adding Binance Account to Trading Bot"
echo "=========================================="
echo ""

# Account Configuration
read -p "Account Name (e.g., 'Trading Account 2'): " ACCOUNT_NAME
read -p "Binance API Key: " API_KEY
read -s -p "Binance API Secret (hidden): " API_SECRET
echo ""
read -p "Account Type (futures/spot/both) [futures]: " ACCOUNT_TYPE
ACCOUNT_TYPE=${ACCOUNT_TYPE:-futures}
read -p "Is this testnet? (true/false) [false]: " TEST_MODE
TEST_MODE=${TEST_MODE:-false}
read -p "Max Position Size USD [1000]: " MAX_POSITION
MAX_POSITION=${MAX_POSITION:-1000}
read -p "Leverage (1-125) [10]: " LEVERAGE
LEVERAGE=${LEVERAGE:-10}
read -p "Max Daily Trades [5]: " MAX_TRADES
MAX_TRADES=${MAX_TRADES:-5}
read -p "Risk Per Trade (0.01-0.10) [0.02]: " MAX_RISK
MAX_RISK=${MAX_RISK:-0.02}
read -p "Enable Auto-Trading? (true/false) [true]: " AUTO_TRADE
AUTO_TRADE=${AUTO_TRADE:-true}
read -p "User ID (default: 1): " USER_ID
USER_ID=${USER_ID:-1}

echo ""
echo "📋 Account Configuration:"
echo "  Name: $ACCOUNT_NAME"
echo "  Type: $ACCOUNT_TYPE"
echo "  Testnet: $TEST_MODE"
echo "  Max Position: \$$MAX_POSITION"
echo "  Leverage: ${LEVERAGE}x"
echo "  Auto-Trade: $AUTO_TRADE"
echo ""

# Encrypt the API keys using Python
echo "🔐 Encrypting API credentials..."

ENCRYPTED_DATA=$(docker exec winu-bot-signal-api python3 -c "
import sys
sys.path.append('/app')
sys.path.append('/bot')
from services.api_key_encryption import get_encryption_service

encryption = get_encryption_service()
api_key_enc, api_secret_enc = encryption.encrypt_key_pair('$API_KEY', '$API_SECRET')
print(f'{api_key_enc}|||{api_secret_enc}')
")

if [ $? -ne 0 ]; then
    echo "❌ Error encrypting credentials"
    exit 1
fi

API_KEY_ENCRYPTED=$(echo "$ENCRYPTED_DATA" | cut -d'|' -f1)
API_SECRET_ENCRYPTED=$(echo "$ENCRYPTED_DATA" | cut -d'|' -f4)

echo "✅ Credentials encrypted"
echo ""

# Insert into database
echo "💾 Adding account to database..."

docker exec winu-bot-signal-postgres psql -U winu -d winudb <<EOF
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
    $USER_ID,
    'binance',
    '$API_KEY_ENCRYPTED',
    '$API_SECRET_ENCRYPTED',
    '$ACCOUNT_NAME',
    '$ACCOUNT_TYPE',
    $TEST_MODE,
    $AUTO_TRADE,
    true,
    $MAX_POSITION,
    $LEVERAGE,
    $MAX_TRADES,
    $MAX_RISK,
    0.05,
    true,
    'fixed',
    100.0
) RETURNING id, api_name, auto_trade_enabled;
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Account added successfully!"
    echo ""
    echo "📊 Verifying account in database..."
    docker exec winu-bot-signal-postgres psql -U winu -d winudb -c "
        SELECT id, api_name, account_type, test_mode, auto_trade_enabled, leverage, max_position_size_usd 
        FROM user_api_keys 
        ORDER BY created_at DESC 
        LIMIT 1;
    "
    echo ""
    echo "🤖 Bot Trading Status:"
    if [ "$AUTO_TRADE" = "true" ]; then
        echo "  ✅ Auto-trading is ENABLED"
        echo "  ✅ Bot will automatically trade on this account"
        echo "  ✅ Signals will be executed on ALL enabled accounts"
    else
        echo "  ⚠️  Auto-trading is DISABLED"
        echo "  ℹ️  To enable: UPDATE user_api_keys SET auto_trade_enabled=true WHERE id=X;"
    fi
    echo ""
    echo "📈 Next Signal Execution:"
    echo "  - Bot will detect this account automatically"
    echo "  - No restart required"
    echo "  - Check logs: docker logs winu-bot-signal-trading-bot"
    echo ""
    echo "🎯 Account added for bot trading only"
    echo "   (not tracked in bot.winu.app dashboard)"
else
    echo ""
    echo "❌ Error adding account to database"
    exit 1
fi





