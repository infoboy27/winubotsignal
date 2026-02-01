'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  CreditCard, 
  Check, 
  X, 
  Crown, 
  Zap, 
  Shield, 
  Users, 
  Clock,
  AlertTriangle,
  ExternalLink,
  RefreshCw
} from 'lucide-react';

const PLANS = [
  {
    id: 'monthly',
    name: 'Monthly Premium',
    price: 29.99,
    currency: 'usd',
    interval: 'month',
    features: [
      'Real-time trading signals',
      'Telegram group access',
      'Dashboard access',
      'Email alerts',
      'Priority support'
    ]
  },
  {
    id: 'yearly',
    name: 'Yearly Premium',
    price: 299.99,
    currency: 'usd',
    interval: 'year',
    features: [
      'Real-time trading signals',
      'Telegram group access',
      'Dashboard access',
      'Email alerts',
      'Priority support',
      '2 months free (20% discount)'
    ]
  }
];

export default function BillingSimplePage() {
  const [processing, setProcessing] = useState(false);
  const router = useRouter();

  const handleSubscribe = async (planId: string) => {
    setProcessing(true);
    try {
      // Simulate subscription process
      alert(`Subscription to ${planId} plan initiated!`);
    } catch (error) {
      console.error('Error subscribing:', error);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Billing & Subscription</h1>
              <p className="text-gray-600 mt-1">Manage your Winu Bot subscription</p>
            </div>
            <button
              onClick={() => router.push('/dashboard')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Current Subscription Status */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Current Subscription</h2>
            <button
              onClick={() => window.location.reload()}
              className="p-2 text-gray-500 hover:text-gray-700"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-green-100 text-green-600">
                <Check className="w-4 h-4" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Status</p>
                <p className="text-sm text-gray-600">Active</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-blue-100 text-blue-600">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Next Billing</p>
                <p className="text-sm text-gray-600">N/A</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-lg bg-green-100 text-green-600">
                <Shield className="w-4 h-4" />
              </div>
              <div>
                <p className="font-medium text-gray-900">Telegram Access</p>
                <p className="text-sm text-gray-600">Connected</p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex space-x-4">
            <button
              onClick={() => alert('Customer portal would open here')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <CreditCard className="w-4 h-4" />
              <span>Manage Subscription</span>
            </button>
          </div>
        </div>

        {/* Subscription Plans */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`bg-white rounded-xl shadow-lg p-6 ${
                plan.id === 'yearly' ? 'ring-2 ring-blue-500' : ''
              }`}
            >
              {plan.id === 'yearly' && (
                <div className="bg-blue-500 text-white text-center py-2 px-4 rounded-lg mb-4 -mt-6 mx-6">
                  <Crown className="w-4 h-4 inline mr-2" />
                  Most Popular
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900">{plan.name}</h3>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-gray-900">${plan.price}</span>
                  <span className="text-gray-600">/{plan.interval}</span>
                </div>
                {plan.id === 'yearly' && (
                  <p className="text-sm text-green-600 mt-2">Save 20% with yearly billing</p>
                )}
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center space-x-3">
                    <Check className="w-5 h-5 text-green-500 flex-shrink-0" />
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={processing}
                className="w-full py-3 px-4 rounded-lg font-semibold transition-colors bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {processing ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Processing...</span>
                  </div>
                ) : (
                  `Subscribe for $${plan.price}/${plan.interval}`
                )}
              </button>
            </div>
          ))}
        </div>

        {/* Features Comparison */}
        <div className="mt-12 bg-white rounded-xl shadow-lg p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">What's Included</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <Zap className="w-6 h-6 text-blue-600" />
              </div>
              <h4 className="font-semibold text-gray-900">Real-time Signals</h4>
              <p className="text-sm text-gray-600">AI-powered trading signals delivered instantly</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <Users className="w-6 h-6 text-green-600" />
              </div>
              <h4 className="font-semibold text-gray-900">Telegram Group</h4>
              <p className="text-sm text-gray-600">Exclusive access to our private trading community</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <Shield className="w-6 h-6 text-purple-600" />
              </div>
              <h4 className="font-semibold text-gray-900">Dashboard Access</h4>
              <p className="text-sm text-gray-600">Advanced analytics and signal tracking</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                <Crown className="w-6 h-6 text-yellow-600" />
              </div>
              <h4 className="font-semibold text-gray-900">Priority Support</h4>
              <p className="text-sm text-gray-600">24/7 customer support for subscribers</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


