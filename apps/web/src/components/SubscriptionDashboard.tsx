'use client';

import { useState, useEffect } from 'react';

interface SubscriptionInfo {
  subscription_tier: string;
  subscription_status: string;
  trial_used: boolean;
  trial_start_date?: string;
  trial_dashboard_access_count: number;
  payment_due_date?: string;
  access_revoked_at?: string;
  current_plan?: {
    id: string;
    name: string;
    price_usd: number;
    price_usdt: number;
    interval: string;
    features: string[];
    telegram_access: boolean;
    support_level: string;
  };
  telegram_access: Array<{
    group_name: string;
    access_granted_at: string;
    is_active: boolean;
  }>;
  last_payment_date?: string;
  payment_method: string;
}

interface PaymentTransaction {
  id: number;
  plan_id: string;
  amount_usdt: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

export default function SubscriptionDashboard() {
  const [subscriptionInfo, setSubscriptionInfo] = useState<SubscriptionInfo | null>(null);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscriptionData();
  }, []);

  const fetchSubscriptionData = async () => {
    try {
      const [infoResponse, transactionsResponse] = await Promise.all([
        fetch('/api/subscriptions/info'),
        fetch('/api/subscriptions/transactions')
      ]);

      if (infoResponse.ok) {
        const infoData = await infoResponse.json();
        setSubscriptionInfo(infoData);
      }

      if (transactionsResponse.ok) {
        const transactionsData = await transactionsResponse.json();
        setTransactions(transactionsData);
      }
    } catch (err) {
      setError('Failed to load subscription information');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-600 bg-green-100';
      case 'trial': return 'text-blue-600 bg-blue-100';
      case 'past_due': return 'text-red-600 bg-red-100';
      case 'inactive': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getTrialInfo = () => {
    if (!subscriptionInfo?.trial_start_date) return null;

    const startDate = new Date(subscriptionInfo.trial_start_date);
    const daysRemaining = Math.max(0, 7 - Math.floor((Date.now() - startDate.getTime()) / (1000 * 60 * 60 * 24)));
    const accessRemaining = Math.max(0, 1 - subscriptionInfo.trial_dashboard_access_count);

    return {
      daysRemaining,
      accessRemaining,
      isExpired: daysRemaining === 0 || accessRemaining === 0
    };
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    );
  }

  const trialInfo = getTrialInfo();

  return (
    <div className="space-y-6">
      {/* Current Subscription Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Current Subscription</h2>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-600">Plan</p>
            <p className="text-lg font-semibold capitalize">{subscriptionInfo?.subscription_tier}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Status</p>
            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(subscriptionInfo?.subscription_status || 'inactive')}`}>
              {subscriptionInfo?.subscription_status}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-600">Payment Method</p>
            <p className="text-lg font-semibold capitalize">{subscriptionInfo?.payment_method}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Last Payment</p>
            <p className="text-lg font-semibold">
              {subscriptionInfo?.last_payment_date ? formatDate(subscriptionInfo.last_payment_date) : 'N/A'}
            </p>
          </div>
        </div>

        {/* Trial Information */}
        {trialInfo && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <h3 className="text-lg font-semibold text-blue-900 mb-2">Trial Information</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-blue-700">Days Remaining</p>
                <p className="text-xl font-bold text-blue-900">{trialInfo.daysRemaining}</p>
              </div>
              <div>
                <p className="text-sm text-blue-700">Dashboard Access Remaining</p>
                <p className="text-xl font-bold text-blue-900">{trialInfo.accessRemaining}</p>
              </div>
            </div>
            {trialInfo.isExpired && (
              <p className="text-red-600 text-sm mt-2">
                Your trial has expired. Please subscribe to continue using the service.
              </p>
            )}
          </div>
        )}

        {/* Payment Due Date */}
        {subscriptionInfo?.payment_due_date && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <h3 className="text-lg font-semibold text-yellow-900 mb-2">Payment Information</h3>
            <p className="text-sm text-yellow-700">
              Next payment due: <span className="font-semibold">{formatDate(subscriptionInfo.payment_due_date)}</span>
            </p>
          </div>
        )}

        {/* Access Revoked Warning */}
        {subscriptionInfo?.access_revoked_at && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-red-900 mb-2">Access Revoked</h3>
            <p className="text-sm text-red-700">
              Your access was revoked on {formatDate(subscriptionInfo.access_revoked_at)} due to overdue payment.
              Please update your payment to restore access.
            </p>
          </div>
        )}
      </div>

      {/* Plan Features */}
      {subscriptionInfo?.current_plan && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Plan Features</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">{subscriptionInfo.current_plan.name}</h3>
              <p className="text-2xl font-bold text-gray-900 mb-4">
                {formatCurrency(subscriptionInfo.current_plan.price_usd)}/{subscriptionInfo.current_plan.interval}
              </p>
            </div>
            <div>
              <ul className="space-y-2">
                {subscriptionInfo.current_plan.features.map((feature, index) => (
                  <li key={index} className="flex items-center">
                    <svg className="w-5 h-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Telegram Access */}
      {subscriptionInfo?.telegram_access && subscriptionInfo.telegram_access.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Telegram Access</h2>
          <div className="space-y-3">
            {subscriptionInfo.telegram_access.map((access, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-semibold capitalize">{access.group_name.replace('_', ' ')}</p>
                  <p className="text-sm text-gray-600">
                    Access granted: {formatDate(access.access_granted_at)}
                  </p>
                </div>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                  access.is_active ? 'text-green-600 bg-green-100' : 'text-red-600 bg-red-100'
                }`}>
                  {access.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Payment History */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Payment History</h2>
        {transactions.length === 0 ? (
          <p className="text-gray-600">No payment history available.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Plan
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {transactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(transaction.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 capitalize">
                      {transaction.plan_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(transaction.amount_usdt)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        transaction.status === 'completed' ? 'text-green-600 bg-green-100' :
                        transaction.status === 'pending' ? 'text-yellow-600 bg-yellow-100' :
                        'text-red-600 bg-red-100'
                      }`}>
                        {transaction.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Manage Subscription</h2>
        <div className="flex flex-wrap gap-4">
          {subscriptionInfo?.subscription_tier === 'free' && !subscriptionInfo?.trial_used && (
            <button
              onClick={() => window.location.href = '/subscription'}
              className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700"
            >
              Start Free Trial
            </button>
          )}
          
          {subscriptionInfo?.subscription_tier === 'free' && subscriptionInfo?.trial_used && (
            <button
              onClick={() => window.location.href = '/subscription'}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
            >
              Subscribe Now
            </button>
          )}
          
          {subscriptionInfo?.subscription_tier !== 'free' && (
            <button
              onClick={() => window.location.href = '/subscription'}
              className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700"
            >
              Change Plan
            </button>
          )}
          
          {subscriptionInfo?.access_revoked_at && (
            <button
              onClick={() => window.location.href = '/subscription'}
              className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700"
            >
              Update Payment
            </button>
          )}
        </div>
      </div>
    </div>
  );
}













