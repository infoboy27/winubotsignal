# NOWPayments Integration Setup Guide

This guide will help you set up NOWPayments for cryptocurrency payments in your Winu trading bot.

## 🚀 Quick Start

### 1. Register for NOWPayments

1. **Visit**: [nowpayments.io](https://nowpayments.io)
2. **Create Account**: Sign up for a merchant account
3. **Complete KYC**: Complete the verification process
4. **Get API Credentials**: Access your API keys from the dashboard

### 2. Get Your Credentials

After account approval, you'll receive:
- **API Key**: Your merchant API key
- **Secret Key**: Your merchant secret key (if required)
- **IPN Secret**: For webhook verification
- **Merchant ID**: Your unique merchant identifier

### 3. Configure Environment Variables

Update your `production.env` file:

```bash
# NOWPayments Configuration
NOWPAYMENTS_API_KEY=your_actual_api_key_here
NOWPAYMENTS_SECRET_KEY=your_actual_secret_key_here
NOWPAYMENTS_IPN_SECRET=your_actual_ipn_secret_here
NOWPAYMENTS_SANDBOX=false  # Set to true for testing

# API Base URL for webhooks
API_BASE_URL=https://api.winu.app
```

### 4. Configure Webhooks

Set up webhook URL in your NOWPayments dashboard:
```
https://api.winu.app/api/crypto-subscriptions/webhooks/nowpayments
```

## 📋 Supported Cryptocurrencies

NOWPayments supports 300+ cryptocurrencies including:

### Popular Options:
- **Bitcoin (BTC)**
- **Ethereum (ETH)**
- **Tether (USDT)**
- **USD Coin (USDC)**
- **Binance Coin (BNB)**
- **Cardano (ADA)**
- **Solana (SOL)**
- **Polkadot (DOT)**
- **Polygon (MATIC)**
- **Litecoin (LTC)**

### Full List:
Access the full list via API: `GET /api/crypto-subscriptions/nowpayments/currencies`

## 🔧 API Endpoints

### Frontend Integration

**Base URL**: `https://api.winu.app/api/crypto-subscriptions`

#### Available Endpoints:

1. **GET /plans** - Get subscription plans with payment methods
2. **POST /create-payment** - Create payment (supports NOWPayments)
3. **GET /nowpayments/currencies** - Get available cryptocurrencies
4. **GET /nowpayments/estimate** - Get price estimate
5. **GET /nowpayments/payment/{payment_id}** - Check payment status
6. **POST /webhooks/nowpayments** - Webhook handler

### Example Usage:

```javascript
// Create NOWPayments payment
const response = await fetch('/api/crypto-subscriptions/create-payment', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    plan_id: 'pro',
    payment_method: 'nowpayments',
    pay_currency: 'btc'
  })
});

const data = await response.json();
// Returns payment address and instructions
```

## 💰 Fee Structure

### NOWPayments Fees:
- **Setup Fee**: Free
- **Transaction Fee**: 0.5% - 1% (based on volume)
- **Withdrawal Fee**: Network fees only
- **Minimum Payment**: Varies by cryptocurrency

### Comparison with Other Providers:

| Provider | Setup Fee | Transaction Fee | Crypto Support |
|----------|-----------|-----------------|----------------|
| **NOWPayments** | Free | 0.5-1% | 300+ |
| **Binance Pay** | Free | 0% | 40+ |
| **Coinbase Commerce** | Free | 1% | 7 |
| **Stripe Crypto** | Free | 2.9% + 30¢ | 2 |

## 🛠️ Testing

### 1. Sandbox Mode

Enable sandbox mode for testing:

```bash
NOWPAYMENTS_SANDBOX=true
```

### 2. Test Integration

```bash
curl -X POST https://api.winu.app/api/crypto-subscriptions/test-payment
```

### 3. Test Payment Flow

1. Select NOWPayments as payment method
2. Choose cryptocurrency (BTC recommended for testing)
3. Create payment
4. Use testnet addresses for testing

## 🔐 Security Features

### Webhook Verification:
```python
def verify_webhook_signature(payload: str, signature: str) -> bool:
    expected_signature = hmac.new(
        ipn_secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
```

### Payment Status Tracking:
- **waiting**: Payment created, waiting for funds
- **confirming**: Payment detected, confirming
- **finished**: Payment completed successfully
- **failed**: Payment failed or expired

## 📱 Frontend Integration

### Payment Method Selection:

```tsx
<button
  onClick={() => handlePayment('nowpayments', selectedCurrency)}
  className="bg-purple-600 text-white font-semibold py-3 px-4 rounded-lg"
>
  <CreditCard className="w-5 h-5 mr-2" />
  NOWPayments
</button>
```

### Currency Selection:

```tsx
<select
  value={selectedCurrency}
  onChange={(e) => setSelectedCurrency(e.target.value)}
>
  <option value="btc">Bitcoin (BTC)</option>
  <option value="eth">Ethereum (ETH)</option>
  <option value="usdt">Tether (USDT)</option>
  {/* ... more options */}
</select>
```

## 🚀 Deployment Steps

### 1. Update Environment Variables:
```bash
# Add NOWPayments configuration to your .env file
NOWPAYMENTS_API_KEY=your_api_key
NOWPAYMENTS_IPN_SECRET=your_ipn_secret
API_BASE_URL=https://api.winu.app
```

### 2. Restart Services:
```bash
docker restart winu-bot-signal-api
```

### 3. Test Integration:
```bash
curl -X POST https://api.winu.app/api/crypto-subscriptions/test-payment
```

### 4. Configure Webhooks:
- Set webhook URL in NOWPayments dashboard
- Test webhook delivery
- Verify signature validation

## 📊 Monitoring

### Payment Status Monitoring:
- Monitor payment confirmations
- Track failed payments
- Set up alerts for payment issues

### API Usage:
- Monitor API rate limits
- Track successful transactions
- Monitor webhook delivery

## 🔧 Troubleshooting

### Common Issues:

1. **Webhook Not Receiving**: Check webhook URL and signature verification
2. **Payment Not Confirming**: Verify minimum amounts and network status
3. **API Errors**: Check API key and rate limits
4. **Currency Not Supported**: Verify currency is available in NOWPayments

### Support:
- NOWPayments Support: [support.nowpayments.io](https://support.nowpayments.io)
- Documentation: [docs.nowpayments.io](https://docs.nowpayments.io)

## 🎯 Benefits of NOWPayments

### Advantages:
- **Wide Crypto Support**: 300+ cryptocurrencies
- **Non-custodial**: You control your funds
- **Low Fees**: 0.5-1% transaction fees
- **Easy Integration**: Simple API
- **Real-time Updates**: Instant payment notifications
- **Global Support**: Worldwide availability

### Perfect For:
- Accepting multiple cryptocurrencies
- International customers
- Lower transaction fees
- Non-custodial requirements
- Wide cryptocurrency support needs












