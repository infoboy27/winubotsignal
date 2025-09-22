'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Clock, Target } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface Signal {
  id: number
  symbol: string
  direction: 'LONG' | 'SHORT'
  timeframe: string
  score: number
  entry_price: string
  stop_loss: string
  take_profit_1: string
  risk_reward_ratio: number
  created_at: string
  confluences: {
    trend: boolean
    smooth_trail: boolean
    liquidity: boolean
    smart_money: boolean
    volume: boolean
  }
}

export default function SignalsList() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSignals()
    
    // Refresh signals every 30 seconds
    const interval = setInterval(fetchSignals, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchSignals = async () => {
    try {
      const response = await fetch('/api/signals/recent?limit=20')
      if (response.ok) {
        const data = await response.json()
        setSignals(data)
      }
    } catch (error) {
      console.error('Failed to fetch signals:', error)
    } finally {
      setLoading(false)
    }
  }

  const getSignalBadgeColor = (direction: string) => {
    return direction === 'LONG' 
      ? 'bg-success-100 text-success-800 border-success-200'
      : 'bg-danger-100 text-danger-800 border-danger-200'
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.65) return 'text-yellow-600'
    return 'text-gray-600'
  }

  const getConfluenceCount = (confluences: any) => {
    if (!confluences) return 0
    return Object.values(confluences).filter(Boolean).length
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-gray-200 rounded-lg h-20"></div>
          </div>
        ))}
      </div>
    )
  }

  if (signals.length === 0) {
    return (
      <div className="text-center py-12">
        <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No signals yet</h3>
        <p className="text-gray-500">Signals will appear here when market conditions are favorable.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {signals.map((signal) => (
        <div key={signal.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-4">
              {/* Direction Icon */}
              <div className={`p-2 rounded-lg ${getSignalBadgeColor(signal.direction)}`}>
                {signal.direction === 'LONG' ? (
                  <TrendingUp className="h-5 w-5" />
                ) : (
                  <TrendingDown className="h-5 w-5" />
                )}
              </div>

              {/* Signal Details */}
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{signal.symbol}</h3>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getSignalBadgeColor(signal.direction)}`}>
                    {signal.direction}
                  </span>
                  <span className="text-sm text-gray-500">{signal.timeframe}</span>
                </div>

                {/* Price Levels */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                  <div>
                    <span className="text-gray-500">Entry:</span>
                    <span className="ml-1 font-medium">${parseFloat(signal.entry_price).toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Stop Loss:</span>
                    <span className="ml-1 font-medium">${parseFloat(signal.stop_loss).toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Take Profit:</span>
                    <span className="ml-1 font-medium">${parseFloat(signal.take_profit_1).toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">R:R:</span>
                    <span className="ml-1 font-medium">{signal.risk_reward_ratio.toFixed(1)}</span>
                  </div>
                </div>

                {/* Confluences */}
                <div className="flex items-center space-x-2 mb-2">
                  <span className="text-sm text-gray-500">Confluences:</span>
                  <span className="text-sm font-medium">{getConfluenceCount(signal.confluences)}/5</span>
                  <div className="flex space-x-1">
                    {signal.confluences?.trend && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        Trend
                      </span>
                    )}
                    {signal.confluences?.smart_money && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                        Smart Money
                      </span>
                    )}
                    {signal.confluences?.liquidity && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
                        Liquidity
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Score and Time */}
            <div className="text-right">
              <div className={`text-2xl font-bold ${getScoreColor(signal.score)}`}>
                {(signal.score * 100).toFixed(0)}%
              </div>
              <div className="flex items-center text-sm text-gray-500 mt-1">
                <Clock className="h-4 w-4 mr-1" />
                {formatDistanceToNow(new Date(signal.created_at), { addSuffix: true })}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

