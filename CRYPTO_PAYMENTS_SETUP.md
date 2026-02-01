# Crypto Payments Setup Guide for Individuals

Since Binance Pay merchant accounts are for entities only, here are the best alternatives for individual crypto payment processing.

## 🎯 **Updated Subscription Tiers**

| Plan | Price | Features | Telegram Access |
|------|-------|----------|-----------------|
| **Basic** | $15/month | Basic signals, Email alerts, Discord access | ❌ No |
| **Pro** | $40/month | All signals, Telegram group, Priority support | ✅ Yes |
| **Premium** | $80/month | All features, VIP Telegram, 24/7 support | ✅ Yes |

## 🚀 **Payment Solutions for Individuals**

### 1. **Coinbase Commerce** (Recommended)
**Best for**: Easy setup, instant confirmation, multiple cryptocurrencies

#### Setup Steps:
1. **Register**: Go to [commerce.coinbase.com](https://commerce.coinbase.com)
2. **Create Account**: Use your personal Coinbase account
3. **Get API Key**: Generate API key in settings
4. **Set Webhook**: Configure webhook URL: `https://api.winu.app/api/crypto-subscriptions/webhooks/coinbase-commerce`

#### Configuration:
```bash
COINBASE_COMMERCE_API_KEY=your_api_key_here
COINBASE_COMMERCE_WEBHOOK_SECRET=your_webhook_secret_here
```

#### Supported Cryptocurrencies:
- USDC, BTC, ETH, LTC, BCH, DAI, USDT

### 2. **Stripe Crypto** (Alternative)
**Best for**: Credit card + crypto options, familiar interface

#### Setup Steps:
1. **Register**: Go to [stripe.com](https://stripe.com)
2. **Enable Crypto**: Enable cryptocurrency payments in dashboard
3. **Get API Keys**: Use existing Stripe keys
4. **Set Webhook**: Configure webhook URL: `https://api.winu.app/api/crypto-subscriptions/webhooks/stripe`

#### Configuration:
```bash
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

#### Supported Cryptocurrencies:
- USDC, USDT (via Stripe's crypto network)

### 3. **Direct Crypto Payments** (Manual)
**Best for**: Complete control, no fees, any cryptocurrency

#### Setup Steps:
1. **Create Wallets**: Set up wallets for each cryptocurrency
2. **Configure Addresses**: Add wallet addresses to environment
3. **Monitor Payments**: Use blockchain monitoring or manual verification

#### Configuration:
```bash
USDT_WALLET_ADDRESS=your_usdt_wallet_address
BTC_WALLET_ADDRESS=your_btc_wallet_address
ETH_WALLET_ADDRESS=your_eth_wallet_address
BNB_WALLET_ADDRESS=your_bnb_wallet_address
```

## 🔄 **User Registration & Payment Flow**

### New Registration Process:
1. **User Registration**: User creates account with email verification
2. **Plan Selection**: User chooses subscription tier (Basic/Pro/Premium)
3. **Payment Method**: User selects payment option (Coinbase/Stripe/Direct)
4. **Payment Processing**: Payment is processed based on selected method
5. **Subscription Activation**: User gets access to dashboard and Telegram groups

### API Endpoints:

#### Frontend Integration:
```javascript
// Create subscription payment
const response = await fetch('/api/crypto-subscriptions/create-payment', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${userToken}`
  },
  body: JSON.stringify({
    plan_id: 'pro',
    payment_method: 'coinbase_commerce'
  })
});

const paymentData = await response.json();
// Redirect user to paymentData.payment_data.payment_url
```

#### Available Endpoints:
- `POST /api/crypto-subscriptions/create-payment` - Create payment
- `GET /api/crypto-subscriptions/payment-status/{id}` - Check payment status
- `POST /api/crypto-subscriptions/activate-subscription` - Activate after payment
- `GET /api/crypto-subscriptions/user-subscription` - Get user's subscription
- `GET /api/crypto-subscriptions/telegram-invite` - Get Telegram invite link
- `POST /api/crypto-subscriptions/webhooks/coinbase-commerce` - Coinbase webhook
- `POST /api/crypto-subscriptions/webhooks/stripe` - Stripe webhook

## 📱 **Telegram Group Access**

### Group Structure:
- **Basic Plan**: Community Discord only
- **Pro Plan**: Access to Pro Telegram signals group
- **Premium Plan**: Access to VIP Telegram group + Pro group

### Telegram Groups:
- **Pro Group**: `https://t.me/winu_pro_signals`
- **VIP Group**: `https://t.me/winu_premium_vip`
- **Community**: `https://t.me/winu_community`

### Access Control:
```javascript
// Get Telegram invite based on subscription
const response = await fetch('/api/crypto-subscriptions/telegram-invite');
const data = await response.json();
// Redirect to data.invite_link
```

## 🛠️ **Implementation Steps**

### 1. Set Up Coinbase Commerce (Recommended):
```bash
# 1. Register at commerce.coinbase.com
# 2. Get API key from settings
# 3. Update environment variables
COINBASE_COMMERCE_API_KEY=your_api_key_here
COINBASE_COMMERCE_WEBHOOK_SECRET=your_webhook_secret_here

# 4. Restart services
docker restart winu-bot-signal-api
```

### 2. Test Integration:
```bash
curl -X POST https://api.winu.app/api/crypto-subscriptions/test-payment
```

### 3. Update Frontend:
- Use the new registration page: `/register-with-plan`
- Include plan selection in registration flow
- Add payment method selection
- Show Telegram invite after payment

## 💰 **Revenue Comparison**

### Payment Method Fees:
| Method | Setup Fee | Transaction Fee | Withdrawal Fee |
|--------|-----------|-----------------|----------------|
| **Coinbase Commerce** | Free | 1% | Free |
| **Stripe Crypto** | Free | 2.9% + 30¢ | Free |
| **Direct Crypto** | Free | 0% | Network fees only |

### Recommended Approach:
1. **Primary**: Coinbase Commerce (lowest fees, instant confirmation)
2. **Secondary**: Stripe Crypto (familiar interface, credit card backup)
3. **Fallback**: Direct crypto (zero fees, manual verification)

## 🔐 **Security Features**

### Webhook Verification:
```python
def verify_coinbase_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### Payment Monitoring:
- All payments are logged
- Webhook signatures are verified
- Failed payments are tracked
- Subscription status is updated in real-time

## 📊 **Analytics & Monitoring**

### Key Metrics:
- **Conversion Rate**: Registration → Payment completion
- **Payment Success Rate**: Successful vs failed payments
- **Plan Distribution**: Basic vs Pro vs Premium
- **Payment Method Usage**: Coinbase vs Stripe vs Direct

### Monitoring:
```bash
# Check payment logs
docker logs winu-bot-signal-api | grep "payment"

# Check webhook logs
docker logs winu-bot-signal-api | grep "webhook"

# Monitor subscription activations
docker logs winu-bot-signal-api | grep "subscription"
```

## 🚨 **Troubleshooting**

### Common Issues:

1. **"Coinbase Commerce not configured"**
   - Check API key is set in environment
   - Restart API service after updating env vars

2. **"Payment creation failed"**
   - Verify API credentials are correct
   - Check webhook URL is accessible

3. **"Webhook processing failed"**
   - Ensure webhook URL is correct: `https://api.winu.app/api/crypto-subscriptions/webhooks/coinbase-commerce`
   - Verify webhook secret matches

4. **"Telegram invite failed"**
   - Check user has active subscription
   - Verify Telegram bot is configured

### Support Resources:
- **Coinbase Commerce**: [support.coinbase.com](https://support.coinbase.com)
- **Stripe Crypto**: [support.stripe.com](https://support.stripe.com)
- **Your System**: Check logs and webhook status

## 🎉 **Success!**

With this setup, your users can:
- ✅ **Register with plan selection**
- ✅ **Pay with cryptocurrency** (USDC, BTC, ETH, etc.)
- ✅ **Get instant access** to dashboard
- ✅ **Join Telegram groups** based on subscription tier
- ✅ **Cancel anytime** through their account

Your Winu trading bot now supports **individual crypto payments** with multiple payment methods and tiered access to Telegram groups! 🚀

---

## 📞 **Next Steps**

1. **Choose Payment Method**: Start with Coinbase Commerce
2. **Set Up Credentials**: Get API keys and configure environment
3. **Test Integration**: Use test endpoints to verify setup
4. **Update Frontend**: Deploy new registration flow
5. **Monitor Payments**: Track conversion and success rates

Your crypto payment system is ready to accept individual subscriptions! 💰



