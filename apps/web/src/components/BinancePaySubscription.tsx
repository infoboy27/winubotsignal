'use client';

import { useState } from 'react';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

interface SubscriptionPlan {
  id: string;
  name: string;
  price_usdt: number;
  features: string[];
  max_positions: number;
  min_signal_score: number;
}

interface BinancePaySubscriptionProps {
  onSuccess?: (subscription: any) => void;
  onCancel?: () => void;
}

export default function BinancePaySubscription({ onSuccess, onCancel }: BinancePaySubscriptionProps) {
  const [selectedPlan, setSelectedPlan] = useState<string>('pro');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [contractCode, setContractCode] = useState<string | null>(null);
  const [authorizationUrl, setAuthorizationUrl] = useState<string | null>(null);

  const plans: SubscriptionPlan[] = [
    {
      id: 'basic',
      name: 'Basic Plan',
      price_usdt: 29.99,
      features: ['Basic signals', 'Email alerts', 'Web dashboard'],
      max_positions: 3,
      min_signal_score: 0.70
    },
    {
      id: 'pro',
      name: 'Pro Plan',
      price_usdt: 59.99,
      features: ['All signals', 'Telegram alerts', 'Priority support', 'Advanced analytics'],
      max_positions: 5,
      min_signal_score: 0.65
    },
    {
      id: 'premium',
      name: 'Premium Plan',
      price_usdt: 99.99,
      features: ['All signals', 'All alerts', '24/7 support', 'Custom strategies', 'API access'],
      max_positions: 10,
      min_signal_score: 0.60
    }
  ];

  const handleSubscribe = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/binance-pay/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ plan_id: selectedPlan }),
      });

      const data = await response.json();

      if (response.ok) {
        setContractCode(data.contract_code);
        setAuthorizationUrl(data.authorization_url);
        onSuccess?.(data);
      } else {
        setError(data.detail || 'Failed to create subscription');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAuthorize = () => {
    if (authorizationUrl) {
      window.open(authorizationUrl, '_blank');
    }
  };

  const checkAuthorizationStatus = async () => {
    if (!contractCode) return;

    try {
      const response = await fetch(`/api/binance-pay/contract/${contractCode}/status`);
      const data = await response.json();

      if (data.authorized) {
        // Subscription is authorized
        onSuccess?.(data);
      }
    } catch (err) {
      console.error('Failed to check authorization status:', err);
    }
  };

  if (contractCode) {
    return (
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Complete Authorization
          </h3>
          <p className="text-gray-600 mb-4">
            Please authorize the Direct Debit contract in your Binance account
          </p>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Contract Code:</span>
            <code className="text-sm bg-white px-2 py-1 rounded border">{contractCode}</code>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Plan:</span>
            <span className="text-sm text-gray-900">{plans.find(p => p.id === selectedPlan)?.name}</span>
          </div>
        </div>

        <div className="space-y-4">
          <button
            onClick={handleAuthorize}
            className="w-full bg-yellow-500 text-white font-semibold py-3 px-4 rounded-lg hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 transition-colors"
          >
            Open Binance App
          </button>

          <button
            onClick={checkAuthorizationStatus}
            className="w-full bg-gray-100 text-gray-700 font-semibold py-3 px-4 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            Check Status
          </button>

          <button
            onClick={() => {
              setContractCode(null);
              setAuthorizationUrl(null);
            }}
            className="w-full text-gray-500 hover:text-gray-700 transition-colors"
          >
            Cancel
          </button>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Authorization Steps:</h4>
          <ol className="text-sm text-blue-800 space-y-1">
            <li>1. Open your Binance app or go to binance.com</li>
            <li>2. Navigate to Binance Pay</li>
            <li>3. Go to Direct Debit section</li>
            <li>4. Find and authorize the contract</li>
            <li>5. Return here and click "Check Status"</li>
          </ol>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg p-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Subscribe with NOWPayments
        </h2>
        <p className="text-gray-600">
          Pay securely with 252+ cryptocurrencies using NOWPayments
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <XMarkIcon className="w-5 h-5 text-red-400 mr-2" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative rounded-lg border-2 p-6 cursor-pointer transition-all ${
              selectedPlan === plan.id
                ? 'border-yellow-500 bg-yellow-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setSelectedPlan(plan.id)}
          >
            {selectedPlan === plan.id && (
              <div className="absolute top-4 right-4">
                <CheckIcon className="w-6 h-6 text-yellow-500" />
              </div>
            )}

            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{plan.name}</h3>
              <div className="text-3xl font-bold text-gray-900 mb-4">
                {plan.price_usdt} <span className="text-lg text-gray-600">USDT</span>
              </div>
              <div className="text-sm text-gray-600 mb-4">
                per month
              </div>
            </div>

            <ul className="space-y-2 mb-6">
              {plan.features.map((feature, index) => (
                <li key={index} className="flex items-center text-sm text-gray-700">
                  <CheckIcon className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>

            <div className="text-xs text-gray-500 space-y-1">
              <div>Max positions: {plan.max_positions}</div>
              <div>Min signal score: {(plan.min_signal_score * 100).toFixed(0)}%</div>
            </div>
          </div>
        ))}
      </div>

      <div className="text-center">
        <button
          onClick={handleSubscribe}
          disabled={loading}
          className="bg-yellow-500 text-white font-semibold py-3 px-8 rounded-lg hover:bg-yellow-600 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Creating Subscription...' : 'Subscribe with Binance Pay'}
        </button>

        {onCancel && (
          <button
            onClick={onCancel}
            className="ml-4 text-gray-500 hover:text-gray-700 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>

      <div className="mt-8 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-2">About Binance Pay Direct Debit:</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Secure cryptocurrency payments</li>
          <li>• Automatic monthly billing</li>
          <li>• No credit card required</li>
          <li>• Cancel anytime</li>
          <li>• Powered by Binance</li>
        </ul>
      </div>
    </div>
  );
}



