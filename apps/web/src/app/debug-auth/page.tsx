'use client';

import { useState, useEffect } from 'react';
import { auth } from '../../lib/auth';

export default function DebugAuthPage() {
  const [user, setUser] = useState(auth.getCurrentUser());
  const [localStorageData, setLocalStorageData] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const currentUser = auth.getCurrentUser();
    setUser(currentUser);
    setIsAuthenticated(auth.isAuthenticated());

    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('winu_user');
      setLocalStorageData(stored);
    }
  }, []);

  const handleRefresh = () => {
    const currentUser = auth.getCurrentUser();
    setUser(currentUser);
    setIsAuthenticated(auth.isAuthenticated());
  };

  const handleLogin = () => {
    const adminUser = {
      id: '1',
      username: 'admin',
      role: 'admin' as const,
      name: 'Winu Bot Admin'
    };
    
    if (typeof window !== 'undefined') {
      localStorage.setItem('winu_user', JSON.stringify(adminUser));
      auth.setCurrentUser(adminUser);
      setUser(adminUser);
      setIsAuthenticated(true);
    }
  };

  const handleLogout = () => {
    auth.logout();
    setUser(null);
    setIsAuthenticated(false);
    setLocalStorageData(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Authentication Debug Page</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Current User</h2>
            <pre className="bg-gray-100 p-4 rounded text-sm">
              {JSON.stringify(user, null, 2)}
            </pre>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">LocalStorage Data</h2>
            <pre className="bg-gray-100 p-4 rounded text-sm">
              {localStorageData || 'No data'}
            </pre>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Authentication Status</h2>
          <div className="space-y-2">
            <p><strong>Is Authenticated:</strong> {isAuthenticated ? 'Yes' : 'No'}</p>
            <p><strong>Is Admin:</strong> {auth.isAdmin() ? 'Yes' : 'No'}</p>
            <p><strong>User Display Name:</strong> {auth.getUserDisplayName()}</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Actions</h2>
          <div className="space-x-4">
            <button
              onClick={handleRefresh}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            >
              Refresh
            </button>
            <button
              onClick={handleLogin}
              className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
            >
              Login as Admin
            </button>
            <button
              onClick={handleLogout}
              className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
