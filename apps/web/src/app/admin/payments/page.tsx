'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

interface DashboardStats {
  total_payments: number;
  successful_payments: number;
  activation_gaps: number;
  pending_payments: number;
}

interface PaymentGap {
  payment_id: number;
  user_id: number;
  username: string;
  email: string;
  plan_id: string;
  payment_status: string;
  subscription_status: string;
  subscription_tier: string;
  transaction_id: string;
  payment_created: string;
}

interface Payment {
  id: number;
  user_id: number;
  username: string;
  plan_id: string;
  amount_usd: string;
  payment_status: string;
  payment_method: string;
  created_at: string;
  subscription_status: string;
}

interface Webhook {
  id: number;
  payment_method: string;
  webhook_type: string;
  user_id: number | null;
  processing_status: string;
  signature_valid: boolean | null;
  created_at: string;
}

interface DashboardData {
  stats: DashboardStats;
  gaps: PaymentGap[];
  recent_payments: Payment[];
  recent_webhooks: Webhook[];
}

export default function AdminPaymentDashboard() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('Never');

  const fetchDashboardData = async () => {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
      
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('/api/admin/payments/data', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.status === 401) {
        router.push('/login');
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const dashboardData = await response.json();
      setData(dashboardData);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(null);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleManualActivate = async (userId: number, planId: string) => {
    if (!confirm(`Manually activate subscription for user ${userId} with plan ${planId}?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('winu_token');
      const response = await fetch('/api/admin/subscriptions/activate-manual', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId,
          plan_id: planId,
          reason: 'Manual activation from dashboard - webhook failure'
        })
      });

      const result = await response.json();
      if (result.success) {
        alert('Subscription activated successfully!');
        fetchDashboardData(); // Refresh
      } else {
        alert('Failed to activate: ' + (result.message || 'Unknown error'));
      }
    } catch (error) {
      alert('Error activating subscription: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-white animate-spin mx-auto mb-4" />
          <p className="text-white">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center p-4">
        <div className="bg-red-500/20 border-2 border-red-500 rounded-lg p-8 max-w-lg">
          <h2 className="text-2xl font-bold text-red-400 mb-4">Error Loading Dashboard</h2>
          <p className="text-white mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-red-600 hover:bg-red-700 px-6 py-2 rounded text-white font-semibold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 text-white p-4 md:p-8">
      <div className="container mx-auto">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-4xl font-bold mb-2">💰 Payment Activation Dashboard</h1>
          <p className="text-blue-200">Real-time payment monitoring and gap detection</p>
          <div className="mt-4 flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse mr-2"></div>
            <span className="text-sm text-green-300">Live Monitoring Active</span>
          </div>
        </header>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="text-sm text-blue-200 mb-2">Total Payments (24h)</div>
            <div className="text-3xl font-bold">{data.stats.total_payments}</div>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="text-sm text-green-200 mb-2">Successful</div>
            <div className="text-3xl font-bold text-green-400">{data.stats.successful_payments}</div>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="text-sm text-red-200 mb-2">Activation Gaps</div>
            <div className="text-3xl font-bold text-red-400">{data.stats.activation_gaps}</div>
          </div>
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="text-sm text-yellow-200 mb-2">Pending</div>
            <div className="text-3xl font-bold text-yellow-400">{data.stats.pending_payments}</div>
          </div>
        </div>

        {/* Activation Gaps Alert */}
        {data.gaps.length > 0 && (
          <div className="bg-red-500/20 border-2 border-red-500 rounded-lg p-6 mb-8">
            <h2 className="text-2xl font-bold text-red-400 mb-4">🚨 Payment Activation Gaps Detected</h2>
            <p className="text-red-200 mb-4">The following payments have completed but subscriptions were NOT activated:</p>
            <div className="space-y-3">
              {data.gaps.map((gap) => (
                <div key={gap.payment_id} className="bg-red-900/30 border border-red-500/50 rounded p-4">
                  <div className="flex justify-between items-start flex-wrap gap-4">
                    <div>
                      <div className="font-bold">User: {gap.username} (ID: {gap.user_id})</div>
                      <div className="text-sm text-red-200">Plan: {gap.plan_id} | Payment: {gap.payment_status}</div>
                      <div className="text-sm text-red-200">User Status: {gap.subscription_status} / {gap.subscription_tier}</div>
                      <div className="text-xs text-gray-400 mt-2">{gap.payment_created}</div>
                    </div>
                    <button
                      onClick={() => handleManualActivate(gap.user_id, gap.plan_id)}
                      className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded text-sm font-semibold whitespace-nowrap"
                    >
                      Manual Activate
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Payments */}
        <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20 mb-8">
          <h2 className="text-2xl font-bold mb-4">Recent Payments (Last 2 Hours)</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="py-3 px-2">User</th>
                  <th className="py-3 px-2">Plan</th>
                  <th className="py-3 px-2">Amount</th>
                  <th className="py-3 px-2">Status</th>
                  <th className="py-3 px-2">Method</th>
                  <th className="py-3 px-2">Time</th>
                  <th className="py-3 px-2">Sub Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {data.recent_payments.length > 0 ? (
                  data.recent_payments.map((payment) => (
                    <tr key={payment.id}>
                      <td className="py-3 px-2">{payment.username || 'N/A'} ({payment.user_id})</td>
                      <td className="py-3 px-2">{payment.plan_id}</td>
                      <td className="py-3 px-2">${payment.amount_usd}</td>
                      <td className={`py-3 px-2 ${payment.payment_status === 'completed' ? 'text-green-400' : 'text-yellow-400'}`}>
                        {payment.payment_status}
                      </td>
                      <td className="py-3 px-2">{payment.payment_method}</td>
                      <td className="py-3 px-2 text-gray-400">{payment.created_at}</td>
                      <td className={`py-3 px-2 ${payment.subscription_status === 'active' ? 'text-green-400' : 'text-red-400'}`}>
                        {payment.subscription_status}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-400">No recent payments</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Webhook Logs */}
        <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20 mb-8">
          <h2 className="text-2xl font-bold mb-4">Recent Webhook Activity (Last 30 min)</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/20">
                  <th className="py-3 px-2">Method</th>
                  <th className="py-3 px-2">Type</th>
                  <th className="py-3 px-2">User</th>
                  <th className="py-3 px-2">Status</th>
                  <th className="py-3 px-2">Signature</th>
                  <th className="py-3 px-2">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {data.recent_webhooks.length > 0 ? (
                  data.recent_webhooks.map((webhook) => {
                    const statusColor = webhook.processing_status === 'completed' ? 'text-green-400' : 
                                      webhook.processing_status === 'failed' ? 'text-red-400' : 'text-yellow-400';
                    const sigColor = webhook.signature_valid === true ? 'text-green-400' : 
                                   webhook.signature_valid === false ? 'text-red-400' : 'text-gray-400';
                    const sigText = webhook.signature_valid === true ? '✓ Valid' : 
                                  webhook.signature_valid === false ? '✗ Invalid' : '-';
                    
                    return (
                      <tr key={webhook.id}>
                        <td className="py-3 px-2">{webhook.payment_method}</td>
                        <td className="py-3 px-2">{webhook.webhook_type || '-'}</td>
                        <td className="py-3 px-2">{webhook.user_id || '-'}</td>
                        <td className={`py-3 px-2 ${statusColor}`}>{webhook.processing_status}</td>
                        <td className={`py-3 px-2 ${sigColor}`}>{sigText}</td>
                        <td className="py-3 px-2 text-gray-400">{webhook.created_at}</td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-400">No recent webhooks</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="text-center text-sm text-gray-400 mt-8">
          <p>Auto-refreshing every 10 seconds</p>
          <p className="mt-2">Last updated: {lastUpdated}</p>
        </div>
      </div>
    </div>
  );
}



