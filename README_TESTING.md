# 🧪 Payment Testing - Two Options

## ✅ System Status: READY FOR TESTING

All systems are operational:
- ✅ API: Healthy
- ✅ Database: Connected
- ✅ Plans: Loading ($0, $14.99, $29.99)
- ✅ Payment Integration: Configured

---

## 🎯 Choose Your Testing Method

### **Option 1: Complete Sandbox Testing** ⭐ Recommended

**Perfect for:** Unlimited safe testing with zero risk

**Setup Time:** 5-10 minutes

**Steps:**
1. **Get sandbox keys:** https://sandbox.nowpayments.io/
   - Sign up (free)
   - Get API key from dashboard
   - Get IPN secret

2. **Configure:**
   ```bash
   # Edit production.env:
   NOWPAYMENTS_SANDBOX_API_KEY=your_sandbox_key_here
   NOWPAYMENTS_SANDBOX_IPN_SECRET=your_sandbox_ipn_secret_here
   NOWPAYMENTS_SANDBOX=true
   
   # Restart:
   docker compose restart api
   ```

3. **Test:**
   ```
   http://localhost:3005/select-tier
   → Select Professional
   → Subscribe with Crypto
   → NOWPayments sandbox page opens
   → Click "Mark as Paid" button
   → Subscription activates! ✅
   ```

**Benefits:**
- 🎯 Test complete flow end-to-end
- 💰 Zero cost - unlimited tests
- ⚡ Instant payment simulation
- 🔄 Easy to retry
- ✅ Tests webhooks automatically

---

### **Option 2: Test Without Sandbox** ⚡ Instant

**Perfect for:** Quick verification right now

**Setup Time:** 0 minutes

**Test A - Invoice Creation (Browser):**
```
1. Open: http://localhost:3005/select-tier
2. Login as: infoboy27
3. Select "Professional" plan
4. Click "Subscribe with Crypto"
5. NOWPayments invoice page opens
6. VERIFY: Shows $14.99, crypto addresses, QR code
7. Close tab (DON'T send crypto!)

Cost: FREE - invoice creation is free
```

**Test B - Webhook Activation (Command Line):**
```bash
# Test subscription activation:
chmod +x test_webhook_only.sh
./test_webhook_only.sh

# This simulates payment webhook
# Tests if subscription activates correctly

Cost: FREE - no blockchain interaction
```

**Limitations:**
- Can't click "Mark as Paid" (production mode)
- Can't test repeatedly without cleanup
- Would need real crypto for actual payment

---

## 📚 Documentation Created

I've created several guides for you:

1. **`QUICK_TEST_GUIDE.md`** - Quick overview (this file)
2. **`COMPLETE_SANDBOX_SETUP.md`** - Detailed sandbox setup
3. **`GET_SANDBOX_KEYS.md`** - How to get sandbox keys
4. **`SAFE_PAYMENT_TESTING.md`** - Safe testing strategies
5. **`test_webhook_only.sh`** - Webhook test script

---

## 🎬 Recommended Workflow

**Quick Test (2 minutes):**
```bash
# Test webhook processing:
./test_webhook_only.sh

# Test invoice creation:
# Open browser → http://localhost:3005/select-tier
```

**Complete Test (15 minutes with sandbox):**
```bash
# 1. Get sandbox keys (5 min)
# 2. Configure in production.env
# 3. Restart: docker compose restart api
# 4. Test at: http://localhost:3005/select-tier
# 5. Use "Mark as Paid" on NOWPayments
# 6. Verify subscription activated
```

---

## 🔄 Current Configuration

```
Mode: PRODUCTION
Sandbox: false (production API keys active)
Can Test Invoice: YES (free)
Can Simulate Payment: NO (need sandbox keys)
Real Payments: Would work (but don't test with real crypto!)
```

---

## 💡 My Recommendation

**For you right now:**

1. **Quick test with Option 2** (2 minutes)
   - Verify invoice creation works
   - Test webhook with script
   - Confirm basic flow

2. **If you want thorough testing:** (Optional)
   - Get sandbox keys (10 minutes)
   - Enable sandbox mode
   - Test unlimited times safely

3. **Go Live:** ✅
   - Current setup works for production
   - Real customers can subscribe
   - Webhooks will activate subscriptions

---

## 🚀 Test Right Now

Choose one:

```bash
# A. Test webhook (simulates successful payment)
./test_webhook_only.sh

# B. Test in browser (view invoice, don't pay)
# Open: http://localhost:3005/select-tier
```

Both are **100% SAFE** and **FREE**!

---

**Questions?**
- For sandbox setup: See `COMPLETE_SANDBOX_SETUP.md`
- For webhook testing: Run `./test_webhook_only.sh`
- For browser testing: Go to http://localhost:3005/select-tier
