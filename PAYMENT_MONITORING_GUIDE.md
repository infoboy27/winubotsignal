# Payment Activation Monitoring - Issue Analysis

## 🔍 Problem Identified

You're experiencing **"Invalid payment session"** error after users complete subscription payments. This occurs at:

**File**: `/home/ubuntu/winubotsignal/apps/web/src/app/payment/success/page.tsx`  
**Line**: 21  
**Error**: `toast.error('Invalid payment session');`

### Root Cause

The error occurs when the payment success page doesn't receive a `session_id` URL parameter:

```typescript
const sessionIdParam = searchParams.get('session_id');
if (sessionIdParam) {
  // Success flow
} else {
  toast.error('Invalid payment session');  // ❌ THIS IS THE ERROR
  router.push('/');
}
```

## 🐛 Two Potential Issues

### Issue #1: Webhook Not Triggering Activation
**Location**: `/home/ubuntu/winubotsignal/apps/api/routers/crypto_subscriptions.py`

The webhook handlers receive payment notifications but may fail to:
1. Process the webhook correctly
2. Call `activate_subscription_after_payment()`
3. Update user subscription status

### Issue #2: Missing Session ID in Redirect
After payment is completed:
1. Payment provider redirects user back
2. The redirect may not include `session_id` parameter
3. Frontend shows "Invalid payment session" error

## 📊 Monitoring Solution Deployed

### Monitor Script: `monitor_payment_activation.py`

**Features**:
- ✅ Detects payments marked "completed" but user still "inactive"
- ✅ Shows payment-to-activation time gaps
- ✅ Tracks subscription events
- ✅ Real-time alerts for activation failures

### Usage:

```bash
# Quick check
./monitor.sh check

# Continuous monitoring (updates every 10 seconds)
./monitor.sh watch

# Continuous monitoring with custom interval (30 seconds)
./monitor.sh watch 30

# Check specific user
./monitor.sh user USER_ID

# Or use Python directly with env vars
POSTGRES_USER=winu POSTGRES_PASSWORD=winu250420 POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=winudb python3 monitor_payment_activation.py check
```

## 🔧 Recommended Fixes

### Fix #1: Add Webhook Logging Table

Create a table to track all incoming webhooks:

```sql
CREATE TABLE webhook_logs (
    id SERIAL PRIMARY KEY,
    payment_method VARCHAR(50),
    webhook_data JSONB,
    signature VARCHAR(500),
    signature_valid BOOLEAN,
    processing_status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_webhook_logs_created_at ON webhook_logs(created_at);
CREATE INDEX idx_webhook_logs_payment_method ON webhook_logs(payment_method);
CREATE INDEX idx_webhook_logs_processing_status ON webhook_logs(processing_status);
```

### Fix #2: Enhanced Error Handling in Webhooks

Update webhook handlers to:
1. Log all incoming webhooks
2. Validate webhook signature
3. Try activation with retry logic
4. Send alerts on failure

### Fix #3: Session ID Management

Ensure payment success redirect includes session_id:

```typescript
// After successful payment, redirect with session
const session_id = payment_data.session_id || payment_data.payment_id || payment_data.transaction_id;
window.location.href = `/payment/success?session_id=${session_id}`;
```

## 🚨 When Alert Triggers

The monitor will alert when:

**Condition 1**: Payment status = `completed`, `confirmed`, `finished`, or `paid`  
**AND**  
**Condition 2**: User subscription_status ≠ `active` OR subscription_tier ≠ paid plan

**What this means**: User paid, but activation webhook failed or didn't run.

## 📝 Manual Fix Process

If monitoring detects a gap:

### Option 1: Use Admin API Endpoint

```bash
curl -X POST http://localhost:8001/api/admin/subscriptions/activate-manual \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_id": USER_ID,
    "plan_id": "professional",
    "reason": "Manual activation - webhook failure"
  }'
```

### Option 2: Database Direct Fix

```sql
-- Update user subscription
UPDATE users 
SET 
  subscription_status = 'active',
  subscription_tier = 'professional',
  plan_id = 'professional',
  last_payment_date = NOW(),
  payment_due_date = NOW() + INTERVAL '30 days',
  subscription_renewal_date = NOW() + INTERVAL '30 days',
  subscription_updated_at = NOW()
WHERE id = USER_ID;

-- Create activation event
INSERT INTO subscription_events (user_id, event_type, event_data, created_at)
VALUES (
  USER_ID,
  'activated',
  '{
    "plan_id": "professional",
    "reason": "manual_activation_webhook_failure",
    "activated_at": "' || NOW() || '",
    "activated_by": "admin"
  }'::jsonb,
  NOW()
);
```

## 🎯 Next Steps

1. **Run the monitor** to catch future payment issues in real-time
2. **Add webhook logging** to track all incoming payment notifications
3. **Check webhook endpoints** are publicly accessible
4. **Verify webhook signatures** are configured correctly
5. **Add retry logic** for failed activations
6. **Set up alerts** (email/Slack/Discord) when gaps are detected

## 📊 Checking Webhook Delivery

### NOWPayments Webhook Check
- Dashboard: https://nowpayments.io/dashboard
- Settings → IPN/Webhooks
- Check webhook URL and recent deliveries

### Coinbase Commerce Webhook Check
- Dashboard: https://commerce.coinbase.com/dashboard
- Settings → Webhook subscriptions
- Check delivery attempts and failures

## 🔄 Testing Payment Flow

1. **Create test payment**
2. **Monitor activates** and watches for webhook
3. **Webhook arrives** → logged in database
4. **Activation runs** → user status changes
5. **Monitor confirms** → no gaps detected

## 📞 Emergency Manual Activation

If a user reports payment completed but no access:

```bash
# 1. Check their payment status
./monitor.sh user USER_ID

# 2. Verify payment in transactions
PGPASSWORD=winu250420 psql -h localhost -U winu -d winudb -c \\
  "SELECT * FROM payment_transactions WHERE user_id = USER_ID ORDER BY created_at DESC LIMIT 1;"

# 3. If payment confirmed, manually activate
PGPASSWORD=winu250420 psql -h localhost -U winu -d winudb -c \\
  "UPDATE users SET subscription_status='active', subscription_tier='professional' WHERE id=USER_ID;"
```

---

## 📁 Files Modified/Created

1. ✅ `/home/ubuntu/winubotsignal/monitor_payment_activation.py` - Main monitor script
2. ✅ `/home/ubuntu/winubotsignal/monitor.sh` - Wrapper script with env loading
3. 📄 This documentation

## 🎬 Start Monitoring Now

```bash
cd /home/ubuntu/winubotsignal
./monitor.sh watch
```

The monitor will continuously check for payment activation issues and alert you immediately when a problem is detected!



