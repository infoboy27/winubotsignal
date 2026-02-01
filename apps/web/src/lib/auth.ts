/**
 * Authentication utilities for Winu Bot Dashboard
 */

export interface User {
  id: string;
  username: string;
  role: 'admin' | 'viewer';
  name: string;
  token?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

// Simple in-memory session storage (in production, use proper session management)
let currentUser: User | null = null;
let isGettingUser = false; // Prevent infinite loops

export const auth = {
  /**
   * Authenticate user with username and password
   * This now delegates to the backend API for proper authentication
   */
  async login(credentials: LoginCredentials): Promise<{ success: boolean; user?: User; error?: string }> {
    try {
      // Use Next.js API proxy for authentication (handles CORS and routing)
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: credentials.username,
          password: credentials.password,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        currentUser = {
          id: data.user?.id || '1',
          username: credentials.username,
          role: data.user?.is_admin ? 'admin' : 'viewer',
          name: data.user?.username || credentials.username,
          token: data.access_token,
        };
        
        // Store in localStorage for persistence (consider httpOnly cookies for production)
        if (typeof window !== 'undefined') {
          localStorage.setItem('winu_user', JSON.stringify(currentUser));
          localStorage.setItem('winu_token', data.access_token);
        }
        
        return { success: true, user: currentUser };
      }
      
      return { 
        success: false, 
        error: 'Invalid username or password' 
      };
    } catch (error) {
      // Log error in production for monitoring
      if (process.env.NODE_ENV === 'production' && typeof window !== 'undefined') {
        // Send to monitoring service in production
      }
      return { 
        success: false, 
        error: 'Authentication service unavailable. Please try again later.' 
      };
    }
  },

  /**
   * Get current authenticated user
   */
  getCurrentUser(): User | null {
    // Prevent infinite loops
    if (isGettingUser) {
      return currentUser;
    }
    
    isGettingUser = true;
    
    try {
      // Return cached user if available
      if (currentUser) {
        return currentUser;
      }
      
      // Try to get from localStorage
      if (typeof window !== 'undefined') {
        try {
          const stored = localStorage.getItem('winu_user');
          if (stored) {
            const parsedUser = JSON.parse(stored);
            currentUser = parsedUser;
            return currentUser;
          }
        } catch (error) {
          // Clear corrupted data
          localStorage.removeItem('winu_user');
        }
      }
      
      return null;
    } finally {
      isGettingUser = false;
    }
  },

  /**
   * Set current user (for login)
   */
  setCurrentUser(user: User): void {
    currentUser = user;
    if (typeof window !== 'undefined') {
      localStorage.setItem('winu_user', JSON.stringify(user));
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.getCurrentUser() !== null;
  },

  /**
   * Check if user is admin
   */
  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.role === 'admin';
  },

  /**
   * Logout current user
   */
  logout(): void {
    currentUser = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('winu_user');
      localStorage.removeItem('winu_token');
    }
  },

  /**
   * Get user display name
   */
  getUserDisplayName(): string {
    const user = this.getCurrentUser();
    return user?.name || 'Unknown User';
  }
};


