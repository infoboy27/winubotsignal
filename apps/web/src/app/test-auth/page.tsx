'use client';

import { useState, useEffect } from 'react';
import { auth } from '../../lib/auth';

export default function TestAuthPage() {
  const [user, setUser] = useState(auth.getCurrentUser());
  const [localStorageData, setLocalStorageData] = useState<string | null>(null);

  useEffect(() => {
    const currentUser = auth.getCurrentUser();
    setUser(currentUser);

    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('winu_user');
      setLocalStorageData(stored);
    }
  }, []);

  const handleRefresh = () => {
    const currentUser = auth.getCurrentUser();
    setUser(currentUser);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Authentication Test Page</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Current User</h2>
          <pre className="bg-gray-100 p-4 rounded">
            {JSON.stringify(user, null, 2)}
          </pre>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">LocalStorage Data</h2>
          <pre className="bg-gray-100 p-4 rounded">
            {localStorageData}
          </pre>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <button
            onClick={handleRefresh}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Refresh User Data
          </button>
        </div>
      </div>
    </div>
  );
}


