'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Activity, AlertCircle } from 'lucide-react'
import SignalsList from '@/components/SignalsList'
import StatsCards from '@/components/StatsCards'
import RealTimeAlerts from '@/components/RealTimeAlerts'

export default function HomePage() {
  const [stats, setStats] = useState({
    totalSignals: 0,
    longSignals: 0,
    shortSignals: 0,
    avgScore: 0,
    highConfidenceSignals: 0
  })

  useEffect(() => {
    // Fetch initial stats
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/signals/stats/summary')
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Winu Bot Signal</h1>
              <p className="text-gray-600">AI-Powered Crypto Trading Signals</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-sm text-gray-500">
                <Activity className="h-4 w-4 mr-1 text-green-500" />
                Live Market Scanning
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Legal Disclaimer Banner */}
      <div className="bg-amber-50 border-b border-amber-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center py-3">
            <AlertCircle className="h-5 w-5 text-amber-600 mr-2" />
            <p className="text-sm text-amber-800">
              <strong>Legal Disclaimer:</strong> This software is for educational and informational purposes only. 
              The signals and alerts generated do not constitute financial advice. Trading cryptocurrencies involves substantial risk.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <StatsCards stats={stats} />

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          {/* Signals List */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">Recent Signals</h2>
                <div className="flex items-center space-x-2">
                  <div className="flex items-center text-sm text-success-600">
                    <TrendingUp className="h-4 w-4 mr-1" />
                    {stats.longSignals} Long
                  </div>
                  <div className="flex items-center text-sm text-danger-600">
                    <TrendingDown className="h-4 w-4 mr-1" />
                    {stats.shortSignals} Short
                  </div>
                </div>
              </div>
              <SignalsList />
            </div>
          </div>

          {/* Real-time Alerts */}
          <div className="space-y-6">
            <RealTimeAlerts />
            
            {/* Quick Stats */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Average Score</span>
                  <span className="font-medium">{stats.avgScore.toFixed(3)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">High Confidence</span>
                  <span className="font-medium">{stats.highConfidenceSignals}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Total Today</span>
                  <span className="font-medium">{stats.totalSignals}</span>
                </div>
              </div>
            </div>

            {/* Market Status */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Market Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Scanner Status</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Active
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Data Feed</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Connected
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Alerts</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Enabled
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

