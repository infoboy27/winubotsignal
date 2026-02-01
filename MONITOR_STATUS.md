# ✅ Payment Activation Monitoring - ACTIVE

## 🎯 What's Running Now

A real-time monitor that tracks user activation after payment completion.

**Status**: ✅ **ACTIVE** (Running in background)  
**Check Interval**: 15 seconds  
**Started**: October 8, 2025

---

## 🔍 What It Monitors

### 1. Payment-to-Activation Gaps (PRIMARY)
Detects when:
- ✅ Payment status = `completed`, `confirmed`, `finished`, or `paid`
- ❌ BUT user subscription_status ≠ `active`
- ❌ OR user subscription_tier ≠ paid plan

**This is the "Invalid payment session" issue root cause!**

### 2. Recent Payments
Shows last 30 minutes of payment activity:
- Transaction IDs
- User IDs
- Payment methods
- Status changes
- Amounts

### 3. Subscription Events
Tracks activation events:
- When activation runs
- What data was used
- Success/failure status
- Time delays

---

## 🚨 Alert System

When a gap is detected, you'll see:

```
⚠️  PAYMENT ACTIVATION GAPS

User ID | Username | Plan | Payment Status | User Status | Activation Event | Payment Time
--------|----------|------|----------------|-------------|------------------|-------------
65      | cpvalera | prof | completed      | inactive    | ❌ No            | 2025-10-08 14:23:45
```

Then detailed user info for each affected user.

---

## 📊 Commands

### Check Current Status
```bash
cd /home/ubuntu/winubotsignal
./monitor.sh check
```

### Watch Continuously (Foreground)
```bash
./monitor.sh watch      # 10 second interval
./monitor.sh watch 30   # 30 second interval
```

### Check Specific User
```bash
./monitor.sh user USER_ID
```

### Stop Background Monitor
```bash
# Find and kill the background process
ps aux | grep monitor_payment
kill PID
```

---

## 🔧 The "Invalid Payment Session" Issue Explained

### The Error Location
**File**: `apps/web/src/app/payment/success/page.tsx`  
**Line**: 21

```typescript
const sessionIdParam = searchParams.get('session_id');
if (sessionIdParam) {
  setSessionId(sessionIdParam);
  setLoading(false);
  toast.success('Payment successful! Welcome to Winu Bot Signal!');
} else {
  toast.error('Invalid payment session');  // ❌ ERROR HERE
  router.push('/');
}
```

### Why It Happens

**Scenario 1: No session_id in URL**
- User completes payment
- Payment provider redirects to `/payment/success`
- BUT doesn't include `?session_id=xxx` parameter
- Frontend shows error

**Scenario 2: Webhook Failure**
- Payment completes successfully
- Webhook doesn't reach your server (firewall/DNS issue)
- OR webhook fails silently (exception in code)
- User subscription not activated
- No session created

### The Root Cause Chain

1. User pays → Payment provider marks payment as "completed"
2. Payment provider sends webhook to your server
3. **❌ FAILURE POINT**: Webhook handler at `/api/crypto-subscriptions/webhooks/nowpayments` or `/api/crypto-subscriptions/webhooks/coinbase-commerce`
   - Signature validation fails?
   - Database error?
   - Exception in `activate_subscription_after_payment()`?
4. User subscription not activated
5. User redirected to success page without proper session
6. **Result**: "Invalid payment session" error

---

## 🎯 What Happens When Monitor Detects an Issue

### Automatic Detection
Every 15 seconds, the monitor:
1. Queries `payment_transactions` for completed payments (last 2 hours)
2. Joins with `users` table
3. Checks if subscription_status is active
4. Checks if subscription_tier matches paid plan
5. Verifies activation event exists in `subscription_events`

### Alert Display
If gap found:
```
🚨 ALERT: 1 payment(s) completed but subscription not activated!

⚠️  DETAILED USER INFO FOR AFFECTED USERS:

User ID: 65
Username: cpvalera
Email: cpvalera@example.com
Status: inactive (should be active)
Tier: free (should be professional)
Plan ID: N/A
Last Payment: Never
```

### What You Should Do
1. Verify payment really completed in payment provider dashboard
2. Check webhook was sent and received
3. Manually activate user if legitimate payment:
   ```bash
   ./monitor.sh user 65  # Check status
   
   # If payment verified, activate manually
   PGPASSWORD=winu250420 psql -h localhost -U winu -d winudb -c "
   UPDATE users 
   SET subscription_status='active', 
       subscription_tier='professional',
       last_payment_date=NOW(),
       payment_due_date=NOW() + INTERVAL '30 days'
   WHERE id=65;"
   ```

---

## 📝 Database Tables Being Monitored

### `payment_transactions`
```
id | user_id | plan_id | amount_usd | status | payment_method | transaction_id | created_at
---|---------|---------|------------|--------|----------------|----------------|------------
```

### `users`
```
id | username | email | subscription_status | subscription_tier | last_payment_date
---|----------|-------|---------------------|-------------------|-------------------
```

### `subscription_events`
```
id | user_id | event_type | event_data | created_at
---|---------|------------|------------|------------
```

---

## 🔄 Next Time a Payment Happens

1. Monitor will detect the new `payment_transactions` row
2. If status changes to "completed" within 15 seconds
3. Monitor checks user subscription status
4. If NOT activated → **IMMEDIATE ALERT**
5. You can manually activate within minutes
6. User gets access quickly

---

## 📊 Background Process Info

The monitor is now running in the background. To check if it's still running:

```bash
ps aux | grep monitor_payment_activation
```

To see output:
```bash
tail -f nohup.out  # if redirected
# or just run in foreground:
./monitor.sh watch
```

---

## 🎬 Testing the Monitor

### Simulate a Gap (for testing)
```sql
-- Create a test payment marked as completed
INSERT INTO payment_transactions 
(user_id, plan_id, amount_usd, amount_usdt, status, payment_method, transaction_id, created_at)
VALUES 
(1, 'professional', 99.00, 99.00, 'completed', 'test', 'TEST_' || NOW()::TEXT, NOW());

-- Monitor should detect this within 15 seconds and alert
-- (assuming user 1 is not already on professional plan)
```

### Clean Up Test
```sql
DELETE FROM payment_transactions WHERE payment_method = 'test';
```

---

## 📞 Support Commands

### View All Payments
```bash
PGPASSWORD=winu250420 psql -h localhost -U winu -d winudb -c "
SELECT id, user_id, plan_id, status, payment_method, created_at 
FROM payment_transactions 
ORDER BY created_at DESC 
LIMIT 10;"
```

### View All Users
```bash
PGPASSWORD=winu250420 psql -h localhost -U winu -d winudb -c "
SELECT id, username, email, subscription_status, subscription_tier 
FROM users 
ORDER BY id DESC 
LIMIT 10;"
```

### View Subscription Events
```bash
PGPASSWORD=winu250420 psql -h localhost -U winu -d winudb -c "
SELECT id, user_id, event_type, created_at 
FROM subscription_events 
ORDER BY created_at DESC 
LIMIT 10;"
```

---

## ✅ Summary

**Monitor Status**: ✅ RUNNING (Background, 15s interval)  
**Purpose**: Detect payment-to-activation gaps in real-time  
**Primary Issue**: "Invalid payment session" after successful payment  
**Root Cause**: Webhook not activating user subscription  
**Solution**: Real-time detection + manual activation capability  

You are now actively monitoring for payment activation issues! 🎉

The monitor will catch any payments that complete but don't activate properly, allowing you to manually activate users and investigate webhook failures.



