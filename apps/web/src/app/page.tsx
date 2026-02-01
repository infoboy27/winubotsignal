'use client';

import { useEffect, useState } from 'react';
import LandingPage from './landing/page';
import { auth } from '../lib/auth';

export default function HomePage() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(auth.getCurrentUser());

  useEffect(() => {
    const hostname = window.location.hostname;
    
    // Check authentication status
    const currentUser = auth.getCurrentUser();
    setUser(currentUser);
    
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Always show landing page on main domain
  // Dashboard access is handled by specific routes
  return <LandingPage />;
}
