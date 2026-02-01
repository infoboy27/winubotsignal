'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Check, Loader2, CreditCard } from 'lucide-react';
import toast from 'react-hot-toast';

interface SubscriptionPlan {
  id: string;
  name: string;
  price_usd: number;
  price_usdt: number;
  interval: string;
  features: string[];
  telegram_access: boolean;
  support_level: string;
}

function PaymentContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const planId = searchParams.get('plan');
  
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [telegramUserId, setTelegramUserId] = useState('');
  const [telegramUsername, setTelegramUsername] = useState('');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState('nowpayments');
  const [selectedCurrency, setSelectedCurrency] = useState('usdc');
  const [paymentDetails, setPaymentDetails] = useState<any>(null);

  useEffect(() => {
    if (planId) {
      fetchPlanDetails(planId);
    } else {
      toast.error('No plan selected');
      router.push('/select-tier');
    }
  }, [planId, router]);

  const fetchPlanDetails = async (planId: string) => {
    try {
      const response = await fetch('/api/subscriptions/plans');
      if (response.ok) {
        const plans = await response.json();
        const plan = plans.find((p: SubscriptionPlan) => p.id === planId);
        if (plan) {
          setSelectedPlan(plan);
        } else {
          toast.error('Invalid plan selected');
          router.push('/select-tier');
        }
      } else {
        toast.error('Failed to load plan details');
        router.push('/select-tier');
      }
    } catch (error) {
      toast.error('Failed to load plan details');
      router.push('/select-tier');
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async () => {
    if (!selectedPlan) return;

    setProcessing(true);
    try {
      // Get authentication token from localStorage
      const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
      
      if (!token) {
        toast.error('Please log in to continue');
        router.push('/login');
        return;
      }

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      const response = await fetch('/api/crypto-subscriptions/create-payment', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          plan_id: selectedPlan.id,
          payment_method: selectedPaymentMethod,
          pay_currency: selectedCurrency,
        }),
      });

      const result = await response.json();

      if (result.success) {
        if (result.payment_data.payment_url) {
          toast.success('Redirecting to payment...');
          window.location.href = result.payment_data.payment_url;
        } else if (result.payment_data.pay_address) {
          // NOWPayments - show payment address
          toast.success('Payment created! Please send crypto to the address shown.');
          setPaymentDetails(result.payment_data);
          console.log('Payment details:', result.payment_data);
        } else {
          toast.success('Payment created successfully!');
        }
      } else {
        toast.error(result.message || 'Failed to create payment');
      }
    } catch (error) {
      toast.error('Failed to process payment');
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading payment details...</p>
        </div>
      </div>
    );
  }

  if (!selectedPlan) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Plan not found</p>
          <button
            onClick={() => router.push('/select-tier')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          >
            Back to Plan Selection
          </button>
        </div>
      </div>
    );
  }

  // Show payment details if payment was created
  if (paymentDetails) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8 text-green-600" />
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Payment Created!</h1>
              <p className="text-gray-600">Send {selectedCurrency.toUpperCase()} to the address below</p>
            </div>

            <div className="space-y-6">
              {/* Payment Address */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Payment Address</h3>
                <div className="bg-white border-2 border-gray-300 rounded-lg p-4 break-all font-mono text-sm">
                  {paymentDetails.pay_address}
                </div>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(paymentDetails.pay_address);
                    toast.success('Address copied to clipboard!');
                  }}
                  className="mt-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  Copy Address
                </button>
              </div>

              {/* Amount */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Amount to Send</h3>
                <div className="text-3xl font-bold text-gray-900">
                  {paymentDetails.amount} {selectedCurrency.toUpperCase()}
                </div>
                <p className="text-sm text-gray-600 mt-1">
                  ≈ ${paymentDetails.price_amount || selectedPlan?.price_usd} USD
                </p>
              </div>

              {/* Order ID */}
              <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Order ID</h3>
                <div className="font-mono text-sm text-gray-900">
                  {paymentDetails.order_id}
                </div>
              </div>

              {/* Instructions */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <h3 className="font-semibold text-blue-900 mb-3">Important Instructions:</h3>
                <ul className="space-y-2 text-sm text-blue-800">
                  <li className="flex items-start">
                    <span className="mr-2">1.</span>
                    <span>Send exactly {paymentDetails.amount} {selectedCurrency.toUpperCase()} to the address above</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">2.</span>
                    <span>Payment will be confirmed automatically within a few minutes</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">3.</span>
                    <span>Your subscription will be activated once payment is confirmed</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-2">4.</span>
                    <span>You will receive an email confirmation</span>
                  </li>
                </ul>
              </div>

              {/* Actions */}
              <div className="flex gap-4">
                <button
                  onClick={() => router.push('/dashboard')}
                  className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 font-medium"
                >
                  Go to Dashboard
                </button>
                <button
                  onClick={() => router.push('/select-tier')}
                  className="flex-1 bg-gray-200 text-gray-700 py-3 px-6 rounded-lg hover:bg-gray-300 font-medium"
                >
                  Back to Plans
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <button
            onClick={() => router.push('/select-tier')}
            className="flex items-center text-blue-600 hover:text-blue-700 mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Plan Selection
          </button>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Complete Your Subscription</h1>
          <p className="text-gray-600">Secure payment with multiple crypto options</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Plan Summary */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Plan Summary</h2>
            
            <div className="border-b border-gray-200 pb-4 mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-lg font-semibold">{selectedPlan.name}</span>
                <span className="text-2xl font-bold text-blue-600">
                  ${selectedPlan.price_usd}/{selectedPlan.interval}
                </span>
              </div>
              <p className="text-gray-600">Billed monthly • Cancel anytime</p>
            </div>

            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900">What's included:</h3>
              {selectedPlan.features.map((feature, index) => (
                <div key={index} className="flex items-center">
                  <Check className="w-5 h-5 text-green-500 mr-3 flex-shrink-0" />
                  <span className="text-gray-700">{feature}</span>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center text-blue-800">
              <CreditCard className="w-5 h-5 mr-2" />
              <span className="font-medium">Secure Payment</span>
            </div>
            <p className="text-sm text-blue-600 mt-1">
              Your payment is processed securely through NOWPayments
            </p>
            </div>
          </div>

          {/* Payment Form */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">Payment Details</h2>
            
            <div className="space-y-6">
              {/* Payment Method Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Payment Method
                </label>
                <div className="p-4 rounded-lg border-2 border-purple-500 bg-purple-50">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center mr-3">
                      <CreditCard className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <div className="font-medium text-purple-700">NOWPayments</div>
                      <div className="text-xs text-purple-600">252+ cryptocurrencies supported</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Currency Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Cryptocurrency
                </label>
                <select
                  value={selectedCurrency}
                  onChange={(e) => setSelectedCurrency(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                >
                  <option value="usdc">USD Coin (USDC)</option>
                  <option value="btc">Bitcoin (BTC)</option>
                  <option value="eth">Ethereum (ETH)</option>
                  <option value="bnb">Binance Coin (BNB)</option>
                  <option value="ada">Cardano (ADA)</option>
                  <option value="sol">Solana (SOL)</option>
                  <option value="dot">Polkadot (DOT)</option>
                  <option value="matic">Polygon (MATIC)</option>
                  <option value="ltc">Litecoin (LTC)</option>
                  <option value="usdt">Tether (USDT) - Limited Support</option>
                </select>
              </div>

              {/* Telegram Information */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Telegram User ID (Optional)
                </label>
                <input
                  type="text"
                  value={telegramUserId}
                  onChange={(e) => setTelegramUserId(e.target.value)}
                  placeholder="e.g., 123456789"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Required for Telegram group access
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Telegram Username (Optional)
                </label>
                <input
                  type="text"
                  value={telegramUsername}
                  onChange={(e) => setTelegramUsername(e.target.value)}
                  placeholder="e.g., @username"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Payment Summary */}
              <div className="border-t border-gray-200 pt-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Plan</span>
                  <span className="font-medium">{selectedPlan.name}</span>
                </div>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-600">Billing</span>
                  <span className="font-medium">Monthly</span>
                </div>
                <div className="flex justify-between items-center text-lg font-bold border-t border-gray-200 pt-2">
                  <span>Total</span>
                  <span className="text-blue-600">${selectedPlan.price_usd} USDT</span>
                </div>
              </div>

              {/* Payment Button */}
              <button
                onClick={handlePayment}
                disabled={processing}
                className="w-full bg-purple-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {processing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin mr-2" />
                    Processing...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-5 h-5 mr-2" />
                    Pay with NOWPayments
                    <span className="ml-2 text-xs">({selectedCurrency.toUpperCase()})</span>
                  </>
                )}
              </button>

              <p className="text-xs text-gray-500 text-center">
                By subscribing, you agree to our Terms of Service and Privacy Policy
              </p>
            </div>
          </div>
        </div>

        {/* Security Notice */}
        <div className="mt-8 bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="font-semibold text-green-900 mb-2">Secure Payment</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm text-green-800">
            <div className="flex items-center">
              <Check className="w-4 h-4 text-green-600 mr-2" />
              <span>SSL Encrypted</span>
            </div>
            <div className="flex items-center">
              <Check className="w-4 h-4 text-green-600 mr-2" />
              <span>NOWPayments Secure</span>
            </div>
            <div className="flex items-center">
              <Check className="w-4 h-4 text-green-600 mr-2" />
              <span>No Card Details Stored</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PaymentPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PaymentContent />
    </Suspense>
  );
}