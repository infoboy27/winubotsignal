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

export default function DashboardSimplePage() {
  const [user, setUser] = useState(auth.getCurrentUser());
  const [signals, setSignals] = useState<Signal[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'completed'>('all');
  const router = useRouter();

  useEffect(() => {
    // Removed authentication check for demo purposes
    const currentUser = auth.getCurrentUser();
    setUser(currentUser);
    fetchData();
  }, [router]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      
      // Try to fetch real data from API first
      let realSignals: Signal[] = [];
      
      try {
        // Fetch real signals from API
        const signalsResponse = await fetch('/api/signals/recent?limit=20');
        if (signalsResponse.ok) {
          const rawSignals = await signalsResponse.json();
          
          // Convert string values to numbers for proper display
          realSignals = rawSignals.map((signal: any) => ({
            ...signal,
            entry_price: signal.entry_price ? parseFloat(signal.entry_price) : undefined,
            take_profit_1: signal.take_profit_1 ? parseFloat(signal.take_profit_1) : undefined,
            stop_loss: signal.stop_loss ? parseFloat(signal.stop_loss) : undefined,
            realized_pnl: signal.realized_pnl ? parseFloat(signal.realized_pnl) : 0,
            score: parseFloat(signal.score)
          }));
          
          setSignals(realSignals);
        } else {
          throw new Error(`Signals API error: ${signalsResponse.status}`);
        }
        
        // Fetch real stats from API
        const statsResponse = await fetch('/api/signals/stats/summary');
        if (statsResponse.ok) {
          const apiStats = await statsResponse.json();
          
          // Convert API response to dashboard format
          const realStats: Stats = {
            total_signals: parseInt(apiStats.totalSignals) || 0,
            active_signals: 0, // API doesn't provide this
            completed_signals: 0, // API doesn't provide this
            win_rate: 0, // API doesn't provide this
            total_profit: 0, // API doesn't provide this
            avg_confidence: apiStats.avgScore ? parseFloat(apiStats.avgScore) * 100 : 0,
            today_signals: 0, // API doesn't provide this
            weekly_signals: 0 // API doesn't provide this
          };
          
          // If stats are empty (all zeros), calculate from signals
          if (realStats.total_signals === 0 && realSignals.length > 0) {
            const calculatedStats: Stats = {
              total_signals: realSignals.length,
              active_signals: realSignals.filter(s => s.is_active !== false).length, // Default to active if not specified
              completed_signals: realSignals.filter(s => s.is_active === false).length,
              win_rate: realSignals.length > 0 ? 
                (realSignals.filter(s => s.realized_pnl && s.realized_pnl > 0).length / realSignals.length * 100) : 0,
              total_profit: realSignals.reduce((sum, s) => sum + (s.realized_pnl || 0), 0),
              avg_confidence: realSignals.length > 0 ? 
                (realSignals.reduce((sum, s) => sum + s.score, 0) / realSignals.length * 100) : 0,
              today_signals: realSignals.filter(s => {
                const today = new Date();
                const signalDate = new Date(s.created_at);
                return signalDate.toDateString() === today.toDateString();
              }).length,
              weekly_signals: realSignals.filter(s => {
                const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
                const signalDate = new Date(s.created_at);
                return signalDate > weekAgo;
              }).length
            };
            setStats(calculatedStats);
          } else {
            setStats(realStats);
          }
        } else {
          throw new Error(`Stats API error: ${statsResponse.status}`);
        }
        
        return; // Exit early if real data loaded successfully
        
      } catch (apiError) {
        console.error('❌ API call failed:', apiError);
      }
      
      // Fallback to sample data if API fails
      const sampleSignals: Signal[] = [
        {
          id: 1,
          symbol: 'BTC/USDT',
          direction: 'LONG',
          score: 0.87,
          timeframe: '1h',
          created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          signal_type: 'ENTRY',
          entry_price: 43250.00,
          take_profit_1: 44500.00,
          stop_loss: 42500.00,
          is_active: true,
          realized_pnl: 2.3
        },
        {
          id: 2,
          symbol: 'ETH/USDT',
          direction: 'SHORT',
          score: 0.92,
          timeframe: '1h',
          created_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
          signal_type: 'ENTRY',
          entry_price: 2650.00,
          take_profit_1: 2580.00,
          stop_loss: 2700.00,
          is_active: true,
          realized_pnl: 1.8
        },
        {
          id: 3,
          symbol: 'SOL/USDT',
          direction: 'LONG',
          score: 0.78,
          timeframe: '1h',
          created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
          signal_type: 'ENTRY',
          entry_price: 98.50,
          take_profit_1: 105.00,
          stop_loss: 95.00,
          is_active: false,
          realized_pnl: 4.2
        },
        {
          id: 4,
          symbol: 'AVAX/USDT',
          direction: 'LONG',
          score: 0.75,
          timeframe: '1h',
          created_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          signal_type: 'ENTRY',
          entry_price: 26.43,
          take_profit_1: 27.22,
          stop_loss: 25.90,
          is_active: true,
          realized_pnl: 0.5
        },
        {
          id: 5,
          symbol: 'DOGE/USDT',
          direction: 'LONG',
          score: 0.70,
          timeframe: '1h',
          created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
          signal_type: 'ENTRY',
          entry_price: 0.240,
          take_profit_1: 0.247,
          stop_loss: 0.235,
          is_active: true,
          realized_pnl: 0.8
        }
      ];

      const sampleStats: Stats = {
        total_signals: 127,
        active_signals: 8,
        completed_signals: 119,
        win_rate: 73.2,
        total_profit: 8.4,
        avg_confidence: 82.1,
        today_signals: 3,
        weekly_signals: 18
      };

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSignals(sampleSignals);
      setStats(sampleStats);
      setError('⚠️ Using sample data - API connection failed. Check console for details.');
      
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
      case 'active':
        return signal.is_active;
      case 'completed':
        return !signal.is_active;
      default:
        return true;
    }
  });

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
          <p className="text-gray-600">Loading dashboard...</p>
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
                  <p className="text-green-100">Real-time signals • Live statistics • No API errors</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
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
                <p className="text-3xl font-bold text-gray-900">{stats?.win_rate?.toFixed(1) || '0.0'}%</p>
                <p className="text-green-600 text-sm flex items-center mt-1">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  Excellent
                </p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <Target className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-purple-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm font-medium">Total Profit</p>
                <p className="text-3xl font-bold text-gray-900">+{stats?.total_profit?.toFixed(1) || '0.0'}%</p>
                <p className="text-purple-600 text-sm flex items-center mt-1">
                  <DollarSign className="w-3 h-3 mr-1" />
                  This month
                </p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-6 h-6 text-purple-600" />
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
                  High quality
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
                    All
                  </button>
                  <button 
                    onClick={() => setActiveFilter('active')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      activeFilter === 'active' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    Active
                  </button>
                  <button 
                    onClick={() => setActiveFilter('completed')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      activeFilter === 'completed' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'text-gray-500 hover:bg-gray-100'
                    }`}
                  >
                    Completed
                  </button>
                </div>
              </div>
              
              {filteredSignals.length === 0 ? (
                <div className="text-center py-12">
                  <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">
                    {activeFilter === 'all' ? 'No signals available' : 
                     activeFilter === 'active' ? 'No active signals' : 
                     'No completed signals'}
                  </p>
                  <p className="text-gray-400 text-sm">
                    {activeFilter === 'all' ? 'Check back later for new trading signals' :
                     activeFilter === 'active' ? 'All signals have been completed' :
                     'No signals have been completed yet'}
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
                            <p className="text-sm text-gray-500">{signal.signal_type} • {formatDate(signal.created_at)}</p>
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
                      
                      {signal.realized_pnl !== undefined && (
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