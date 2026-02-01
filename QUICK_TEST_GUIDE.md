# ⚡ Quick Payment Testing Guide

## 🎯 Two Ways to Test

---

## ✅ **Option 1: Full Sandbox Testing (Recommended)**

### **What You Need:** (5 minutes to set up)
- Sandbox API keys from NOWPayments

### **Steps:**

**1. Get Sandbox Keys:**
```
Visit: https://sandbox.nowpayments.io/
Sign up → Login → Get API Keys from dashboard
```

**2. Add Keys to Configuration:**
```bash
# Edit production.env, find this section:
NOWPAYMENTS_SANDBOX_API_KEY=PASTE_YOUR_SANDBOX_KEY_HERE
NOWPAYMENTS_SANDBOX_IPN_SECRET=PASTE_YOUR_SANDBOX_IPN_SECRET_HERE
NOWPAYMENTS_SANDBOX=true
```

**3. Restart API:**
```bash
docker compose restart api
```

**4. Test in Browser:**
```
1. Go to: http://localhost:3005/select-tier
2. Select "Professional" ($14.99)
3. Click "Subscribe with Crypto"
4. You'll be redirected to NOWPayments sandbox
5. Click "Mark as Paid" button (sandbox feature)
6. Subscription activates automatically!
```

### **Benefits:**
- ✅ 100% Safe - No real crypto
- ✅ Unlimited tests
- ✅ Instant confirmation
- ✅ "Mark as Paid" button
- ✅ Tests complete flow

---

## ✅ **Option 2: Test Without Sandbox Keys (Right Now)**

### **What You Can Test Immediately:**

**Test A: Invoice Creation (Free)**
```bash
# 1. Browser test:
http://localhost:3005/select-tier

# 2. Select Professional plan

# 3. Click "Subscribe with Crypto"

# 4. You'll get redirected to NOWPayments invoice page
#    - Real invoice will be created
#    - Shows $14.99
#    - Shows crypto addresses
#    - DON'T send any crypto!

# 5. Just verify the invoice page works
#    Then close the tab

# Cost: FREE (invoice expires in 24hrs if not paid)
```

**Test B: Webhook Simulation (Free)**
```bash
# Test subscription activation without payment
./test_webhook_only.sh

# This simulates a successful payment
# Tests if webhook activates subscription
# Cost: FREE - no blockchain interaction
```

### **Benefits:**
- ✅ Instant - no signup needed
- ✅ Free - no costs
- ✅ Tests most of the flow
- ❌ Can't test actual payment confirmation

---

## 📊 Comparison

| Feature | Sandbox Keys | Without Sandbox |
|---------|--------------|-----------------|
| Setup Time | 5-10 minutes | 0 minutes |
| Cost | FREE forever | FREE for invoice |
| Real Payments | ❌ Simulated | ⚠️ Would be real |
| "Mark as Paid" | ✅ Yes | ❌ No |
| Complete Flow | ✅ 100% | 🟡 95% |
| Webhook Test | ✅ Auto | 🟡 Manual |

---

## 🚀 My Recommendation

### **For Quick Verification:**
Use **Option 2** right now:
1. Test invoice creation (just view, don't pay)
2. Run `./test_webhook_only.sh` to test activation
3. Takes 2 minutes total

### **For Thorough Testing:**
Use **Option 1**:
1. Spend 5 minutes getting sandbox keys
2. Test complete flow unlimited times
3. Perfect confidence before going live

---

## 🎬 Quick Start Commands

### **Test Right Now (No Setup):**
```bash
# View invoice creation:
# Open: http://localhost:3005/select-tier
# Click Professional → Subscribe (view only, don't pay)

# Test webhook:
chmod +x test_webhook_only.sh
./test_webhook_only.sh
```

### **Enable Sandbox (After Getting Keys):**
```bash
# 1. Edit production.env with your sandbox keys

# 2. Enable sandbox mode:
sed -i 's/NOWPAYMENTS_SANDBOX=false/NOWPAYMENTS_SANDBOX=true/' production.env

# 3. Restart:
docker compose restart api

# 4. Test:
# Open: http://localhost:3005/select-tier
# Select plan → Subscribe → Mark as Paid on NOWPayments
```

---

## 🔍 Verify Everything Works

After testing (either option), verify:

```bash
# Check subscription activated
docker compose exec postgres psql -U winu -d winudb -c \
  "SELECT id, username, subscription_tier, subscription_status 
   FROM users WHERE id=1;"

# Should show subscription_tier = active after test
```

---

## 💡 Current Status

- ✅ **Code Updated:** Supports both sandbox and production keys
- ✅ **Invoice API:** Working  
- ✅ **Webhook Handler:** Ready
- ✅ **Production Mode:** Currently active
- ⏳ **Sandbox Keys:** Need to be added (optional)

---

## 🆘 Need Help?

**Getting Sandbox Keys:**
- See: `GET_SANDBOX_KEYS.md`

**Complete Setup:**
- See: `COMPLETE_SANDBOX_SETUP.md`

**Safe Testing:**
- See: `SAFE_PAYMENT_TESTING.md`

**Just test webhook:**
```bash
./test_webhook_only.sh
```

---

**Ready to test? Pick your option above!** 🚀












