'use client';

import { useRouter } from 'next/navigation';
import { XCircle, ArrowLeft, CreditCard } from 'lucide-react';
import toast from 'react-hot-toast';

export default function PaymentCancelPage() {
  const router = useRouter();

  const handleRetryPayment = () => {
    router.push('/subscription');
  };

  const handleGoHome = () => {
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <XCircle className="w-12 h-12 text-red-600" />
        </div>
        
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Payment Cancelled</h1>
        <p className="text-gray-600 mb-6">
          Your payment was cancelled. No charges have been made to your account.
        </p>
        
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-semibold">
            💳 Payment was not completed
          </p>
          <p className="text-red-700 text-sm mt-2">
            You can try again or choose a different plan.
          </p>
        </div>

        <div className="space-y-3">
          <button
            onClick={handleRetryPayment}
            className="w-full py-3 px-6 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center"
          >
            <CreditCard className="w-5 h-5 mr-2" />
            <span>Try Payment Again</span>
          </button>

          <button
            onClick={handleGoHome}
            className="w-full py-3 px-6 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors flex items-center justify-center"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            <span>Back to Home</span>
          </button>
        </div>

        <p className="text-sm text-gray-500 mt-6">
          Need help? Contact our support team.
        </p>
      </div>
    </div>
  );
}
