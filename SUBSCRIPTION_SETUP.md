# Winu Bot Subscription System Setup

This document explains how to set up and configure the subscription system for Winu Bot Signal.

## Overview

The subscription system provides:
- Monthly/Yearly subscription plans via Stripe
- Subscription-based access control for trading signals
- Telegram group access for subscribers
- Customer portal for subscription management
- Webhook handling for subscription events

## Prerequisites

1. **Stripe Account**: Create a Stripe account at https://stripe.com
2. **Stripe Products**: Create subscription products in your Stripe dashboard
3. **Database**: PostgreSQL with the subscription fields migration applied

## Setup Steps

### 1. Stripe Configuration

#### Create Stripe Products
1. Log into your Stripe Dashboard
2. Go to Products → Create Product
3. Create two products:
   - **Monthly Premium**: $29.99/month
   - **Yearly Premium**: $299.99/year

#### Get Stripe Keys
1. Go to Developers → API Keys
2. Copy your:
   - Secret Key (starts with `sk_test_` or `sk_live_`)
   - Publishable Key (starts with `pk_test_` or `pk_live_`)

#### Set Up Webhooks
1. Go to Developers → Webhooks
2. Add endpoint: `https://your-domain.com/api/billing/webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook secret (starts with `whsec_`)

### 2. Environment Configuration

Update your `production.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_your_live_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 3. Database Migration

Run the subscription migration:

```bash
# Connect to your PostgreSQL database
psql -h your-db-host -U your-username -d your-database

# Run the migration
\i migrations/add_subscription_fields.sql
```

### 4. Update Stripe Plan IDs

In `apps/api/routers/billing.py`, update the plan IDs to match your Stripe products:

```python
SUBSCRIPTION_PLANS = {
    "monthly": SubscriptionPlan(
        id="price_your_monthly_price_id",  # Replace with your Stripe price ID
        name="Monthly Premium",
        price=29.99,
        # ...
    ),
    "yearly": SubscriptionPlan(
        id="price_your_yearly_price_id",  # Replace with your Stripe price ID
        name="Yearly Premium",
        price=299.99,
        # ...
    )
}
```

### 5. Deploy and Test

1. **Deploy the application** with the new subscription features
2. **Test the subscription flow**:
   - Create a test subscription
   - Verify webhook events are received
   - Test subscription access control
   - Test customer portal access

## Features

### Subscription Plans
- **Monthly Premium**: $29.99/month
- **Yearly Premium**: $299.99/year (20% discount)

### Access Control
- Trading signals require active subscription
- Dashboard access for subscribers
- Telegram group access for verified users

### Customer Portal
- Manage subscription
- Update payment method
- View billing history
- Cancel subscription

### Telegram Integration
- Link Telegram account with verification code
- Access to private trading group
- Automatic removal on subscription cancellation

## API Endpoints

### Authentication
- `GET /auth/subscription-info` - Get user subscription info

### Billing
- `GET /billing/plans` - Get available subscription plans
- `GET /billing/subscription` - Get user subscription details
- `POST /billing/checkout` - Create Stripe checkout session
- `GET /billing/customer-portal` - Get customer portal URL
- `POST /billing/webhook` - Stripe webhook handler

### Telegram
- `POST /telegram/link` - Generate Telegram linking code
- `POST /telegram/verify` - Verify Telegram linking code
- `GET /telegram/status` - Get Telegram account status
- `DELETE /telegram/unlink` - Unlink Telegram account

## Frontend Components

### Pages
- `/billing` - Subscription management page
- `/dashboard` - Updated with subscription status

### Components
- `SubscriptionStatus` - Shows current subscription status
- `TelegramLink` - Telegram account linking interface
- `BillingPage` - Complete subscription management

## Security Considerations

1. **Webhook Security**: Always verify Stripe webhook signatures
2. **Access Control**: Implement proper subscription checks
3. **Data Protection**: Encrypt sensitive subscription data
4. **Rate Limiting**: Implement rate limiting on subscription endpoints

## Monitoring

### Key Metrics to Monitor
- Subscription conversion rate
- Churn rate
- Payment failure rate
- Webhook processing success rate

### Logs to Watch
- Stripe webhook events
- Subscription status changes
- Payment failures
- Access control violations

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**
   - Check webhook URL is accessible
   - Verify webhook secret is correct
   - Check Stripe webhook logs

2. **Subscription Access Denied**
   - Verify subscription status in database
   - Check current_period_end is not expired
   - Verify Stripe subscription is active

3. **Telegram Linking Fails**
   - Check verification code expiry
   - Verify Telegram bot is running
   - Check user permissions

### Debug Commands

```bash
# Check subscription status
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-api.com/auth/subscription-info

# Test webhook endpoint
curl -X POST https://your-api.com/billing/webhook \
  -H "Content-Type: application/json" \
  -d '{"type": "test"}'
```

## Support

For issues with the subscription system:
1. Check application logs
2. Verify Stripe dashboard
3. Test webhook endpoints
4. Review database subscription records

## Next Steps

1. **Analytics**: Add subscription analytics dashboard
2. **Notifications**: Email notifications for subscription events
3. **Trial Periods**: Add free trial functionality
4. **Referrals**: Implement referral system
5. **Multi-tier Plans**: Add different subscription tiers
