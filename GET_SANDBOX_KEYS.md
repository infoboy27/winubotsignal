# 🧪 Get NOWPayments Sandbox API Keys

## Step 1: Access NOWPayments Sandbox

Go to: **https://sandbox.nowpayments.io/**

## Step 2: Create Sandbox Account

1. Click "Sign Up" or "Register"
2. Fill in email and password
3. Verify email
4. Login to sandbox dashboard

## Step 3: Get Your Sandbox API Keys

Once logged in:

1. Go to **Settings** or **API Keys** section
2. You'll find:
   - **Sandbox API Key** (looks like: `SANDBOX-XXX-XXX-XXX-XXX`)
   - **IPN Secret** (for webhook verification)

3. Copy these keys

## Step 4: Configure Sandbox Keys

Add these to your `production.env` file:

```bash
# NOWPayments Sandbox Configuration (for testing)
NOWPAYMENTS_SANDBOX_API_KEY=YOUR_SANDBOX_KEY_HERE
NOWPAYMENTS_SANDBOX_IPN_SECRET=YOUR_SANDBOX_IPN_SECRET_HERE

# Toggle between sandbox/production
NOWPAYMENTS_SANDBOX=true  # Set to true for testing
```

## Step 5: Update Code to Support Sandbox Keys

The code needs to use different keys based on sandbox mode.

---

## 🚀 Quick Alternative: Test with Current Setup

If you want to test RIGHT NOW without waiting for sandbox keys, you can:

### **Option A: Test Invoice Creation (Free & Safe)**

This creates a real invoice but you don't have to pay it:

```bash
# 1. Go to browser
http://localhost:3005/select-tier

# 2. Select Professional plan

# 3. Click "Subscribe with Crypto"

# 4. You'll get redirected to NOWPayments invoice page
#    - Real invoice ID
#    - Real payment address
#    - Shows $14.99

# 5. DON'T send any crypto - just verify:
#    ✅ Invoice was created
#    ✅ Redirect works
#    ✅ Correct amount shown
#    ✅ Multiple crypto options

# 6. Close the page (invoice expires in 24 hours)
```

**Cost: FREE** - Invoice creation is free, you only pay if you send crypto

### **Option B: Test Webhook Manually (Free & Safe)**

Test subscription activation without creating invoice:

```bash
# Run the webhook test script
./test_webhook_only.sh

# This simulates payment confirmation
# Tests if subscription gets activated
# Completely free - no blockchain interaction
```

---

## 📋 What You Can Test Without Sandbox Keys

✅ **Can Test (Free):**
1. Plan selection UI
2. Payment page loading
3. Invoice creation (creates but don't pay)
4. Webhook processing (manual simulation)
5. Subscription activation logic
6. Database updates
7. Email notifications (if configured)

❌ **Can't Test Without Sandbox Keys:**
1. Automatic "Mark as Paid" button
2. Instant payment simulation
3. Testing multiple payment scenarios easily
4. Risk-free payment testing

---

## 💡 Recommendation

**For Complete Testing:**
1. Get sandbox keys (takes 5-10 minutes)
2. Test everything safely
3. Then switch to production

**For Quick Verification:**
1. Test invoice creation (view but don't pay)
2. Test webhook manually
3. Verify subscription activates
4. You're good to go live!

---

## 🔗 Useful Links

- **Sandbox Dashboard:** https://sandbox.nowpayments.io/
- **Sandbox API Docs:** https://documenter.getpostman.com/view/7907941/S1a32n38
- **Main Documentation:** https://nowpayments.io/doc/













