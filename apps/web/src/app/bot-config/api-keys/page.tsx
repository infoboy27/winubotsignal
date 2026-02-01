'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Trash2, Edit2, CheckCircle, XCircle, Eye, EyeOff, RefreshCw, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface APIKey {
  id: number;
  api_name: string;
  api_key_masked: string;
  account_type: string;
  test_mode: boolean;
  is_active: boolean;
  is_verified: boolean;
  auto_trade_enabled: boolean;
  max_position_size_usd: number;
  leverage: number;
  max_daily_trades: number;
  total_orders: number;
  successful_orders: number;
  total_pnl: number;
  current_balance: number;
}

export default function APIKeysManagement() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    api_key: '',
    api_secret: '',
    api_name: '',
    account_type: 'futures',
    test_mode: false,
    max_position_size_usd: 1000,
    leverage: 10,
    max_daily_trades: 5,
    max_risk_per_trade: 0.02,
    max_daily_loss: 0.05,
    position_sizing_mode: 'fixed',
    position_size_value: 100,
    auto_trade_enabled: false
  });
  const [showSecrets, setShowSecrets] = useState<{[key: string]: boolean}>({});

  useEffect(() => {
    fetchAPIKeys();
  }, []);

  const fetchAPIKeys = async () => {
    try {
      const token = localStorage.getItem('winu_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('/api/bot/multi-account/api-keys', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.status === 401) {
        router.push('/login');
        return;
      }

      const data = await response.json();
      setApiKeys(data.api_keys || []);
    } catch (error) {
      toast.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAPIKey = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const token = localStorage.getItem('winu_token');
    try {
      const response = await fetch('/api/bot/multi-account/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });

      const result = await response.json();
      
      if (response.ok) {
        toast.success('API key added successfully!');
        setShowAddForm(false);
        fetchAPIKeys();
        
        // Reset form
        setFormData({
          api_key: '', api_secret: '', api_name: '',
          account_type: 'futures', test_mode: false,
          max_position_size_usd: 1000, leverage: 10,
          max_daily_trades: 5, max_risk_per_trade: 0.02,
          max_daily_loss: 0.05, position_sizing_mode: 'fixed',
          position_size_value: 100, auto_trade_enabled: false
        });
      } else {
        toast.error(result.detail || 'Failed to add API key');
      }
    } catch (error) {
      toast.error('Error adding API key');
    }
  };

  const handleVerify = async (id: number) => {
    const token = localStorage.getItem('winu_token');
    try {
      const response = await fetch(`/api/bot/multi-account/api-keys/${id}/verify`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const result = await response.json();
      
      if (response.ok) {
        toast.success(`Verified! Balance: $${result.balance?.toFixed(2) || 0}`);
        fetchAPIKeys();
      } else {
        toast.error(result.detail || 'Verification failed');
      }
    } catch (error) {
      toast.error('Error verifying API key');
    }
  };

  const handleToggleAutoTrade = async (id: number, currentState: boolean) => {
    const token = localStorage.getItem('winu_token');
    try {
      const response = await fetch(`/api/bot/multi-account/api-keys/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ auto_trade_enabled: !currentState })
      });

      if (response.ok) {
        toast.success(`Auto-trade ${!currentState ? 'enabled' : 'disabled'}`);
        fetchAPIKeys();
      } else {
        toast.error('Failed to update');
      }
    } catch (error) {
      toast.error('Error updating');
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete API key "${name}"? This cannot be undone.`)) return;
    
    const token = localStorage.getItem('winu_token');
    try {
      const response = await fetch(`/api/bot/multi-account/api-keys/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('API key deleted');
        fetchAPIKeys();
      } else {
        toast.error('Failed to delete');
      }
    } catch (error) {
      toast.error('Error deleting');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-white animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 p-4 md:p-8">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">🔑 API Key Management</h1>
            <p className="text-blue-200">Manage your Binance accounts for multi-account trading</p>
          </div>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg font-semibold text-white flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add API Key
          </button>
        </div>

        {/* Add Form */}
        {showAddForm && (
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20 mb-8">
            <h2 className="text-2xl font-bold text-white mb-4">Add New Binance Account</h2>
            <form onSubmit={handleAddAPIKey} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">Account Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.api_name}
                    onChange={(e) => setFormData({...formData, api_name: e.target.value})}
                    className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                    placeholder="My Main Trading Account"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">Account Type *</label>
                  <select
                    value={formData.account_type}
                    onChange={(e) => setFormData({...formData, account_type: e.target.value})}
                    className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                  >
                    <option value="spot">Spot</option>
                    <option value="futures">Futures</option>
                    <option value="both">Both</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-blue-200 mb-2">Binance API Key *</label>
                <input
                  type={showSecrets['api_key'] ? 'text' : 'password'}
                  required
                  value={formData.api_key}
                  onChange={(e) => setFormData({...formData, api_key: e.target.value})}
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-blue-200 mb-2">Binance API Secret *</label>
                <input
                  type={showSecrets['api_secret'] ? 'text' : 'password'}
                  required
                  value={formData.api_secret}
                  onChange={(e) => setFormData({...formData, api_secret: e.target.value})}
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">Max Position Size (USD)</label>
                  <input
                    type="number"
                    value={formData.max_position_size_usd}
                    onChange={(e) => setFormData({...formData, max_position_size_usd: parseFloat(e.target.value)})}
                    className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">Leverage</label>
                  <input
                    type="number"
                    value={formData.leverage}
                    onChange={(e) => setFormData({...formData, leverage: parseFloat(e.target.value)})}
                    className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-blue-200 mb-2">Max Daily Trades</label>
                  <input
                    type="number"
                    value={formData.max_daily_trades}
                    onChange={(e) => setFormData({...formData, max_daily_trades: parseInt(e.target.value)})}
                    className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded text-white"
                  />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-white">
                  <input
                    type="checkbox"
                    checked={formData.test_mode}
                    onChange={(e) => setFormData({...formData, test_mode: e.target.checked})}
                    className="w-5 h-5"
                  />
                  Test Mode (Testnet)
                </label>
                <label className="flex items-center gap-2 text-white">
                  <input
                    type="checkbox"
                    checked={formData.auto_trade_enabled}
                    onChange={(e) => setFormData({...formData, auto_trade_enabled: e.target.checked})}
                    className="w-5 h-5"
                  />
                  Enable Auto-Trading
                </label>
              </div>

              <div className="flex gap-4">
                <button type="submit" className="bg-green-600 hover:bg-green-700 px-6 py-2 rounded text-white font-semibold">
                  Add API Key
                </button>
                <button type="button" onClick={() => setShowAddForm(false)} className="bg-gray-600 hover:bg-gray-700 px-6 py-2 rounded text-white">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* API Keys List */}
        {apiKeys.length === 0 ? (
          <div className="bg-white/10 backdrop-blur-lg rounded-lg p-12 border border-white/20 text-center">
            <div className="text-6xl mb-4">🔑</div>
            <h3 className="text-2xl font-bold text-white mb-2">No API Keys Yet</h3>
            <p className="text-blue-200 mb-6">Add your first Binance API key to start multi-account trading</p>
            <button
              onClick={() => setShowAddForm(true)}
              className="bg-green-600 hover:bg-green-700 px-8 py-3 rounded-lg font-semibold text-white inline-flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              Add Your First API Key
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {apiKeys.map((key) => (
              <div key={key.id} className="bg-white/10 backdrop-blur-lg rounded-lg p-6 border border-white/20">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-2xl font-bold text-white">{key.api_name}</h3>
                    <p className="text-sm text-gray-400">API Key: {key.api_key_masked}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleVerify(key.id)}
                      className="bg-blue-600 hover:bg-blue-700 p-2 rounded"
                      title="Verify Connection"
                    >
                      <RefreshCw className="w-4 h-4 text-white" />
                    </button>
                    <button
                      onClick={() => handleDelete(key.id, key.api_name)}
                      className="bg-red-600 hover:bg-red-700 p-2 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4 text-white" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-400">Type</div>
                    <div className="text-white font-semibold">{key.account_type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Mode</div>
                    <div className="text-white font-semibold">{key.test_mode ? '🧪 Test' : '🚀 Live'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Verified</div>
                    <div>{key.is_verified ? <CheckCircle className="w-5 h-5 text-green-400" /> : <XCircle className="w-5 h-5 text-red-400" />}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Status</div>
                    <div className="text-white font-semibold">{key.is_active ? '✅ Active' : '⏸️  Inactive'}</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-400">Max Position</div>
                    <div className="text-white font-semibold">${key.max_position_size_usd}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Leverage</div>
                    <div className="text-white font-semibold">{key.leverage}x</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Balance</div>
                    <div className="text-white font-semibold">${key.current_balance?.toFixed(2) || '0.00'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">PNL</div>
                    <div className={`font-semibold ${key.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ${key.total_pnl?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <div className="text-xs text-gray-400">Total Orders</div>
                    <div className="text-white font-semibold">{key.total_orders || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Successful</div>
                    <div className="text-green-400 font-semibold">{key.successful_orders || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Failed</div>
                    <div className="text-red-400 font-semibold">{key.total_orders - key.successful_orders || 0}</div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-white/10">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={key.auto_trade_enabled}
                      onChange={() => handleToggleAutoTrade(key.id, key.auto_trade_enabled)}
                      className="w-5 h-5"
                    />
                    <span className="text-white font-semibold">Auto-Trade Enabled</span>
                  </label>
                  {key.auto_trade_enabled && (
                    <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm font-semibold">
                      🟢 Live Trading
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}



