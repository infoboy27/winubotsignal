# 🧪 Safe Payment Testing Guide

## ⚠️ Important: Production Mode Active

Your NOWPayments account is using **production mode** with a valid API key. This means:
- ✅ Real payment links will be created
- ⚠️ Any payments sent will be **REAL** cryptocurrency
- ⚠️ Invoice/payment IDs are tracked on real blockchain

---

## 🎯 Safe Testing Options

### **Option 1: Test with VERY Small Amount (Safest)**

Instead of $14.99, temporarily test with a minimal amount:

1. **Create a test plan** with $0.10 or $1.00
2. Complete the flow with real but minimal crypto
3. Verify webhook and subscription activation work
4. Cost: ~$1 in crypto fees + small test amount

### **Option 2: Test Flow Without Payment (Recommended)**

Test everything EXCEPT the actual crypto transfer:

#### **Test Steps:**

```bash
# 1. Test invoice creation (no payment required)
# Go to: http://localhost:3005/select-tier
# Select Professional plan
# Click "Subscribe with Crypto"
# Note the invoice URL you get redirected to

# 2. Verify invoice was created
curl http://localhost:8001/api/crypto-subscriptions/nowpayments/invoice/INVOICE_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. DO NOT send crypto yet - just verify:
#    ✅ Invoice URL works
#    ✅ Shows correct amount
#    ✅ Multiple crypto options available
#    ✅ Addresses are generated

# 4. Test webhook manually (simulate payment)
# See instructions below
```

### **Option 3: Manual Webhook Simulation**

Test subscription activation without creating real payment:

```bash
# 1. Simulate successful payment webhook
curl -X POST "http://localhost:8001/api/crypto-subscriptions/webhooks/nowpayments" \
  -H "Content-Type: application/json" \
  -H "x-nowpayments-sig: $(echo -n '{"order_id":"WINU_SUB_1_professional_'$(date +%s)'","payment_status":"finished"}' | openssl dgst -sha512 -hmac '1Mu7CI1nnCaq4OGU0ja3PxQv8xDuu3tt' | cut -d' ' -f2)" \
  -d '{
    "invoice_id": "test_'$(date +%s)'",
    "invoice_status": "paid",
    "order_id": "WINU_SUB_1_professional_'$(date +%s)'",
    "payment_status": "finished",
    "price_amount": 14.99,
    "price_currency": "usd",
    "pay_amount": 0.00015,
    "pay_currency": "btc"
  }'

# 2. Check if subscription activated
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT username, subscription_tier, subscription_status, subscription_start_date 
   FROM users WHERE id=1;"
```

---

## 🔍 What Each Step Tests

### ✅ Invoice Creation Test
**Tests:** API integration, invoice generation, redirect URL  
**Cost:** FREE  
**How:**
1. Go to payment page
2. Click "Subscribe"
3. Note the invoice URL
4. **DON'T** send crypto
5. Verify invoice shows on NOWPayments

### ✅ Webhook Processing Test  
**Tests:** Webhook handler, subscription activation, database updates  
**Cost:** FREE  
**How:** Use the manual webhook simulation above

### ✅ Complete End-to-End Test
**Tests:** Everything including real payment  
**Cost:** ~$15 + fees  
**How:**
1. Use smallest plan or create $0.50 test plan
2. Complete real payment
3. Verify subscription activates

---

## 🧪 Recommended Testing Approach

**Phase 1: Free Tests (Do These First)**
1. ✅ Verify invoice creation works (free)
2. ✅ Check invoice URL redirects properly (free)
3. ✅ Test webhook with manual call (free)
4. ✅ Verify subscription activates from webhook (free)

**Phase 2: Small Payment Test (Optional)**
1. Send $1 worth of crypto to test invoice
2. Verify real payment completes
3. Check webhook fires automatically
4. Confirm subscription activates

**Phase 3: Production Ready**
1. If Phase 1 & 2 work, production is ready
2. Real customers can subscribe
3. Webhooks will activate subscriptions automatically

---

## 📊 Verify Current Status

Check if the flow works without payment:

```bash
# Test 1: Plans endpoint
curl -s http://localhost:8001/onboarding/plans | python3 -m json.tool | head -20

# Test 2: Try creating invoice (will generate real invoice!)
# Only run if you want to test - invoice will expire in 24hrs if not paid
```

---

## 🎬 Manual Webhook Test Script

Save this as `test_webhook.sh`:

```bash
#!/bin/bash

# Configuration
USER_ID=1  # Your user ID
PLAN_ID="professional"
TIMESTAMP=$(date +%s)
ORDER_ID="WINU_SUB_${USER_ID}_${PLAN_ID}_${TIMESTAMP}"
IPN_SECRET="1Mu7CI1nnCaq4OGU0ja3PxQv8xDuu3tt"

# Create webhook payload
PAYLOAD='{
  "invoice_id": "test_'$TIMESTAMP'",
  "invoice_status": "paid",
  "order_id": "'$ORDER_ID'",
  "payment_status": "finished",
  "price_amount": 14.99,
  "price_currency": "usd",
  "pay_amount": 0.00015,
  "pay_currency": "btc",
  "actually_paid": 0.00015
}'

# Generate signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha512 -hmac "$IPN_SECRET" | cut -d' ' -f2)

echo "📤 Sending webhook with order ID: $ORDER_ID"
echo "🔐 Signature: $SIGNATURE"

# Send webhook
curl -X POST "http://localhost:8001/api/crypto-subscriptions/webhooks/nowpayments" \
  -H "Content-Type: application/json" \
  -H "x-nowpayments-sig: $SIGNATURE" \
  -d "$PAYLOAD"

echo -e "\n\n✅ Webhook sent! Checking subscription status..."

# Check subscription status
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT id, username, subscription_tier, subscription_status 
   FROM users WHERE id=$USER_ID;"
```

Then run:
```bash
chmod +x test_webhook.sh
./test_webhook.sh
```

---

## 💡 Key Points

1. **Invoice Creation = FREE** ✅
   - Creating invoices doesn't cost anything
   - Invoices expire if not paid (24 hours)
   - Safe to test invoice creation

2. **Sending Crypto = REAL MONEY** ⚠️
   - Only send crypto if you're ready
   - Double-check amounts
   - Verify addresses

3. **Webhook Testing = FREE** ✅
   - Can simulate webhooks for free
   - Tests subscription activation
   - No crypto needed

---

## 🔄 Get Sandbox API Keys (Optional)

To use real sandbox mode:

1. Go to [nowpayments.io/sandbox](https://nowpayments.io/sandbox)
2. Create sandbox account
3. Get sandbox API keys
4. Update `production.env`:
   ```bash
   NOWPAYMENTS_SANDBOX=true
   NOWPAYMENTS_API_KEY=sandbox_key_here
   ```
5. Restart API: `docker compose restart api`

---

**Current Configuration:**
- Mode: **Production** (real payments)
- API Key: **Valid** ✅
- Webhooks: **Configured** ✅
- Invoice Creation: **Working** ✅

**Recommendation:** Test webhook manually first (free), then do one $1 test payment to verify end-to-end.












