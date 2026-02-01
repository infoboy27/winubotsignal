#!/bin/bash
# Safe Webhook Testing Script - Tests subscription activation WITHOUT real payment

echo "🧪 Testing NOWPayments Webhook Processing"
echo "=========================================="
echo ""

# Configuration
USER_ID=1  # Change this to your user ID
PLAN_ID="professional"
TIMESTAMP=$(date +%s)
ORDER_ID="WINU_SUB_${USER_ID}_${PLAN_ID}_${TIMESTAMP}"
IPN_SECRET="1Mu7CI1nnCaq4OGU0ja3PxQv8xDuu3tt"

# Create webhook payload
PAYLOAD=$(cat <<EOF
{"invoice_id":"test_${TIMESTAMP}","invoice_status":"paid","order_id":"${ORDER_ID}","payment_status":"finished","price_amount":14.99,"price_currency":"usd","pay_amount":0.00015,"pay_currency":"btc","actually_paid":0.00015}
EOF
)

# Generate proper HMAC-SHA512 signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha512 -hmac "$IPN_SECRET" | awk '{print $2}')

echo "📋 Test Configuration:"
echo "   User ID: $USER_ID"
echo "   Plan: $PLAN_ID"
echo "   Order ID: $ORDER_ID"
echo ""

echo "📤 Sending test webhook..."
echo "   Payload: $PAYLOAD"
echo "   Signature: $SIGNATURE"
echo ""

# Send webhook
RESPONSE=$(curl -s -X POST "http://localhost:8001/api/crypto-subscriptions/webhooks/nowpayments" \
  -H "Content-Type: application/json" \
  -H "x-nowpayments-sig: $SIGNATURE" \
  -d "$PAYLOAD")

echo "📬 Webhook Response:"
echo "   $RESPONSE"
echo ""

# Wait a moment for processing
sleep 2

echo "🔍 Checking subscription status..."
docker compose exec -T postgres psql -U winu -d winudb << EOF
SELECT 
  id, 
  username, 
  subscription_tier, 
  subscription_status,
  subscription_start_date
FROM users 
WHERE id=$USER_ID;
EOF

echo ""
echo "📊 Recent Subscription Events:"
docker compose exec -T postgres psql -U winu -d winudb << EOF
SELECT 
  event_type,
  subscription_tier,
  created_at
FROM subscription_events 
WHERE user_id=$USER_ID 
ORDER BY created_at DESC 
LIMIT 5;
EOF

echo ""
echo "✅ Test Complete!"
echo ""
echo "Expected Result:"
echo "  - subscription_tier should be: professional"
echo "  - subscription_status should be: active"
echo "  - subscription_start_date should be: recent timestamp"












