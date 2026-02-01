'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface SubscriptionPlan {
  id: string;
  name: string;
  price_usd: number;
  price_usdt: number;
  interval: string;
  duration_days?: number;
  dashboard_access_limit: number;
  features: string[];
  telegram_access: boolean;
  support_level: string;
  binance_pay_id?: string;
}

interface UserSubscriptionInfo {
  subscription_tier: string;
  subscription_status: string;
  trial_used: boolean;
  trial_start_date?: string;
  trial_dashboard_access_count: number;
  payment_due_date?: string;
  access_revoked_at?: string;
  plan_info?: SubscriptionPlan;
  telegram_access: any[];
}

export default function SubscriptionPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [userInfo, setUserInfo] = useState<UserSubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [startingTrial, setStartingTrial] = useState(false);
  const [subscribing, setSubscribing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscriptionData();
  }, []);

  const fetchSubscriptionData = async () => {
    try {
      // Always fetch plans (no auth required)
      const plansResponse = await fetch('/api/subscriptions/plans');
      if (plansResponse.ok) {
        const plansData = await plansResponse.json();
        setPlans(plansData);
      }

      // Try to fetch user info (requires auth)
      try {
        const userInfoResponse = await fetch('/api/subscriptions/info');
        if (userInfoResponse.ok) {
          const userData = await userInfoResponse.json();
          setUserInfo(userData);
        } else if (userInfoResponse.status === 401) {
          // User not authenticated, that's okay - they can still see plans
          console.log('User not authenticated, showing plans only');
        }
      } catch (authErr) {
        // Authentication error, continue without user info
        console.log('Authentication error, showing plans only');
      }
    } catch (err) {
      setError('Failed to load subscription plans');
    } finally {
      setLoading(false);
    }
  };

  const startFreeTrial = async () => {
    // Check if user is authenticated
    if (!userInfo) {
      setError('Please log in first to start your free trial');
      router.push('/login');
      return;
    }

    setStartingTrial(true);
    setError(null);

    try {
      const response = await fetch('/api/subscriptions/trial/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();

      if (result.success) {
        // Refresh user info
        await fetchSubscriptionData();
        // Redirect to dashboard with access granted
        router.push('/dashboard?trial_started=true');
      } else {
        setError(result.message || 'Failed to start free trial');
      }
    } catch (err) {
      setError('Failed to start free trial');
    } finally {
      setStartingTrial(false);
    }
  };

  const subscribeToPlan = async (planId: string) => {
    // Check if user is authenticated
    if (!userInfo) {
      setError('Please log in first to subscribe');
      router.push('/login');
      return;
    }

    setSubscribing(planId);
    setError(null);

    try {
      const telegramUserId = prompt('Enter your Telegram User ID (optional):');
      const telegramUsername = prompt('Enter your Telegram Username (optional):');

      const response = await fetch('/api/subscriptions/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          plan_id: planId,
          telegram_user_id: telegramUserId || null,
          telegram_username: telegramUsername || null,
        }),
      });

      const result = await response.json();

      if (result.success && result.data.payment_url) {
        // Redirect to Binance Pay
        window.location.href = result.data.payment_url;
      } else {
        setError(result.message || 'Failed to create subscription');
      }
    } catch (err) {
      setError('Failed to create subscription');
    } finally {
      setSubscribing(null);
    }
  };

  const getTrialInfo = () => {
    if (!userInfo?.trial_start_date) return null;

    const startDate = new Date(userInfo.trial_start_date);
    const daysRemaining = Math.max(0, 7 - Math.floor((Date.now() - startDate.getTime()) / (1000 * 60 * 60 * 24)));
    const accessRemaining = Math.max(0, 1 - userInfo.trial_dashboard_access_count);

    return {
      daysRemaining,
      accessRemaining,
      isExpired: daysRemaining === 0 || accessRemaining === 0
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading subscription plans...</p>
        </div>
      </div>
    );
  }

  const trialInfo = getTrialInfo();
  const currentPlan = plans.find(plan => plan.id === userInfo?.subscription_tier);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Your Trading Plan
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Unlock powerful trading signals, exclusive Telegram groups, and premium features
          </p>
        </div>

        {/* Authentication Notice */}
        {!userInfo && (
          <div className="mb-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
            <h2 className="text-xl font-semibold text-blue-900 mb-2">Please Log In</h2>
            <p className="text-blue-800 mb-4">
              You need to be logged in to start a free trial or subscribe to a plan.
            </p>
            <button
              onClick={() => router.push('/login')}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Log In
            </button>
          </div>
        )}

        {/* Current Status */}
        {userInfo && (
          <div className="mb-8 p-6 bg-white rounded-lg shadow-md">
            <h2 className="text-2xl font-semibold mb-4">Your Current Status</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600">Subscription Tier</p>
                <p className="text-lg font-semibold capitalize">{userInfo.subscription_tier}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Status</p>
                <p className="text-lg font-semibold capitalize">{userInfo.subscription_status}</p>
              </div>
              {trialInfo && (
                <>
                  <div>
                    <p className="text-sm text-gray-600">Trial Days Remaining</p>
                    <p className="text-lg font-semibold">{trialInfo.daysRemaining}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Dashboard Access Remaining</p>
                    <p className="text-lg font-semibold">{trialInfo.accessRemaining}</p>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        {/* Subscription Plans */}
        <div className="grid md:grid-cols-3 gap-8">
          {/* Free Trial Plan */}
          {!userInfo?.trial_used && (
            <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-green-200">
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-green-600 mb-2">Free Trial</h3>
                <div className="text-4xl font-bold text-gray-900 mb-2">$0</div>
                <p className="text-gray-600">7 days • 1 dashboard access</p>
              </div>
              
              <ul className="space-y-3 mb-8">
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  1-time dashboard access
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Basic signal preview
                </li>
                <li className="flex items-center">
                  <svg className="w-5 h-5 text-green-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Limited features
                </li>
              </ul>
              
              <button
                onClick={startFreeTrial}
                disabled={startingTrial}
                className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {startingTrial ? 'Starting Trial...' : 'Start Free Trial'}
              </button>
            </div>
          )}

          {/* Professional Plan */}
          <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-blue-200">
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-blue-600 mb-2">Professional</h3>
              <div className="text-4xl font-bold text-gray-900 mb-2">$14.99</div>
              <p className="text-gray-600">per month</p>
            </div>
            
            <ul className="space-y-3 mb-8">
              <li className="flex items-center">
                <svg className="w-5 h-5 text-blue-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Dashboard access
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-blue-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Telegram group access
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-blue-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Priority support
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-blue-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Real-time signals
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-blue-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Email alerts
              </li>
            </ul>
            
            <button
              onClick={() => subscribeToPlan('professional')}
              disabled={subscribing === 'professional'}
              className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {subscribing === 'professional' ? 'Creating Payment...' : 'Subscribe with Binance Pay'}
            </button>
          </div>

          {/* VIP Elite Plan */}
          <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-purple-200 relative">
            <div className="absolute top-0 right-0 bg-purple-600 text-white px-3 py-1 rounded-bl-lg rounded-tr-lg text-sm font-semibold">
              Most Popular
            </div>
            
            <div className="text-center mb-6">
              <h3 className="text-2xl font-bold text-purple-600 mb-2">VIP Elite</h3>
              <div className="text-4xl font-bold text-gray-900 mb-2">$29.99</div>
              <p className="text-gray-600">per month</p>
            </div>
            
            <ul className="space-y-3 mb-8">
              <li className="flex items-center">
                <svg className="w-5 h-5 text-purple-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                All Professional features
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-purple-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                24/7 priority support
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-purple-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Early access to new features
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-purple-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Access to trading bot
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-purple-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Custom alerts
              </li>
              <li className="flex items-center">
                <svg className="w-5 h-5 text-purple-500 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Access to airdrops
              </li>
            </ul>
            
            <button
              onClick={() => subscribeToPlan('vip_elite')}
              disabled={subscribing === 'vip_elite'}
              className="w-full bg-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {subscribing === 'vip_elite' ? 'Creating Payment...' : 'Subscribe with NOWPayments'}
            </button>
          </div>
        </div>

        {/* Payment Info */}
        <div className="mt-12 text-center">
          <p className="text-gray-600 mb-4">
            All payments are processed securely via Binance Pay
          </p>
          <div className="flex justify-center space-x-6 text-sm text-gray-500">
            <span>✓ Secure Payments</span>
            <span>✓ Cancel Anytime</span>
            <span>✓ 24/7 Support</span>
          </div>
        </div>
      </div>
    </div>
  );
}
