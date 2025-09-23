'use client'

import { useState, useEffect } from 'react'
import { Bell, Wifi, WifiOff } from 'lucide-react'
import { io, Socket } from 'socket.io-client'
import toast from 'react-hot-toast'

interface Alert {
  id: string
  type: string
  data: any
  timestamp: string
}

export default function RealTimeAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [connected, setConnected] = useState(false)
  const [socket, setSocket] = useState<Socket | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.winu.app'
    const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://')
    const socketConnection = io(wsUrl, {
      path: '/ws/alerts',
      transports: ['websocket', 'polling']
    })

    socketConnection.on('connect', () => {
      setConnected(true)
      console.log('Connected to WebSocket')
    })

    socketConnection.on('disconnect', () => {
      setConnected(false)
      console.log('Disconnected from WebSocket')
    })

    socketConnection.on('message', (message) => {
      const alert: Alert = {
        id: Date.now().toString(),
        type: message.type || 'signal',
        data: message.data,
        timestamp: message.timestamp || new Date().toISOString()
      }

      setAlerts(prev => [alert, ...prev.slice(0, 9)]) // Keep last 10 alerts
      
      // Show toast notification
      if (message.type === 'signals') {
        toast.success(`New ${message.data.direction} signal for ${message.data.symbol}`)
      }
    })

    setSocket(socketConnection)

    return () => {
      socketConnection.disconnect()
    }
  }, [])

  const formatAlertMessage = (alert: Alert) => {
    if (alert.type === 'signals') {
      return `${alert.data.symbol} ${alert.data.direction} signal (${alert.data.timeframe}) - Score: ${(alert.data.score * 100).toFixed(0)}%`
    }
    return `${alert.type}: ${JSON.stringify(alert.data)}`
  }

  const getAlertColor = (alert: Alert) => {
    if (alert.type === 'signals') {
      return alert.data.direction === 'LONG' 
        ? 'border-l-success-500 bg-success-50'
        : 'border-l-danger-500 bg-danger-50'
    }
    return 'border-l-blue-500 bg-blue-50'
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Real-time Alerts</h3>
        <div className="flex items-center space-x-2">
          {connected ? (
            <div className="flex items-center text-success-600">
              <Wifi className="h-4 w-4 mr-1" />
              <span className="text-sm">Connected</span>
            </div>
          ) : (
            <div className="flex items-center text-danger-600">
              <WifiOff className="h-4 w-4 mr-1" />
              <span className="text-sm">Disconnected</span>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="text-center py-8">
            <Bell className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No alerts yet</p>
            <p className="text-xs text-gray-400">Real-time alerts will appear here</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`border-l-4 p-3 rounded ${getAlertColor(alert)}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {formatAlertMessage(alert)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(alert.timestamp).toLocaleTimeString()}
                  </p>
                </div>
                <Bell className="h-4 w-4 text-gray-400" />
              </div>
            </div>
          ))
        )}
      </div>

      {!connected && (
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-center">
            <WifiOff className="h-5 w-5 text-amber-600 mr-2" />
            <p className="text-sm text-amber-800">
              Trying to reconnect to real-time feed...
            </p>
          </div>
        </div>
      )}
    </div>
  )
}




