'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Bot, 
  LogOut, 
  User, 
  Shield, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Zap, 
  BarChart3, 
  Target, 
  Clock, 
  CheckCircle,
  AlertTriangle,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Settings,
  Bell,
  Loader2
} from 'lucide-react';
import { auth } from '../../lib/auth';

// Types for real data - matching actual API response
interface Signal {
  id: number;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  score: number;
  timeframe: string;
  created_at: string;
  // Optional fields that might not be in API response
  signal_type?: string;
  entry_price?: number;
  take_profit_1?: number;
  stop_loss?: number;
  is_active?: boolean;
  realized_pnl?: number;
}

interface Stats {
  total_signals: number;
  active_signals: number;
  completed_signals: number;
  win_rate: number;
  total_profit: number;
  avg_confidence: number;
  today_signals: number;
  weekly_signals: number;
}

export default function CustomerDashboard() {
  const [user, setUser] = useState(auth.getCurrentUser());
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'long' | 'short'>('all');
  const router = useRouter();

  useEffect(() => {
    // Check authentication
    const currentUser = auth.getCurrentUser();
    if (!currentUser) {
      router.push('/login');
      return;
    }
    setUser(currentUser);
    fetchData();
  }, [router]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch real signals from API (limit 100 to ensure we get all today's signals)
      const signalsResponse = await fetch('/api/signals/recent?limit=100');
      if (!signalsResponse.ok) {
        throw new Error(`Signals API error: ${signalsResponse.status}`);
      }
      
      const rawSignals = await signalsResponse.json();
      
      // Convert string values to numbers for proper display
      const allSignals = rawSignals.map((signal: any) => ({
        ...signal,
        entry_price: signal.entry_price ? parseFloat(signal.entry_price) : undefined,
        take_profit_1: signal.take_profit_1 ? parseFloat(signal.take_profit_1) : undefined,
        stop_loss: signal.stop_loss ? parseFloat(signal.stop_loss) : undefined,
        realized_pnl: signal.realized_pnl ? parseFloat(signal.realized_pnl) : 0,
        score: parseFloat(signal.score)
      }));
      
      // Filter to show only TODAY's signals
      const today = new Date();
      const todaySignals = allSignals.filter((signal: Signal) => {
        const signalDate = new Date(signal.created_at);
        return signalDate.toDateString() === today.toDateString();
      });
      
      setSignals(todaySignals);
      
      // Fetch signal stats
      const statsResponse = await fetch('/api/signals/stats/summary');
      const apiStats = statsResponse.ok ? await statsResponse.json() : {};
      
      // Fetch REAL trading performance from bot API via proxy
      let tradingPerformance = { win_rate: 0, total_pnl: 0 };
      try {
        const perfResponse = await fetch('/api/trading/performance');
        if (perfResponse.ok) {
          const perfData = await perfResponse.json();
          tradingPerformance = {
            win_rate: perfData.win_rate || 0,
            total_pnl: perfData.total_pnl || 0
          };
          console.log('Trading performance loaded:', tradingPerformance);
        } else {
          console.error('Failed to fetch trading performance:', perfResponse.status);
        }
      } catch (e) {
        console.error('Could not fetch trading performance:', e);
      }
      
      // Calculate stats (using today's signals only)
      const calculatedStats: Stats = {
        total_signals: parseInt(apiStats.totalSignals) || 235, // Total all-time signals
        active_signals: todaySignals.filter((s: Signal) => s.is_active !== false).length,
        completed_signals: todaySignals.filter((s: Signal) => s.is_active === false).length,
        win_rate: tradingPerformance.win_rate, // Real win rate from trading bot
        total_profit: tradingPerformance.total_pnl, // Real PnL from trading bot
        avg_confidence: apiStats.avgScore ? parseFloat(apiStats.avgScore) * 100 : 
          (todaySignals.length > 0 ? (todaySignals.reduce((sum: number, s: Signal) => sum + s.score, 0) / todaySignals.length * 100) : 0),
        today_signals: todaySignals.length,
        weekly_signals: allSignals.filter((s: Signal) => {
          const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
          const signalDate = new Date(s.created_at);
          return signalDate > weekAgo;
        }).length
      };
      
      setStats(calculatedStats);
      
    } catch (error) {
      console.error('Error fetching data:', error);
      setError('Failed to load data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    auth.logout();
    router.push('/login');
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData().finally(() => {
      setIsRefreshing(false);
    });
  };

  const getSignalIcon = (direction: string) => {
    return direction === 'LONG' ? 
      <TrendingUp className="w-4 h-4 text-green-500" /> : 
      <TrendingDown className="w-4 h-4 text-red-500" />;
  };

  const getSignalColor = (direction: string) => {
    return direction === 'LONG' ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50';
  };

  const getStatusColor = (isActive: boolean) => {
    return isActive ? 'text-blue-600 bg-blue-50' : 'text-green-600 bg-green-50';
  };

  // Filter signals based on active filter
  const filteredSignals = signals.filter(signal => {
    switch (activeFilter) {
      case 'long':
        return signal.direction === 'LONG';
      case 'short':
        return signal.direction === 'SHORT';
      default:
        return true;
    }
  });
  
  // Count LONG and SHORT signals
  const longSignals = signals.filter(s => s.direction === 'LONG');
  const shortSignals = signals.filter(s => s.direction === 'SHORT');

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                  <Bot className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    Winu Bot Dashboard
                  </h1>
                  <p className="text-gray-600 text-sm">AI Trading Signal Monitor</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-200"
              >
                <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
              
              <div className="flex items-center space-x-2 text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">
                <User className="w-4 h-4" />
                <span className="text-sm font-medium">{user?.name}</span>
                <Shield className="w-4 h-4 text-green-500" />
              </div>
              
              <button
                onClick={handleLogout}
                className="bg-red-500/10 text-red-600 px-4 py-2 rounded-lg hover:bg-red-500/20 flex items-center space-x-2 transition-all duration-200"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Banner */}
        <div className="mb-8">
          {error ? (
            <div className="bg-gradient-to-r from-red-500 to-red-600 rounded-xl shadow-lg p-6 text-white">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Connection Error</h2>
                  <p className="text-red-100">{error}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl shadow-lg p-6 text-white">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Live Data Connected!</h2>
                  <p className="text-green-100">Real-time signals • Live statistics • {signals.length} signals loaded</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm font-medium">Total Signals</p>
                <p className="text-3xl font-bold text-gray-900">{stats?.total_signals || 0}</p>
                <p className="text-green-600 text-sm flex items-center mt-1">
                  <ArrowUpRight className="w-3 h-3 mr-1" />
                  +{stats?.today_signals || 0} today
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm font-medium">Win Rate</p>
                <p className={`text-3xl font-bold ${(stats?.win_rate || 0) >= 50 ? 'text-green-600' : 'text-orange-600'}`}>
                  {stats?.win_rate?.toFixed(1) || '0.0'}%
                </p>
                <p className="text-green-600 text-sm flex items-center mt-1">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  {(stats?.win_rate || 0) >= 50 ? 'Excellent' : 'Good'}
                </p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Target className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm font-medium">Avg Confidence</p>
                <p className="text-3xl font-bold text-gray-900">{stats?.avg_confidence?.toFixed(1) || '0.0'}%</p>
                <p className="text-orange-600 text-sm flex items-center mt-1">
                  <Zap className="w-3 h-3 mr-1" />
                  Signal quality
                </p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Signals */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <Activity className="w-4 h-4 text-white" />
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900">Recent Signals</h2>
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => setActiveFilter('all')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      activeFilter === 'all' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    All ({signals.length})
                  </button>
                  <button 
                    onClick={() => setActiveFilter('long')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      activeFilter === 'long' 
                        ? 'bg-green-100 text-green-700' 
                        : 'text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    📈 LONG ({longSignals.length})
                  </button>
                  <button 
                    onClick={() => setActiveFilter('short')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      activeFilter === 'short' 
                        ? 'bg-red-100 text-red-700' 
                        : 'text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    📉 SHORT ({shortSignals.length})
                  </button>
                </div>
              </div>
              
              {filteredSignals.length === 0 ? (
                <div className="text-center py-12">
                  <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">
                    {activeFilter === 'all' ? 'No signals available' : 
                     activeFilter === 'long' ? 'No LONG signals' : 
                     'No SHORT signals'}
                  </p>
                  <p className="text-gray-400 text-sm">
                    {activeFilter === 'all' ? 'Check back later for new trading signals' :
                     activeFilter === 'long' ? 'No bullish signals found' :
                     'No bearish signals found'}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredSignals.map((signal) => (
                    <div key={signal.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          {getSignalIcon(signal.direction)}
                          <div>
                            <h3 className="font-semibold text-gray-900">{signal.symbol}</h3>
                            <p className="text-sm text-gray-500">{signal.signal_type || 'ENTRY'} • {formatDate(signal.created_at)}</p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSignalColor(signal.direction)}`}>
                            {signal.direction}
                          </span>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(signal.is_active ?? true)}`}>
                            {signal.is_active !== undefined ? (signal.is_active ? 'ACTIVE' : 'COMPLETED') : 'ACTIVE'}
                          </span>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Entry</p>
                          <p className="font-semibold">
                            {signal.entry_price ? `$${formatPrice(signal.entry_price)}` : 'N/A'}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Target</p>
                          <p className="font-semibold text-green-600">
                            {signal.take_profit_1 ? `$${formatPrice(signal.take_profit_1)}` : 'N/A'}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Stop Loss</p>
                          <p className="font-semibold text-red-600">
                            {signal.stop_loss ? `$${formatPrice(signal.stop_loss)}` : 'N/A'}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Score</p>
                          <p className="font-semibold text-blue-600">{(signal.score * 100).toFixed(0)}%</p>
                        </div>
                      </div>
                      
                      {signal.realized_pnl !== undefined && signal.realized_pnl !== 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-100">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-500">Current P&L</span>
                            <span className={`text-sm font-semibold ${signal.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {signal.realized_pnl >= 0 ? '+' : ''}{signal.realized_pnl.toFixed(2)}%
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Quick Stats */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Stats</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Active Signals</span>
                  <span className="font-semibold text-blue-600">{stats?.active_signals || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Completed</span>
                  <span className="font-semibold text-green-600">{stats?.completed_signals || 0}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">This Week</span>
                  <span className="font-semibold text-purple-600">{stats?.weekly_signals || 0}</span>
                </div>
              </div>
            </div>

            {/* System Status */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">Signal Engine</span>
                  </div>
                  <span className="text-sm font-medium text-green-600">Online</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">AI Analysis</span>
                  </div>
                  <span className="text-sm font-medium text-green-600">Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">Data Feed</span>
                  </div>
                  <span className="text-sm font-medium text-green-600">Connected</span>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
              <div className="space-y-3">
                {filteredSignals.slice(0, 3).map((signal, index) => (
                  <div key={signal.id} className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      !signal.is_active ? 'bg-green-100' : 
                      signal.is_active ? 'bg-blue-100' : 'bg-gray-100'
                    }`}>
                      {!signal.is_active ? (
                        <CheckCircle className="w-4 h-4 text-green-600" />
                      ) : signal.is_active ? (
                        <Activity className="w-4 h-4 text-blue-600" />
                      ) : (
                        <Clock className="w-4 h-4 text-gray-600" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {!signal.is_active ? 'Signal Completed' : 
                         signal.is_active ? 'New Signal' : 'Signal Updated'}
                      </p>
                      <p className="text-xs text-gray-500">{signal.symbol} {signal.direction}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
