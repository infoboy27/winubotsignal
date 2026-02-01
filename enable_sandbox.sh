#!/bin/bash
# Enable NOWPayments Sandbox Mode

echo "🧪 NOWPayments Sandbox Configuration"
echo "====================================="
echo ""

# Prompt for sandbox API key
read -p "Enter your SANDBOX API Key: " SANDBOX_API_KEY
read -p "Enter your SANDBOX IPN Secret: " SANDBOX_IPN_SECRET

if [ -z "$SANDBOX_API_KEY" ] || [ -z "$SANDBOX_IPN_SECRET" ]; then
    echo "❌ Error: Both API key and IPN secret are required"
    exit 1
fi

echo ""
echo "📝 Updating production.env..."

# Update production.env with sandbox keys
sed -i "s|^NOWPAYMENTS_SANDBOX_API_KEY=.*|NOWPAYMENTS_SANDBOX_API_KEY=$SANDBOX_API_KEY|" production.env
sed -i "s|^NOWPAYMENTS_SANDBOX_IPN_SECRET=.*|NOWPAYMENTS_SANDBOX_IPN_SECRET=$SANDBOX_IPN_SECRET|" production.env
sed -i "s|^NOWPAYMENTS_SANDBOX=.*|NOWPAYMENTS_SANDBOX=true|" production.env

echo "✅ Configuration updated!"
echo ""
echo "🔄 Restarting API container..."

docker compose down api
docker compose up -d api

echo ""
echo "⏳ Waiting for API to start..."
sleep 5

echo ""
echo "🔍 Verifying sandbox mode..."
SANDBOX_MODE=$(docker compose exec -T api printenv NOWPAYMENTS_SANDBOX)

if [ "$SANDBOX_MODE" = "true" ]; then
    echo "✅ Sandbox mode ENABLED!"
    echo ""
    echo "📊 Checking API logs..."
    docker compose logs api --tail=10 | grep -i "sandbox\|nowpayments"
    echo ""
    echo "🎉 Ready to test!"
    echo ""
    echo "📍 Test at: http://localhost:3005/select-tier"
    echo ""
    echo "What you'll get:"
    echo "  - Redirected to: sandbox.nowpayments.io"
    echo "  - 'Mark as Paid' button available"
    echo "  - Zero risk - no real crypto"
    echo "  - Unlimited tests!"
else
    echo "❌ Sandbox mode not enabled. Please check configuration."
fi

echo ""
echo "═══════════════════════════════════════"












