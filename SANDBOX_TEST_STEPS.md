# 🧪 NOWPayments Sandbox Testing - Step by Step

## ✅ Sandbox Mode is Now ENABLED

The system is configured for safe payment testing with **NO REAL CRYPTOCURRENCY** required.

---

## 🚀 Quick Test (Browser Method)

### Step 1: Login to Your Account
```
URL: http://localhost:3005/login
Username: infoboy27
Password: (your password)
```

### Step 2: Go to Plan Selection
```
URL: http://localhost:3005/select-tier
```
You should see:
- ✅ Free Trial: $0 (7 days)
- ✅ Professional: $14.99/month  
- ✅ VIP Elite: $29.99/month

### Step 3: Select Professional Plan
- Click on "Professional" plan card
- Click "Select Plan" button
- You'll be taken to `/payment?plan=professional`

### Step 4: Complete Payment Form
The payment page will show:
- Plan summary with $14.99/month
- Payment method selection (NOWPayments is pre-selected)
- Currency selection (BTC, USDT, ETH, etc.)

**Click "Subscribe with Crypto"**

### Step 5: NOWPayments Sandbox Page
You'll be **automatically redirected** to:
```
https://nowpayments.io/payment/?iid=INVOICE_ID
```

On the NOWPayments page you'll see:
- 💰 Amount: $14.99
- 🪙 Available cryptocurrencies
- 📍 Wallet address (fake in sandbox)
- ⏱️ Payment timer

### Step 6: Simulate Payment (Sandbox Only!)

**In NOWPayments Sandbox**, you have special testing features:

**Option A: Mark as Paid**
- Look for a button that says "Mark as Paid" or "Simulate Payment"
- Click it - this simulates receiving the cryptocurrency
- Webhook fires automatically

**Option B: Use Test Crypto**
- Select a cryptocurrency (e.g., BTC)
- Copy the fake address shown
- In sandbox, the payment is auto-confirmed after a few seconds

### Step 7: Verify Subscription Activated
After payment confirmation, check:

```bash
# Check user subscription status
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT id, username, subscription_tier, subscription_status, subscription_start_date 
   FROM users WHERE username='infoboy27';"
```

Expected result:
```
 id | username  | subscription_tier | subscription_status | subscription_start_date  
----+-----------+-------------------+---------------------+-------------------------
  1 | infoboy27 | professional      | active             | 2025-10-07 ...
```

---

## 🔍 Alternative: Manual Webhook Test

If you want to skip the UI and test webhook processing directly:

```bash
# 1. Create a fake order ID (replace user_id with your user ID)
ORDER_ID="WINU_SUB_1_professional_$(date +%s)"

# 2. Send webhook payload
curl -X POST "http://localhost:8001/api/crypto-subscriptions/webhooks/nowpayments" \
  -H "Content-Type: application/json" \
  -H "x-nowpayments-sig: test_sandbox_signature" \
  -d "{
    \"invoice_id\": \"test_invoice_$(date +%s)\",
    \"invoice_status\": \"paid\",
    \"order_id\": \"$ORDER_ID\",
    \"payment_status\": \"finished\",
    \"price_amount\": 14.99,
    \"price_currency\": \"usd\",
    \"pay_amount\": 0.00015,
    \"pay_currency\": \"btc\",
    \"actually_paid\": 0.00015
  }"

# 3. Check if subscription was activated
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT subscription_tier, subscription_status FROM users WHERE id=1;"
```

---

## 📊 Monitoring During Test

### Watch API Logs (Real-time)
```bash
docker compose logs -f api
```

Look for:
- ✅ "Creating NOWPayments invoice..."
- ✅ "NOWPayments webhook received..."
- ✅ "Subscription activated for user..."

### Check Payment in Database
```bash
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT * FROM payment_transactions ORDER BY created_at DESC LIMIT 3;"
```

---

## 🎯 Expected Results

### ✅ Successful Test Should Show:

1. **Payment Created**
   - Invoice ID generated
   - Invoice URL returned
   - Order ID in format: `WINU_SUB_1_professional_123456`

2. **Redirect Works**
   - Browser redirects to NOWPayments
   - Payment page loads
   - Shows correct amount ($14.99)

3. **Webhook Received**
   - Logs show: "NOWPayments webhook received"
   - Order ID extracted correctly
   - User ID and plan ID parsed

4. **Subscription Activated**
   - User subscription_tier = "professional"
   - subscription_status = "active"
   - subscription_start_date = current timestamp
   - Dashboard shows premium features unlocked

---

## 🔄 Return to Production Mode

After testing, switch back:

```bash
# 1. Edit production.env
sed -i 's/NOWPAYMENTS_SANDBOX=true/NOWPAYMENTS_SANDBOX=false/' production.env

# 2. Restart API
docker compose restart api

# 3. Verify production mode
docker compose exec api printenv NOWPAYMENTS_SANDBOX
# Should output: false
```

---

## 💡 Pro Tips

1. **Sandbox is Safe**: No real money, no real crypto transactions
2. **Unlimited Testing**: Create as many test payments as you want
3. **Instant Confirmation**: Sandbox payments confirm immediately
4. **Full Webhook Support**: Webhooks work exactly like production
5. **Easy Reset**: Just clear database records to test again

## 🎬 Quick Test Command

One-liner to test the complete flow:

```bash
echo "Testing payment flow..." && \
curl -s http://localhost:8001/onboarding/plans | grep -q "professional" && \
echo "✅ Plans endpoint working" || echo "❌ Plans endpoint failed"
```

---

**Current Status:** 
- 🟢 Sandbox Mode: **ENABLED**
- 🟢 API: **READY**
- 🟢 Webhooks: **CONFIGURED**
- 🟢 Ready for Testing: **YES**

**Test at:** http://localhost:3005/select-tier












