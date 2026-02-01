'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Check, Clock, Zap, Crown, ArrowRight, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

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

interface UserInfo {
  subscription_tier: string;
  subscription_status: string;
  trial_used: boolean;
  trial_start_date?: string;
  trial_dashboard_access_count: number;
}

export default function SelectTierPage() {
  const router = useRouter();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedPlan, setSelectedPlan] = useState<string>('');
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    
    // Also check auth state directly
    const checkAuthState = async () => {
      try {
        const { auth } = await import('../../lib/auth');
        const currentUser = auth.getCurrentUser();
        console.log('Auth library current user:', currentUser);
        
        if (currentUser && !userInfo) {
          console.log('User is logged in via auth library but userInfo is null - forcing refetch');
          fetchData();
        }
      } catch (err) {
        console.log('Error checking auth state:', err);
      }
    };
    
    checkAuthState();
  }, []);

  const fetchData = async () => {
    try {
      console.log('Fetching subscription plans...');
      
      // Fetch plans (public endpoint)
      const plansResponse = await fetch('/api/subscriptions/plans');
      console.log('Plans response status:', plansResponse.status);
      
      if (plansResponse.ok) {
        const plansData = await plansResponse.json();
        console.log('Plans data:', plansData);
        setPlans(plansData);
      } else {
        console.error('Failed to fetch plans:', plansResponse.status, plansResponse.statusText);
        setError('Failed to load subscription plans');
      }

      // Try to fetch user info (requires auth) - but don't redirect if not authenticated
      try {
        // Get token from localStorage
        const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
        
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };
        
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
          console.log('Token found, making authenticated request');
        } else {
          console.log('No token found in localStorage');
        }
        
        const userInfoResponse = await fetch('/api/subscriptions/info', {
          headers,
        });
        
        console.log('User info response status:', userInfoResponse.status);
        
        if (userInfoResponse.ok) {
          const userData = await userInfoResponse.json();
          console.log('User data received:', userData);
          setUserInfo(userData);
          
          // If user already has a subscription tier, redirect to dashboard
          if (userData.subscription_tier && userData.subscription_tier !== 'free') {
            router.push('/dashboard');
            return;
          }
        } else if (userInfoResponse.status === 401) {
          // User not authenticated - this is OK, they can still view plans
          console.log('User not authenticated - allowing plan viewing');
          setUserInfo(null);
        } else {
          console.log('Unexpected response status:', userInfoResponse.status);
          const errorData = await userInfoResponse.text();
          console.log('Error response:', errorData);
          setUserInfo(null);
        }
      } catch (authErr) {
        // Auth error - this is OK, they can still view plans
        console.log('Auth error - allowing plan viewing:', authErr);
        setUserInfo(null);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load subscription plans');
    } finally {
      setLoading(false);
    }
  };

  const handlePlanSelection = async (planId: string) => {
    console.log('Plan selection clicked:', planId);
    console.log('User info available:', userInfo);
    
    // Check if user is authenticated first
    if (!userInfo) {
      console.log('No user info, checking localStorage for token');
      const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
      console.log('Token in localStorage:', token ? 'exists' : 'missing');
      
      if (!token) {
        toast.error('Please log in to continue');
        router.push('/login');
        return;
      } else {
        console.log('Token exists but userInfo is null, attempting to fetch user info');
        
        // Try to fetch user info directly
        try {
          const headers: HeadersInit = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          };
          
          const response = await fetch('/api/subscriptions/info', { headers });
          if (response.ok) {
            const userData = await response.json();
            setUserInfo(userData);
            console.log('Successfully fetched user info, continuing with subscription');
            // Continue with the subscription process
          } else {
            console.log('Failed to fetch user info, redirecting to login');
            toast.error('Authentication expired. Please log in again.');
            router.push('/login');
            return;
          }
        } catch (err) {
          console.log('Error fetching user info:', err);
          toast.error('Authentication error. Please log in again.');
          router.push('/login');
          return;
        }
      }
    }

    setSelectedPlan(planId);
    setProcessing(true);
    setError(null);

    try {
      if (planId === 'free_trial') {
        // Start free trial
        const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
        
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };
        
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch('/api/subscriptions/trial/start', {
          method: 'POST',
          headers,
        });

        const result = await response.json();

        if (result.success) {
          toast.success('Free trial started! Welcome to your dashboard.');
          router.push('/dashboard?trial_started=true');
        } else {
          setError(result.message || 'Failed to start free trial');
        }
      } else {
        // Redirect to payment process
        toast.success('Redirecting to payment...');
        router.push(`/payment?plan=${planId}`);
      }
    } catch (err) {
      setError('Failed to process selection');
    } finally {
      setProcessing(false);
      setSelectedPlan('');
    }
  };

  const getPlanIcon = (planId: string) => {
    switch (planId) {
      case 'free_trial':
        return <Clock className="w-6 h-6" />;
      case 'professional':
        return <Zap className="w-6 h-6" />;
      case 'vip_elite':
        return <Crown className="w-6 h-6" />;
      default:
        return <Check className="w-6 h-6" />;
    }
  };

  const getPlanColor = (planId: string) => {
    switch (planId) {
      case 'free_trial':
        return 'from-green-500 to-blue-600';
      case 'professional':
        return 'from-blue-500 to-purple-600';
      case 'vip_elite':
        return 'from-purple-500 to-pink-600';
      default:
        return 'from-gray-500 to-gray-600';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading subscription plans...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Choose Your Trading Plan</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Select the perfect plan for your trading needs. Start with our free trial or jump straight to premium features.
          </p>
        </div>

        {/* Authentication Notice */}
        {!userInfo && (
          <div className="mb-8 p-6 bg-blue-50 border border-blue-200 rounded-lg max-w-4xl mx-auto">
            <div className="flex items-center justify-center space-x-3">
              <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">!</span>
              </div>
              <p className="text-blue-800 font-medium">
                Please log in to subscribe to any plan or start your free trial
              </p>
              <button
                onClick={() => router.push('/login')}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Log In
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg max-w-2xl mx-auto">
            {error}
          </div>
        )}

        {/* Debug Info */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              Debug: {plans.length} plans loaded, loading: {loading.toString()}
            </p>
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {plans.length > 0 ? plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative bg-white rounded-2xl shadow-xl p-8 transition-all duration-300 hover:shadow-2xl ${
                plan.id === 'vip_elite' ? 'ring-2 ring-purple-500 scale-105' : ''
              } ${selectedPlan === plan.id ? 'ring-2 ring-green-500' : ''}`}
            >
              {/* Popular Badge */}
              {plan.id === 'vip_elite' && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <div className="bg-gradient-to-r from-purple-500 to-pink-600 text-white px-4 py-2 rounded-full text-sm font-semibold">
                    Most Popular
                  </div>
                </div>
              )}

              {/* Plan Header */}
              <div className="text-center mb-6">
                <div className={`w-16 h-16 bg-gradient-to-r ${getPlanColor(plan.id)} rounded-full flex items-center justify-center mx-auto mb-4 text-white`}>
                  {getPlanIcon(plan.id)}
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                
                {/* Price */}
                <div className="mb-6">
                  <span className="text-4xl font-bold text-gray-900">
                    ${plan.price_usd}
                  </span>
                  {plan.interval !== 'trial' && (
                    <span className="text-gray-600 ml-2">/{plan.interval}</span>
                  )}
                </div>
              </div>

              {/* Features */}
              <div className="space-y-3 mb-8">
                {plan.features.map((feature, index) => (
                  <div key={index} className="flex items-center">
                    <Check className="w-5 h-5 text-green-500 mr-3 flex-shrink-0" />
                    <span className="text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>

              {/* Select Button */}
              <button
                onClick={() => handlePlanSelection(plan.id)}
                disabled={processing}
                className={`w-full py-3 px-4 rounded-lg font-semibold transition-all ${
                  !userInfo 
                    ? 'bg-gray-400 text-white cursor-not-allowed' 
                    : `bg-gradient-to-r ${getPlanColor(plan.id)} text-white hover:opacity-90`
                } disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center`}
              >
                {processing && selectedPlan === plan.id ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : !userInfo ? (
                  <>
                    Log In Required
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </>
                ) : (
                  <>
                    {plan.id === 'free_trial' ? 'Start Free Trial' : 'Select Plan'}
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </>
                )}
              </button>

              {/* Trial Notice */}
              {plan.id === 'free_trial' && userInfo?.trial_used && (
                <p className="text-sm text-red-600 text-center mt-2">
                  You have already used your free trial
                </p>
              )}
            </div>
          )) : (
            <div className="col-span-3 text-center py-12">
              <p className="text-gray-600 text-lg">No subscription plans available</p>
              <p className="text-gray-500 text-sm mt-2">Please try refreshing the page</p>
            </div>
          )}
        </div>

        {/* Features Comparison */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h3 className="text-2xl font-bold text-gray-900 text-center mb-8">What's Included</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Zap className="w-6 h-6 text-blue-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">AI-Powered Signals</h4>
              <p className="text-sm text-gray-600">Advanced algorithms analyze market data to generate high-probability trading signals</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-6 h-6 text-green-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Real-time Alerts</h4>
              <p className="text-sm text-gray-600">Instant notifications via Telegram, Discord, and email when new signals are generated</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Crown className="w-6 h-6 text-purple-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Professional Tools</h4>
              <p className="text-sm text-gray-600">Access to our dashboard, analytics, risk management tools, and exclusive Telegram group</p>
            </div>
          </div>
        </div>

        {/* Back to Login */}
        <div className="text-center mt-8">
          <p className="text-gray-600">
            Already have an account?{' '}
            <button
              onClick={() => router.push('/login')}
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              Sign in here
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
