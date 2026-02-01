'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Bot } from 'lucide-react';
import { auth } from '../../lib/auth';

export default function DashboardRootPage() {
  const router = useRouter();

  useEffect(() => {
    // Check if user is authenticated
    const user = auth.getCurrentUser();
    
    if (!user) {
      // Redirect to login if not authenticated
      router.push('/login');
    } else {
      // Redirect to dashboard if authenticated
      router.push('/dashboard');
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900 flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-2xl mb-4 shadow-2xl animate-pulse">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <div className="flex items-center justify-center space-x-2 text-white">
          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span>Loading Winu Bot Dashboard...</span>
        </div>
      </div>
    </div>
  );
}





