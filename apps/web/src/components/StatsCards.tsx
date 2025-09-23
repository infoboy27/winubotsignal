'use client'

import { TrendingUp, TrendingDown, Target, Award } from 'lucide-react'

interface StatsCardsProps {
  stats: {
    totalSignals: number
    longSignals: number
    shortSignals: number
    avgScore: number
    highConfidenceSignals: number
  }
}

export default function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      title: 'Total Signals',
      value: stats.totalSignals,
      icon: Target,
      color: 'bg-blue-500',
      textColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Long Signals',
      value: stats.longSignals,
      icon: TrendingUp,
      color: 'bg-success-500',
      textColor: 'text-success-600',
      bgColor: 'bg-success-50',
    },
    {
      title: 'Short Signals',
      value: stats.shortSignals,
      icon: TrendingDown,
      color: 'bg-danger-500',
      textColor: 'text-danger-600',
      bgColor: 'bg-danger-50',
    },
    {
      title: 'High Confidence',
      value: stats.highConfidenceSignals,
      icon: Award,
      color: 'bg-purple-500',
      textColor: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card) => (
        <div key={card.title} className="card">
          <div className="flex items-center">
            <div className={`p-3 rounded-lg ${card.bgColor}`}>
              <card.icon className={`h-6 w-6 ${card.textColor}`} />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">{card.title}</p>
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            </div>
          </div>
          
          {card.title === 'High Confidence' && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-sm text-gray-600">
                <span>Avg Score</span>
                <span className="font-medium">{(stats.avgScore * 100).toFixed(1)}%</span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}




