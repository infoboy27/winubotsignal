# 🧪 NOWPayments Payment Testing Guide

This guide shows you how to test the complete payment flow without using real cryptocurrency.

## 🎯 Testing Methods

### **Method 1: Sandbox Mode (Recommended)**

NOWPayments sandbox allows you to simulate payments with fake transactions.

#### Setup:
1. ✅ Sandbox mode is now **ENABLED** (`NOWPAYMENTS_SANDBOX=true`)
2. Using sandbox API: `https://api-sandbox.nowpayments.io/v1`
3. All payments are simulated (no real crypto needed)

#### Test the Flow:

**Option A: Automated Test Script**
```bash
# Run the automated test
python3 test_payment_flow.py

# This will:
# 1. Create a test payment/invoice
# 2. Get the invoice URL
# 3. Optionally simulate webhook confirmation
```

**Option B: Manual Browser Test**
```bash
# 1. Go to payment page
http://localhost:3005/select-tier

# 2. Select "Professional" plan ($14.99)

# 3. Click "Subscribe with Crypto"

# 4. You'll be redirected to NOWPayments sandbox page

# 5. In sandbox, you can:
#    - Select any cryptocurrency
#    - Click "Mark as Paid" (sandbox feature)
#    - Webhook will trigger automatically
```

**Option C: Direct API Test**
```bash
# Create a test payment via API
curl -X POST "http://localhost:8001/api/crypto-subscriptions/create-payment" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "plan_id": "professional",
    "payment_method": "nowpayments",
    "pay_currency": "btc"
  }'

# Response will include:
# {
#   "success": true,
#   "payment_data": {
#     "invoice_id": "1234567890",
#     "invoice_url": "https://nowpayments.io/payment/?iid=1234567890",
#     "order_id": "WINU_SUB_1_professional_1234567890",
#     "amount": 14.99,
#     "status": "waiting"
#   }
# }
```

### **Method 2: Simulate Webhook Manually**

If you just want to test the webhook processing without creating a real payment:

```bash
# Simulate a successful payment webhook
curl -X POST "http://localhost:8001/api/crypto-subscriptions/webhooks/nowpayments" \
  -H "Content-Type: application/json" \
  -H "x-nowpayments-sig: test_signature" \
  -d '{
    "invoice_id": "test_invoice_123",
    "invoice_status": "paid",
    "order_id": "WINU_SUB_1_professional_1696000000",
    "payment_status": "finished",
    "price_amount": 14.99,
    "price_currency": "usd"
  }'
```

## 📊 What to Check

### 1. **Payment Creation**
- ✅ Invoice is created successfully
- ✅ Invoice URL is returned
- ✅ Order ID follows format: `WINU_SUB_{user_id}_{plan_id}_{timestamp}`
- ✅ Amount matches plan price

### 2. **Payment Page Redirect**
- ✅ User is redirected to NOWPayments hosted page
- ✅ Payment page shows correct amount
- ✅ Multiple crypto options available
- ✅ Success/cancel URLs configured

### 3. **Webhook Processing**
- ✅ Webhook signature verified (if not in sandbox)
- ✅ Payment status extracted correctly
- ✅ User subscription activated
- ✅ Database updated with transaction

### 4. **User Dashboard**
- ✅ Subscription status changes to "active"
- ✅ Access granted to premium features
- ✅ Payment confirmation email sent (if configured)

## 🔍 Monitoring Test Results

### Check Database:
```sql
-- Check payment transactions
SELECT * FROM payment_transactions 
ORDER BY created_at DESC LIMIT 5;

-- Check user subscription status
SELECT id, username, subscription_tier, subscription_status, subscription_start_date
FROM users 
WHERE id = 1;

-- Check subscription events
SELECT * FROM subscription_events 
ORDER BY created_at DESC LIMIT 10;
```

### Check API Logs:
```bash
# Watch for payment creation
docker compose logs -f api | grep -i "nowpayments\|invoice\|payment"

# Watch for webhook processing
docker compose logs -f api | grep -i "webhook\|subscription.*activated"
```

## 🎬 Complete Test Scenario

Here's a step-by-step test you can run:

```bash
# 1. Enable sandbox mode (already done)
# NOWPAYMENTS_SANDBOX=true

# 2. Restart API
docker compose restart api

# 3. Run automated test
python3 test_payment_flow.py

# 4. Or test via browser:
#    - Go to http://localhost:3005/login
#    - Login as user: infoboy27
#    - Go to /select-tier
#    - Select Professional plan
#    - Click Subscribe
#    - Check payment details displayed
#    - If invoice URL, click to open NOWPayments page

# 5. In NOWPayments Sandbox:
#    - Select any cryptocurrency (BTC, ETH, USDT, etc.)
#    - You'll see fake wallet address
#    - Click "Mark as Paid" button (sandbox feature)
#    - Webhook fires automatically

# 6. Verify subscription activated:
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8001/api/subscriptions/info
```

## 🔄 Reset Test Data

To reset and test again:

```bash
# 1. Clear test payment records
docker compose exec postgres psql -U winu -d winudb -c \
  "DELETE FROM payment_transactions WHERE order_id LIKE 'WINU_SUB_%';"

# 2. Reset user subscription
docker compose exec postgres psql -U winu -d winudb -c \
  "UPDATE users SET subscription_tier='free', subscription_status='inactive' WHERE id=1;"

# 3. Run test again
python3 test_payment_flow.py
```

## 🚀 Switch Back to Production

When testing is complete:

```bash
# 1. Disable sandbox mode
# Edit production.env: NOWPAYMENTS_SANDBOX=false

# 2. Restart API
docker compose restart api

# 3. Verify production mode
curl http://localhost:8001/api/crypto-subscriptions/nowpayments/currencies | head -20
```

## 💡 Sandbox vs Production Differences

| Feature | Sandbox | Production |
|---------|---------|------------|
| API URL | `api-sandbox.nowpayments.io` | `api.nowpayments.io` |
| Real Crypto | ❌ No | ✅ Yes |
| Test Payments | ✅ Yes | ❌ No |
| Webhook Delivery | ✅ Yes | ✅ Yes |
| Mark as Paid | ✅ Available | ❌ Not Available |
| Transaction Fees | ❌ None | ✅ Yes |

## 📝 Notes

- Sandbox invoices expire after 24 hours (same as production)
- Sandbox API keys are different from production
- Test payments won't affect real blockchain
- Webhook signatures work same way in sandbox

## 🆘 Troubleshooting

**Issue**: "API key not configured"
- **Solution**: Check `production.env` has `NOWPAYMENTS_API_KEY` set

**Issue**: "Webhook signature invalid"
- **Solution**: In sandbox mode, update `NOWPAYMENTS_IPN_SECRET` or disable signature check

**Issue**: "Payment not activating subscription"
- **Solution**: Check webhook logs: `docker compose logs api | grep webhook`
- Verify order_id format: `WINU_SUB_{user_id}_{plan_id}_{timestamp}`

**Issue**: "Invoice URL not opening"
- **Solution**: Check if invoice was created successfully
- Verify `invoice_url` is in response
- Try the invoice_id directly: `https://nowpayments.io/payment/?iid={invoice_id}`












