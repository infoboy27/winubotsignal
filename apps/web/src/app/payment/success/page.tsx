'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { CheckCircle, ArrowRight, Loader2, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

function PaymentSuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [paymentVerified, setPaymentVerified] = useState(false);

  useEffect(() => {
    const verifyPayment = async () => {
      // Try to get session_id from URL parameters
      let sessionIdParam = searchParams.get('session_id');
      
      // If no session_id, try alternative parameters
      if (!sessionIdParam) {
        sessionIdParam = searchParams.get('payment_id') || 
                        searchParams.get('transaction_id') || 
                        searchParams.get('order_id');
      }
      
      // If still no ID found, check if user just came from payment page
      if (!sessionIdParam) {
        // Try to verify user's subscription status instead
        const checkUserSubscription = async () => {
          try {
            const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
            
            if (!token) {
              // No token, redirect to login
              toast.error('Please log in to view your subscription status');
              router.push('/login');
              return;
            }
            
            // Check user's current subscription status
            const response = await fetch('/api/users/me', {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            
            if (response.ok) {
              const user = await response.json();
              
              // Check if user has an active subscription
              if (user.subscription_status === 'active' && user.subscription_tier !== 'free') {
                // User has active subscription, show success
                setPaymentVerified(true);
                setSessionId('verified_by_status');
                setLoading(false);
                toast.success('Payment verified! Welcome to Winu Bot Signal!');
                return;
              }
            }
            
            // If we get here, payment status is unclear
            setLoading(false);
            setVerifying(false);
            toast.loading('Verifying your payment... This may take a moment.', {
              duration: 5000,
              icon: '⏳'
            });
            
            // Show a message that payment is being processed
            setSessionId('processing');
            
          } catch (error) {
            console.error('Error checking subscription:', error);
            setLoading(false);
            // Don't show error, show processing message instead
            setSessionId('processing');
            toast.loading('Payment processing... Please wait.', {
              duration: 5000,
              icon: '⏳'
            });
          }
        };
        
        await checkUserSubscription();
      } else {
        // We have a session ID, show success
        setSessionId(sessionIdParam);
        setPaymentVerified(true);
        setLoading(false);
        toast.success('Payment successful! Welcome to Winu Bot Signal!');
      }
    };
    
    verifyPayment();
  }, [searchParams, router]);

  const handleContinue = () => {
    router.push('/dashboard');
  };

  const handleContactSupport = () => {
    router.push('/support');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-white animate-spin mx-auto mb-4" />
          <p className="text-white">Verifying your payment...</p>
        </div>
      </div>
    );
  }

  // Payment is being processed
  if (sessionId === 'processing') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
          <div className="text-center">
            <div className="w-20 h-20 bg-yellow-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="w-12 h-12 text-white" />
            </div>

            <h1 className="text-3xl font-bold text-white mb-4">
              Payment Processing
            </h1>

            <p className="text-blue-200 text-lg mb-8">
              Your payment is being processed. This usually takes 1-2 minutes.
              You'll receive a confirmation email once your subscription is activated.
            </p>

            <div className="bg-blue-500/20 border border-blue-400/30 rounded-lg p-6 mb-8">
              <h3 className="text-white font-semibold mb-4">What to do next:</h3>
              <ul className="text-left text-blue-200 space-y-2">
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                  <span>Check your email for payment confirmation</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                  <span>Wait 1-2 minutes for activation</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                  <span>Refresh your dashboard to see updated status</span>
                </li>
                <li className="flex items-start">
                  <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                  <span>Contact support if not activated within 5 minutes</span>
                </li>
              </ul>
            </div>

            <div className="flex gap-4">
              <button
                onClick={handleContinue}
                className="flex-1 py-3 px-6 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <span>Go to Dashboard</span>
                <ArrowRight className="w-5 h-5 ml-2" />
              </button>
              <button
                onClick={handleContactSupport}
                className="flex-1 py-3 px-6 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
              >
                Contact Support
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Payment verified successfully
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center p-4">
      <div className="max-w-lg w-full bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
        <div className="text-center">
          <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-12 h-12 text-white" />
          </div>

          <h1 className="text-3xl font-bold text-white mb-4">
            Payment Successful!
          </h1>

          <p className="text-blue-200 text-lg mb-8">
            Thank you for subscribing to Winu Bot Signal.
            Your account is now active and you have full access to all premium features.
          </p>

          <div className="bg-blue-500/20 border border-blue-400/30 rounded-lg p-6 mb-8">
            <h3 className="text-white font-semibold mb-4">What's Next?</h3>
            <ul className="text-left text-blue-200 space-y-2">
              <li className="flex items-start">
                <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                <span>Access premium trading signals</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                <span>Real-time alerts via Telegram & Discord</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                <span>Advanced backtesting tools</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="w-5 h-5 mr-2 mt-0.5 text-green-400" />
                <span>AI-powered market analysis</span>
              </li>
            </ul>
          </div>

          <button
            onClick={handleContinue}
            className="w-full py-3 px-6 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors flex items-center justify-center"
          >
            <span>Continue to Dashboard</span>
            <ArrowRight className="w-5 h-5 ml-2" />
          </button>

          {sessionId && sessionId !== 'verified_by_status' && sessionId !== 'processing' && (
            <p className="text-sm text-gray-500 mt-4">
              Session ID: {sessionId}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    }>
      <PaymentSuccessContent />
    </Suspense>
  );
}
