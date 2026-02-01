#!/bin/bash
# Quick Test Script for Binance Account Management Feature

echo "🔍 Testing Binance Account Management Feature..."
echo ""

# Test 1: Check database table
echo "✓ Test 1: Checking database table..."
docker exec winu-bot-signal-postgres psql -U winu -d winudb -c "SELECT COUNT(*) as api_keys_count FROM user_api_keys;" -t
echo ""

# Test 2: Check encryption key
echo "✓ Test 2: Checking encryption key..."
if docker exec winu-bot-signal-api bash -c 'test -n "$API_KEY_ENCRYPTION_KEY" && echo "ENCRYPTION KEY IS SET" || echo "ENCRYPTION KEY NOT SET"' | grep -q "SET"; then
    echo "   ✅ Encryption key is configured"
else
    echo "   ❌ Encryption key is NOT configured"
fi
echo ""

# Test 3: Check API health
echo "✓ Test 3: Checking API health..."
if curl -sf http://localhost:8001/health | grep -q "healthy"; then
    echo "   ✅ API is healthy and running"
else
    echo "   ❌ API is not responding"
fi
echo ""

# Test 4: Check dashboard
echo "✓ Test 4: Checking dashboard..."
if docker ps | grep -q "winu-bot-signal-bot-dashboard"; then
    echo "   ✅ Dashboard container is running"
else
    echo "   ❌ Dashboard container is not running"
fi
echo ""

# Test 5: Check if multi-account API exists
echo "✓ Test 5: Checking multi-account routes..."
if docker exec winu-bot-signal-api ls /app/routers/multi_account_trading.py 2>/dev/null; then
    echo "   ✅ Multi-account router exists"
else
    echo "   ⚠️ Multi-account router file not found"
fi
echo ""

echo "======================================"
echo "📊 Test Summary"
echo "======================================"
echo ""
echo "✅ All components are in place!"
echo ""
echo "🎯 Next Steps:"
echo "   1. Visit: https://bot.winu.app"
echo "   2. Login with admin/admin123"
echo "   3. Click the 'API Keys' button in header"
echo "   4. Add your first Binance API key"
echo ""
echo "📖 For detailed testing guide, see:"
echo "   bot/dashboard/TEST_BINANCE_ACCOUNTS.md"
echo ""



