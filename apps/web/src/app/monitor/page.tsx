'use client';

import { useState, useEffect } from 'react';
import { Activity, AlertTriangle, CheckCircle, Clock, Database, TrendingUp, RefreshCw } from 'lucide-react';

interface SystemStatus {
  timestamp: string;
  health: {
    services: {
      api: { status: string; error?: string };
      docker: Record<string, string>;
    };
  };
  data_ingestion: {
    status: string;
    total_candles: number;
    last_data_update: string;
    active_assets: number;
    total_assets: number;
  };
  signal_generation: {
    status: string;
    recent_signals: number;
    signals_today: number;
    latest_signal: any;
  };
  worker_logs: {
    status: string;
    has_errors: boolean;
    has_warnings: boolean;
    last_scan: string;
    last_ingestion: string;
  };
}

export default function MonitorPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/monitor/status');
      const data = await response.json();
      setStatus(data);
    } catch (error) {
      console.error('Error fetching status:', error);
    } finally {
      setLoading(false);
    }
  };

  const triggerDataIngestion = async () => {
    try {
      await fetch('/api/admin/ingest-data', { method: 'POST' });
      alert('Data ingestion triggered!');
      fetchStatus();
    } catch (error) {
      console.error('Error triggering data ingestion:', error);
    }
  };

  const triggerSignalGeneration = async () => {
    try {
      await fetch('/api/admin/generate-signals', { method: 'POST' });
      alert('Signal generation triggered!');
      fetchStatus();
    } catch (error) {
      console.error('Error triggering signal generation:', error);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchStatus, 30000); // Refresh every 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to fetch system status</h2>
          <p className="text-gray-600">Please check the API connection</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'success':
        return 'text-green-600 bg-green-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      case 'warning':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'success':
        return <CheckCircle className="h-5 w-5" />;
      case 'error':
        return <AlertTriangle className="h-5 w-5" />;
      default:
        return <Clock className="h-5 w-5" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">System Monitor</h1>
              <p className="text-gray-600">Real-time monitoring of Winu Bot Signal</p>
            </div>
            <div className="flex space-x-4">
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 rounded-lg flex items-center space-x-2 ${
                  autoRefresh ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'
                }`}
              >
                <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
                <span>{autoRefresh ? 'Auto Refresh ON' : 'Auto Refresh OFF'}</span>
              </button>
              <button
                onClick={fetchStatus}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
              >
                <RefreshCw className="h-4 w-4" />
                <span>Refresh Now</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* System Health */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Activity className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">API Status</p>
                <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status.health.services.api.status)}`}>
                  {getStatusIcon(status.health.services.api.status)}
                  <span className="ml-1">{status.health.services.api.status}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <Database className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Data Candles</p>
                <p className="text-2xl font-bold text-gray-900">{status.data_ingestion.total_candles.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <TrendingUp className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Recent Signals</p>
                <p className="text-2xl font-bold text-gray-900">{status.signal_generation.recent_signals}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Active Assets</p>
                <p className="text-2xl font-bold text-gray-900">{status.data_ingestion.active_assets}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Status */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Data Ingestion Status */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Data Ingestion</h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Status</span>
                  <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status.data_ingestion.status)}`}>
                    {getStatusIcon(status.data_ingestion.status)}
                    <span className="ml-1">{status.data_ingestion.status}</span>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Total Candles</span>
                  <span className="text-sm text-gray-900">{status.data_ingestion.total_candles.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Active Assets</span>
                  <span className="text-sm text-gray-900">{status.data_ingestion.active_assets} / {status.data_ingestion.total_assets}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Last Update</span>
                  <span className="text-sm text-gray-900">
                    {status.data_ingestion.last_data_update ? 
                      new Date(status.data_ingestion.last_data_update).toLocaleString() : 
                      'Unknown'
                    }
                  </span>
                </div>
              </div>
              <div className="mt-6">
                <button
                  onClick={triggerDataIngestion}
                  className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center justify-center space-x-2"
                >
                  <Database className="h-4 w-4" />
                  <span>Trigger Data Ingestion</span>
                </button>
              </div>
            </div>
          </div>

          {/* Signal Generation Status */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Signal Generation</h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Status</span>
                  <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status.signal_generation.status)}`}>
                    {getStatusIcon(status.signal_generation.status)}
                    <span className="ml-1">{status.signal_generation.status}</span>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Recent Signals</span>
                  <span className="text-sm text-gray-900">{status.signal_generation.recent_signals}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">Signals Today</span>
                  <span className="text-sm text-gray-900">{status.signal_generation.signals_today}</span>
                </div>
                {status.signal_generation.latest_signal && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-600">Latest Signal</span>
                    <span className="text-sm text-gray-900">
                      {status.signal_generation.latest_signal.symbol} - {status.signal_generation.latest_signal.direction}
                    </span>
                  </div>
                )}
              </div>
              <div className="mt-6">
                <button
                  onClick={triggerSignalGeneration}
                  className="w-full bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center justify-center space-x-2"
                >
                  <TrendingUp className="h-4 w-4" />
                  <span>Trigger Signal Generation</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Worker Status */}
        <div className="mt-8 bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Worker Status</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="flex items-center">
                <div className={`p-2 rounded-lg ${status.worker_logs.has_errors ? 'bg-red-100' : 'bg-green-100'}`}>
                  <AlertTriangle className={`h-5 w-5 ${status.worker_logs.has_errors ? 'text-red-600' : 'text-green-600'}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Errors</p>
                  <p className="text-lg font-bold text-gray-900">{status.worker_logs.has_errors ? 'Yes' : 'No'}</p>
                </div>
              </div>

              <div className="flex items-center">
                <div className={`p-2 rounded-lg ${status.worker_logs.has_warnings ? 'bg-yellow-100' : 'bg-green-100'}`}>
                  <AlertTriangle className={`h-5 w-5 ${status.worker_logs.has_warnings ? 'text-yellow-600' : 'text-green-600'}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Warnings</p>
                  <p className="text-lg font-bold text-gray-900">{status.worker_logs.has_warnings ? 'Yes' : 'No'}</p>
                </div>
              </div>

              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Activity className="h-5 w-5 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Last Scan</p>
                  <p className="text-sm text-gray-900">{status.worker_logs.last_scan}</p>
                </div>
              </div>

              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Database className="h-5 w-5 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Last Ingestion</p>
                  <p className="text-sm text-gray-900">{status.worker_logs.last_ingestion}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Last Updated */}
        <div className="mt-8 text-center text-sm text-gray-500">
          Last updated: {new Date(status.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
  );
}





