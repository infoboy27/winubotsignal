# 🧪 Complete Sandbox Testing Setup

## 🎯 Goal
Test the entire payment flow from start to finish with **ZERO RISK** using NOWPayments sandbox.

---

## 📝 Step-by-Step Setup

### **Step 1: Get Sandbox API Keys** (5 minutes)

1. **Visit:** https://sandbox.nowpayments.io/

2. **Create Account:**
   - Click "Sign Up"
   - Enter email and password
   - Verify your email

3. **Login to Sandbox Dashboard**

4. **Get Your API Keys:**
   - Navigate to **Settings** → **API Keys**
   - Copy the following:
     - ✅ **Sandbox API Key**
     - ✅ **IPN Secret** (for webhooks)

### **Step 2: Configure Sandbox Keys**

Edit `/home/ubuntu/winubotsignal/production.env`:

```bash
# Sandbox Keys (PASTE YOUR KEYS HERE)
NOWPAYMENTS_SANDBOX_API_KEY=YOUR_SANDBOX_KEY_HERE
NOWPAYMENTS_SANDBOX_IPN_SECRET=YOUR_SANDBOX_IPN_SECRET_HERE

# Enable sandbox mode
NOWPAYMENTS_SANDBOX=true
```

### **Step 3: Apply Configuration**

```bash
# Restart API to load new keys
docker compose restart api

# Verify sandbox mode is active
docker compose logs api --tail=20 | grep "SANDBOX"
# Should see: "🧪 NOWPayments initialized in SANDBOX mode"
```

---

## 🧪 Test the Complete Flow

Once sandbox keys are configured, here's the full test:

### **Test 1: Invoice Creation via Browser**

```bash
# 1. Open browser
http://localhost:3005/select-tier

# 2. Login if needed
Username: infoboy27

# 3. Select "Professional" plan ($14.99)

# 4. Click "Subscribe with Crypto"

# 5. You'll be redirected to NOWPayments sandbox page
URL will be: https://nowpayments.io/payment/?iid=SANDBOX_INVOICE_ID
```

### **Test 2: Simulate Payment on NOWPayments**

On the NOWPayments sandbox payment page:

1. **Select any cryptocurrency** (e.g., BTC, USDT, ETH)

2. **You'll see:**
   - Fake wallet address
   - Amount to send
   - QR code
   - Timer

3. **Look for sandbox features:**
   - **"Mark as Paid"** button
   - **"Simulate Payment"** button
   - **Admin controls** (sandbox only)

4. **Click "Mark as Paid"** or "Simulate Payment"

5. **Webhook fires automatically!**
   - NOWPayments sends webhook to your server
   - Server processes payment
   - Subscription activates

### **Test 3: Verify Subscription Activated**

```bash
# Check subscription status
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT id, username, subscription_tier, subscription_status, payment_due_date 
   FROM users WHERE username='infoboy27';"

# Expected result:
# subscription_tier: professional (or pro/paid depending on schema)
# subscription_status: active
```

### **Test 4: Check Webhook Logs**

```bash
# View webhook processing
docker compose logs api | grep -i "webhook\|subscription.*activated"

# Should see:
# ✅ "NOWPayments webhook received"
# ✅ "Subscription activated for user 1, plan professional"
```

---

## 🎬 Complete Test Checklist

Use this checklist to verify everything:

- [ ] **Step 1:** Sandbox keys configured
- [ ] **Step 2:** API restarted with sandbox mode
- [ ] **Step 3:** Logs show "SANDBOX mode"
- [ ] **Step 4:** Can access /select-tier page
- [ ] **Step 5:** Plans show correct prices
- [ ] **Step 6:** Clicking subscribe creates invoice
- [ ] **Step 7:** Redirect to NOWPayments works
- [ ] **Step 8:** Invoice shows $14.99
- [ ] **Step 9:** Multiple crypto options available
- [ ] **Step 10:** "Mark as Paid" button visible (sandbox)
- [ ] **Step 11:** Clicking button simulates payment
- [ ] **Step 12:** Webhook received and logged
- [ ] **Step 13:** Subscription status = active
- [ ] **Step 14:** User gains premium access

---

## 🔄 Quick Commands

```bash
# Enable sandbox
sed -i 's/NOWPAYMENTS_SANDBOX=false/NOWPAYMENTS_SANDBOX=true/' production.env
docker compose restart api

# Disable sandbox (back to production)
sed -i 's/NOWPAYMENTS_SANDBOX=true/NOWPAYMENTS_SANDBOX=false/' production.env
docker compose restart api

# Check current mode
docker compose logs api | grep "NOWPayments initialized"
# Sandbox: "🧪 NOWPayments initialized in SANDBOX mode"
# Production: "💰 NOWPayments initialized in PRODUCTION mode"

# Watch webhook processing live
docker compose logs -f api | grep -i webhook
```

---

## 📊 What Gets Tested

### **Frontend → Backend:**
- ✅ Plan selection
- ✅ Payment form
- ✅ API authentication
- ✅ Invoice creation request

### **Backend → NOWPayments:**
- ✅ Invoice API call
- ✅ Invoice URL generation
- ✅ Success/cancel URL configuration

### **NOWPayments → User:**
- ✅ Payment page display
- ✅ Crypto address generation
- ✅ QR code display
- ✅ Payment simulation (sandbox)

### **NOWPayments → Backend (Webhook):**
- ✅ Webhook delivery
- ✅ Signature verification
- ✅ Payment data parsing
- ✅ Subscription activation

### **Backend → Database:**
- ✅ Transaction record created
- ✅ User subscription updated
- ✅ Subscription events logged

### **Backend → User:**
- ✅ Dashboard access granted
- ✅ Premium features unlocked
- ✅ Confirmation email sent

---

## 🚀 After Successful Testing

Once all tests pass:

1. **Switch back to production**
   ```bash
   NOWPAYMENTS_SANDBOX=false
   ```

2. **Configure webhook in production dashboard**
   ```
   URL: https://api.winu.app/api/crypto-subscriptions/webhooks/nowpayments
   ```

3. **Your payment system is LIVE!** 🎉

---

## 💡 Pro Tips

1. **Test Multiple Times:** Sandbox allows unlimited tests
2. **Test Different Cryptos:** Try BTC, USDT, ETH in sandbox
3. **Test Failures:** Try canceling payments to test cancel flow
4. **Monitor Logs:** Keep `docker compose logs -f api` running during tests
5. **Database Checks:** Verify each step writes to database correctly

---

## 🆘 Troubleshooting

**"Invalid API key" in sandbox:**
- Make sure `NOWPAYMENTS_SANDBOX_API_KEY` is set
- Verify you copied the **sandbox** key, not production key
- Sandbox keys start with different prefix than production

**Webhook not received:**
- Check `docker compose logs api | grep webhook`
- Verify IPN secret matches
- In sandbox, webhooks might be delayed 1-2 minutes

**Subscription not activating:**
- Check order_id format: `WINU_SUB_{user_id}_{plan_id}_{timestamp}`
- Verify payment_status is "finished" or "paid"
- Check webhook logs for parsing errors

---

**Ready to Start?**

1. Get your sandbox keys from: https://sandbox.nowpayments.io/
2. Add them to `production.env`
3. Run: `docker compose restart api`
4. Test at: http://localhost:3005/select-tier

**Estimated Time:** 10-15 minutes for complete testing












