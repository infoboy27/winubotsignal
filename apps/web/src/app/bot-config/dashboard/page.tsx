'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';
import Link from 'next/link';

interface Account {
  id: number;
  api_name: string;
  account_type: string;
  test_mode: boolean;
  is_active: boolean;
  auto_trade_enabled: boolean;
  total_orders: number;
  successful_orders: number;
  failed_orders: number;
  total_pnl: number;
  current_balance: number;
  leverage: number;
}

interface DashboardData {
  accounts: Account[];
  today_stats: {
    total: number;
    success: number;
  };
  summary: {
    total_accounts: number;
    active_accounts: number;
    total_balance: number;
    total_pnl: number;
  };
}

export default function MultiAccountDashboard() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);

  const fetchDashboard = async () => {
    try {
      const token = localStorage.getItem('winu_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('/api/bot/multi-account/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.status === 401) {
        router.push('/login');
        return;
      }

      const dashboardData = await response.json();
      setData(dashboardData);
    } catch (error) {
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-white animate-spin" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 p-4 md:p-8">
      <div className="container mx-auto max-w-7xl">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">📊 Multi-Account Dashboard</h1>
            <p className="text-blue-200">Overview of all your trading accounts</p>
          </div>
          <Link 
            href="/bot-config/api-keys"
            className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold text-white"
          >
            Manage API Keys
          </Link>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-blue-200 mb-2">Total Accounts</div>
                <div className="text-3xl font-bold text-white">{data.summary.total_accounts}</div>
                <div className="text-xs text-green-400 mt-1">{data.summary.active_accounts} active</div>
              </div>
              <Activity className="w-12 h-12 text-blue-400 opacity-50" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-blue-200 mb-2">Total Balance</div>
                <div className="text-3xl font-bold text-white">${data.summary.total_balance.toFixed(2)}</div>
                <div className="text-xs text-gray-400 mt-1">Combined USDT</div>
              </div>
              <DollarSign className="w-12 h-12 text-green-400 opacity-50" />
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-blue-200 mb-2">Total PNL</div>
                <div className={`text-3xl font-bold ${data.summary.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${data.summary.total_pnl.toFixed(2)}
                </div>
                <div className="text-xs text-gray-400 mt-1">All time</div>
              </div>
              {data.summary.total_pnl >= 0 ? (
                <TrendingUp className="w-12 h-12 text-green-400 opacity-50" />
              ) : (
                <TrendingDown className="w-12 h-12 text-red-400 opacity-50" />
              )}
            </div>
          </div>

          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
            <div>
              <div className="text-sm text-blue-200 mb-2">Today's Trades</div>
              <div className="text-3xl font-bold text-white">{data.today_stats.total}</div>
              <div className="text-xs text-green-400 mt-1">{data.today_stats.success} successful</div>
            </div>
          </div>
        </div>

        {/* Accounts List */}
        <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
          <h2 className="text-2xl font-bold text-white mb-6">Your Trading Accounts</h2>
          
          <div className="space-y-4">
            {data.accounts.map((account) => (
              <div key={account.id} className="bg-white/5 rounded-lg p-4 border border-white/10">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-lg font-bold text-white">{account.api_name}</div>
                    <div className="text-sm text-gray-400">
                      {account.account_type} | {account.test_mode ? 'Testnet' : 'Live'} | {account.leverage}x leverage
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {account.auto_trade_enabled && (
                      <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs font-semibold">
                        🟢 Auto-Trade ON
                      </span>
                    )}
                    {!account.is_active && (
                      <span className="bg-gray-500/20 text-gray-400 px-3 py-1 rounded-full text-xs font-semibold">
                        ⏸️ Inactive
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <div className="text-xs text-gray-400">Balance</div>
                    <div className="text-white font-semibold">${account.current_balance?.toFixed(2) || '0.00'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">PNL</div>
                    <div className={`font-semibold ${account.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ${account.total_pnl?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Total Orders</div>
                    <div className="text-white font-semibold">{account.total_orders || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Successful</div>
                    <div className="text-green-400 font-semibold">{account.successful_orders || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Failed</div>
                    <div className="text-red-400 font-semibold">{account.failed_orders || 0}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="text-center text-sm text-gray-400 mt-8">
          <p>Auto-refreshing every 10 seconds</p>
        </div>
      </div>
    </div>
  );
}



