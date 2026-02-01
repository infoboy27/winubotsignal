'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { auth } from '../lib/auth';
import { Bot, Shield, Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requireAdmin = true }: ProtectedRouteProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = () => {
      const user = auth.getCurrentUser();
      
      if (!user) {
        router.push('/login');
        return;
      }
      
      if (requireAdmin && !auth.isAdmin()) {
        router.push('/login');
        return;
      }
      
      setIsAuthenticated(true);
      setIsLoading(false);
    };

    // Check authentication immediately and then again after a short delay
    checkAuth();
    const timer = setTimeout(checkAuth, 1000);
    return () => clearTimeout(timer);
  }, [router, requireAdmin]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-2xl mb-4 shadow-2xl animate-pulse">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <div className="flex items-center justify-center space-x-2 text-white">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Authenticating...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-500 rounded-2xl mb-4 shadow-2xl">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Access Denied</h2>
          <p className="text-blue-200">You don't have permission to access this page.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}


