'use client';

import { useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

interface ProtectedDashboardProps {
  children: ReactNode;
}

interface AccessCheck {
  access: boolean;
  reason: string;
  tier: string;
  trial_days_remaining?: number;
  dashboard_access_remaining?: number;
  payment_due_date?: string;
  message?: string;
}

export default function ProtectedDashboard({ children }: ProtectedDashboardProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [accessGranted, setAccessGranted] = useState(false);
  const [accessInfo, setAccessInfo] = useState<AccessCheck | null>(null);

  useEffect(() => {
    checkDashboardAccess();
  }, []);

  const checkDashboardAccess = async () => {
    try {
      // Get authentication token
      const token = typeof window !== 'undefined' ? localStorage.getItem('winu_token') : null;
      
      if (!token) {
        console.error('No authentication token found');
        toast.error('Please log in to access the dashboard');
        router.push('/login');
        setLoading(false);
        return;
      }
      
      // First, request dashboard access (this will increment trial access count if applicable)
      const accessResponse = await fetch('/api/subscriptions/dashboard-access', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      const accessResult = await accessResponse.json();

      if (accessResult.success && accessResult.data.access_granted) {
        setAccessGranted(true);
        setAccessInfo(accessResult.data);
        setLoading(false);
      } else {
        // Access denied, show appropriate message and redirect
        setAccessGranted(false);
        setAccessInfo(accessResult.data);
        
        // Show toast message
        toast.error(accessResult.data.message || 'Access denied');
        
        // Redirect based on reason
        if (accessResult.data.reason === 'trial_not_started') {
          router.push('/select-tier');
        } else if (accessResult.data.reason === 'trial_expired' || accessResult.data.reason === 'trial_limit_exceeded') {
          router.push('/select-tier');
        } else if (accessResult.data.reason === 'payment_overdue') {
          router.push('/select-tier');
        } else if (accessResult.data.reason === 'no_subscription') {
          router.push('/select-tier');
        } else {
          router.push('/login');
        }
        
        setLoading(false);
      }
    } catch (error) {
      console.error('Error checking dashboard access:', error);
      toast.error('Failed to verify access');
      router.push('/login');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (!accessGranted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-8 bg-white rounded-lg shadow-lg">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600 mb-6">{accessInfo?.message || 'You do not have access to the dashboard'}</p>
          
          {accessInfo?.trial_days_remaining !== undefined && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-blue-700">
                Trial Days Remaining: <span className="font-semibold">{accessInfo.trial_days_remaining}</span>
              </p>
              <p className="text-sm text-blue-700">
                Dashboard Access Remaining: <span className="font-semibold">{accessInfo.dashboard_access_remaining}</span>
              </p>
            </div>
          )}
          
          <div className="space-y-3">
            <button
              onClick={() => router.push('/select-tier')}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700"
            >
              Select Plan
            </button>
            <button
              onClick={() => router.push('/login')}
              className="w-full bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Trial Access Banner */}
      {accessInfo?.tier === 'free_trial' && (
        <div className="bg-blue-600 text-white py-3 px-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">
                Free Trial Active • {accessInfo.trial_days_remaining} days remaining • {accessInfo.dashboard_access_remaining} dashboard access left
              </span>
            </div>
            <button
              onClick={() => router.push('/select-tier')}
              className="bg-white text-blue-600 px-4 py-1 rounded-full text-sm font-medium hover:bg-blue-50"
            >
              Upgrade Now
            </button>
          </div>
        </div>
      )}
      
      {/* Main Dashboard Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </div>
    </div>
  );
}
