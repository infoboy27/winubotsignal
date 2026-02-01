'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Mail, User, Lock, ArrowRight, CheckCircle, CreditCard } from 'lucide-react';
import toast from 'react-hot-toast';

interface SubscriptionPlan {
  id: string;
  name: string;
  price_usd: number;
  features: string[];
  max_positions: number;
  min_signal_score: number;
  telegram_access: boolean;
  discord_access: boolean;
}

export default function RegisterWithPlanPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    selectedPlan: 'pro' as string
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [nowPaymentsData, setNowPaymentsData] = useState(null);
  const [selectedCurrency, setSelectedCurrency] = useState('usdc');

  const subscriptionPlans: SubscriptionPlan[] = [
    {
      id: 'basic',
      name: 'Basic Plan',
      price_usd: 15.00,
      features: [
        'Basic trading signals',
        'Email alerts', 
        'Web dashboard access',
        'Community Discord access',
        'Basic support'
      ],
      max_positions: 3,
      min_signal_score: 0.70,
      telegram_access: false,
      discord_access: true
    },
    {
      id: 'pro',
      name: 'Pro Plan', 
      price_usd: 40.00,
      features: [
        'All trading signals',
        'Telegram alerts & group access',
        'Priority support',
        'Advanced analytics',
        'Risk management tools',
        'Mobile app access'
      ],
      max_positions: 5,
      min_signal_score: 0.65,
      telegram_access: true,
      discord_access: true
    },
    {
      id: 'premium',
      name: 'Premium Plan',
      price_usd: 80.00,
      features: [
        'All trading signals',
        'Exclusive Telegram VIP group',
        '24/7 priority support',
        'Custom trading strategies',
        'API access',
        'Advanced analytics',
        'Portfolio management',
        'Direct access to trading team'
      ],
      max_positions: 10,
      min_signal_score: 0.60,
      telegram_access: true,
      discord_access: true
    }
  ];

  const selectedPlan = subscriptionPlans.find(plan => plan.id === formData.selectedPlan);

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    // Validate password strength
    if (formData.password.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/onboarding/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success('Account created successfully! Please check your email for verification.');
        setCurrentStep(2);
      } else {
        toast.error(data.detail || 'Registration failed');
      }
    } catch (error) {
      toast.error('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async (paymentMethod: string, payCurrency: string = 'btc') => {
    setPaymentLoading(true);

    try {
      // Create payment
      const response = await fetch('/api/crypto-subscriptions/create-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}` // Assuming token is stored
        },
        body: JSON.stringify({
          plan_id: formData.selectedPlan,
          payment_method: paymentMethod,
          pay_currency: payCurrency
        }),
      });

      const data = await response.json();

      if (response.ok) {
        if (paymentMethod === 'coinbase_commerce') {
          // Redirect to Coinbase Commerce payment page
          window.open(data.payment_data.payment_url, '_blank');
          toast.success('Redirecting to payment page...');
        } else if (paymentMethod === 'stripe_crypto') {
          // Handle Stripe payment
          toast.success('Stripe payment initiated...');
        } else if (paymentMethod === 'nowpayments') {
          // Handle NOWPayments - show payment address and QR code
          setNowPaymentsData(data.payment_data);
          setCurrentStep(3);
          toast.success('NOWPayments payment created!');
        } else if (paymentMethod === 'direct_crypto') {
          // Show direct crypto payment info
          setCurrentStep(3);
        }
      } else {
        toast.error(data.detail || 'Payment creation failed');
      }
    } catch (error) {
      toast.error('Payment error. Please try again.');
    } finally {
      setPaymentLoading(false);
    }
  };

  const renderStep1 = () => (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">Create Account</h1>
            <p className="text-white/70">Join Winu Trading Bot</p>
          </div>

          <form onSubmit={handleStep1Submit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
                <input
                  type="text"
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all duration-200"
                  placeholder="Choose a username"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
                <input
                  type="email"
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all duration-200"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  className="w-full pl-10 pr-12 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all duration-200"
                  placeholder="Create a password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-white/60 w-5 h-5" />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  className="w-full pl-10 pr-12 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-transparent transition-all duration-200"
                  placeholder="Confirm your password"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white transition-colors"
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-white text-indigo-600 font-semibold py-3 px-4 rounded-lg hover:bg-white/90 focus:outline-none focus:ring-2 focus:ring-white/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div>
              ) : (
                <>
                  Create Account
                  <ArrowRight className="w-5 h-5 ml-2" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-white/70 text-sm">
              Already have an account?{' '}
              <button
                onClick={() => router.push('/login')}
                className="text-white hover:text-white/80 font-medium transition-colors"
              >
                Sign in
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex items-center justify-center p-4">
      <div className="w-full max-w-6xl">
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 border border-white/20">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-3xl font-bold text-white mb-2">Account Created!</h2>
            <p className="text-white/70">Please check your email for verification, then choose your plan</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {subscriptionPlans.map((plan) => (
              <div
                key={plan.id}
                className={`relative rounded-lg border-2 p-6 cursor-pointer transition-all ${
                  formData.selectedPlan === plan.id
                    ? 'border-yellow-500 bg-yellow-50/10'
                    : 'border-white/20 hover:border-white/40'
                }`}
                onClick={() => setFormData({...formData, selectedPlan: plan.id})}
              >
                {formData.selectedPlan === plan.id && (
                  <div className="absolute top-4 right-4">
                    <CheckCircle className="w-6 h-6 text-yellow-500" />
                  </div>
                )}

                <div className="text-center mb-4">
                  <h3 className="text-xl font-semibold text-white mb-2">{plan.name}</h3>
                  <div className="text-3xl font-bold text-white mb-2">
                    ${plan.price_usd}
                    <span className="text-lg text-white/70">/month</span>
                  </div>
                </div>

                <ul className="space-y-2 mb-6">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-center text-sm text-white/90">
                      <CheckCircle className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <div className="text-xs text-white/60 space-y-1">
                  <div>Max positions: {plan.max_positions}</div>
                  <div>Min signal score: {(plan.min_signal_score * 100).toFixed(0)}%</div>
                  <div>Telegram access: {plan.telegram_access ? 'Yes' : 'No'}</div>
                </div>
              </div>
            ))}
          </div>

          {selectedPlan && (
            <div className="text-center">
              <h3 className="text-xl font-semibold text-white mb-4">Choose Payment Method</h3>
              <div className="grid md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                <button
                  onClick={() => handlePayment('nowpayments', selectedCurrency)}
                  disabled={paymentLoading}
                  className="bg-purple-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  <CreditCard className="w-5 h-5 mr-2" />
                  NOWPayments
                </button>

                <button
                  onClick={() => handlePayment('direct_crypto')}
                  disabled={paymentLoading}
                  className="bg-green-500 text-white font-semibold py-3 px-4 rounded-lg hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  <CreditCard className="w-5 h-5 mr-2" />
                  Direct Crypto
                </button>
              </div>
              
              {/* NOWPayments Currency Selector */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-white/80 mb-2">Select Cryptocurrency for NOWPayments:</label>
                <select
                  value={selectedCurrency}
                  onChange={(e) => setSelectedCurrency(e.target.value)}
                  className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
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
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div>
      {currentStep === 1 && renderStep1()}
      {currentStep === 2 && renderStep2()}
    </div>
  );
}



