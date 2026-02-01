'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Check, Star, Zap, Crown, ArrowRight, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

interface Plan {
  id: string;
  name: string;
  price: number;
  currency: string;
  duration: string;
  features: string[];
  description: string;
  popular?: boolean;
  recommended?: boolean;
}

function SelectPlanContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get('email') || '';
  
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [freeTrialUsed, setFreeTrialUsed] = useState(false);

  useEffect(() => {
    fetchPlans();
    checkFreeTrialEligibility();
  }, [email]);

  const fetchPlans = async () => {
    try {
        const response = await fetch('/api/onboarding/plans');
      const data = await response.json();
      setPlans(data.plans);
    } catch (error) {
      console.error('Error fetching plans:', error);
      toast.error('Failed to load plans');
    }
  };

  const checkFreeTrialEligibility = async () => {
    try {
        const response = await fetch(`/api/onboarding/check-free-trial/${encodeURIComponent(email)}`);
      const data = await response.json();
      setFreeTrialUsed(!data.eligible);
    } catch (error) {
      console.error('Error checking free trial:', error);
    }
  };

  const handlePlanSelection = async (planId: string) => {
    // For free trial, redirect to subscription page to start trial
    if (planId === 'free_trial') {
      router.push('/subscription');
      return;
    }

    // For other plans, redirect to subscription page for Binance Pay
    setLoading(true);
    try {
      toast.success('Redirecting to subscription...');
      router.push('/subscription');
    } catch (error) {
      console.error('Plan selection error:', error);
      toast.error('An error occurred during plan selection');
    } finally {
      setLoading(false);
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
        return <Star className="w-6 h-6" />;
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">Choose Your Plan</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Select the perfect plan for your trading needs. Start with our free trial or jump straight to premium features.
          </p>
        </div>

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative bg-white rounded-2xl shadow-xl p-8 transition-all duration-300 hover:shadow-2xl ${
                plan.popular ? 'ring-2 ring-blue-500 scale-105' : ''
              } ${selectedPlan === plan.id ? 'ring-2 ring-green-500' : ''}`}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-4 py-2 rounded-full text-sm font-semibold">
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
                <p className="text-gray-600 mb-4">{plan.description}</p>
                
                {/* Price */}
                <div className="mb-6">
                  <span className="text-4xl font-bold text-gray-900">
                    ${plan.price}
                  </span>
                  <span className="text-gray-600 ml-2">/{plan.duration}</span>
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
                disabled={loading || (plan.id === 'free_trial' && freeTrialUsed)}
                className={`w-full py-3 px-4 rounded-lg font-semibold transition-all ${
                  (plan.id === 'free_trial' && freeTrialUsed)
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : `bg-gradient-to-r ${getPlanColor(plan.id)} text-white hover:opacity-90`
                } disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center`}
              >
                {loading && selectedPlan === plan.id ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    {plan.id === 'free_trial' && freeTrialUsed ? 'Already Used' : 'Select Plan'}
                    <ArrowRight className="ml-2 w-5 h-5" />
                  </>
                )}
              </button>

              {/* Free Trial Notice */}
              {plan.id === 'free_trial' && freeTrialUsed && (
                <p className="text-sm text-red-600 text-center mt-2">
                  You have already used your free trial
                </p>
              )}
            </div>
          ))}
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
                <Star className="w-6 h-6 text-purple-600" />
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

export default function SelectPlanPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    }>
      <SelectPlanContent />
    </Suspense>
  );
}
