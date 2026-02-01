'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Bot, Shield, Zap } from 'lucide-react';

export default function LoginPage() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Use the auth library for login (which calls the backend API)
      const { auth } = await import('../../lib/auth');
      const result = await auth.login(credentials);

      if (result.success && result.user) {
        // Check subscription status and redirect accordingly
        try {
          // Get the auth token that was just set
          const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
          
          const subscriptionResponse = await fetch('/api/subscriptions/info', {
            headers: token ? {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`,
            } : {
              'Content-Type': 'application/json',
            }
          });
          
          if (subscriptionResponse.ok) {
            const subscriptionData = await subscriptionResponse.json();
            
            // If user has an active trial or paid subscription, redirect to dashboard
            if (subscriptionData.subscription_status === 'trial' || 
                subscriptionData.subscription_status === 'active' ||
                (subscriptionData.subscription_tier && subscriptionData.subscription_tier !== 'free')) {
              router.push('/dashboard');
            } else {
              // User needs to select a subscription tier
              router.push('/select-tier');
            }
          } else {
            // If we can't check subscription, redirect to dashboard
            router.push('/dashboard');
          }
        } catch (subscriptionError) {
          // If there's an error checking subscription, redirect to dashboard
          router.push('/dashboard');
        }
      } else {
        setError(result.error || 'Invalid username or password');
      }
    } catch (err) {
      // Error already logged in auth library
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/20 to-cyan-900/20"></div>
      
      <div className="relative z-10 w-full max-w-md">
        {/* Logo and Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-2xl mb-4 shadow-2xl">
            <Bot className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">Winu Bot</h1>
          <p className="text-blue-200 text-lg">Trading Signal Dashboard</p>
          <div className="flex items-center justify-center space-x-4 mt-4 text-blue-300">
            <div className="flex items-center space-x-1">
              <Shield className="w-4 h-4" />
              <span className="text-sm">Secure</span>
            </div>
            <div className="flex items-center space-x-1">
              <Zap className="w-4 h-4" />
              <span className="text-sm">Real-time</span>
            </div>
          </div>
        </div>

        {/* Login Form */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white mb-2">Admin Access</h2>
            <p className="text-blue-200">Sign in to access the trading dashboard</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 text-red-200 text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-blue-200 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={credentials.username}
                onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent"
                placeholder="Enter your username"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-blue-200 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-blue-300 focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:border-transparent pr-12"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-blue-300 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg"
            >
              {loading ? (
                <div className="flex items-center justify-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Signing in...</span>
                </div>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Contact admin for access */}
          <div className="mt-6 text-center">
            <p className="text-blue-200 text-sm">
              Need access? Contact your administrator.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-blue-300 text-sm">
          <p>© 2024 Winu Bot Signal. All rights reserved.</p>
          <p className="mt-1">Powered by AI Trading Technology</p>
        </div>
      </div>
    </div>
  );
}


