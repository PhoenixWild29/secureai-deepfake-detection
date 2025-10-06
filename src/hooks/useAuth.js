/**
 * Authentication Hook
 * Manages authentication state and JWT token handling for the application
 */

import { useState, useEffect, useCallback } from 'react';

/**
 * Custom hook for authentication management
 * @returns {Object} Authentication state and methods
 */
export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Check authentication status on component mount
   */
  useEffect(() => {
    checkAuthStatus();
  }, []);

  /**
   * Check if user is authenticated by verifying session
   */
  const checkAuthStatus = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Check if we have a valid session
      const response = await fetch('/api/auth/status', {
        method: 'GET',
        credentials: 'include', // Include cookies for session-based auth
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.authenticated && data.user) {
          setUser(data.user);
          setIsAuthenticated(true);
          setToken(data.token || null);
        } else {
          setUser(null);
          setIsAuthenticated(false);
          setToken(null);
        }
      } else {
        setUser(null);
        setIsAuthenticated(false);
        setToken(null);
      }
    } catch (error) {
      console.error('Auth status check failed:', error);
      setError('Failed to check authentication status');
      setUser(null);
      setIsAuthenticated(false);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Sign in user with email and password
   * @param {string} email - User email
   * @param {string} password - User password
   * @returns {Promise<Object>} Sign in result
   */
  const signIn = async (email, password) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/login', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Update authentication state
        setUser(data.user || { email });
        setIsAuthenticated(true);
        setToken(data.token || null);
        
        return {
          success: true,
          user: data.user || { email }
        };
      } else {
        const errorMessage = data.error || 'Sign in failed';
        setError(errorMessage);
        return {
          success: false,
          error: errorMessage
        };
      }
    } catch (error) {
      console.error('Sign in error:', error);
      const errorMessage = 'Network error. Please try again.';
      setError(errorMessage);
      return {
        success: false,
        error: errorMessage
      };
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Sign out user
   */
  const signOut = async () => {
    try {
      setIsLoading(true);

      // Call logout endpoint
      await fetch('/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      // Clear authentication state
      setUser(null);
      setIsAuthenticated(false);
      setToken(null);
      setError(null);
    } catch (error) {
      console.error('Sign out error:', error);
      setError('Failed to sign out');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Get current authentication token
   * @returns {string|null} JWT token or null
   */
  const getToken = useCallback(() => {
    return token;
  }, [token]);

  /**
   * Get headers with authentication token
   * @returns {Object} Headers object with authorization
   */
  const getAuthHeaders = useCallback(() => {
    const headers = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }, [token]);

  /**
   * Make authenticated API request
   * @param {string} url - API endpoint URL
   * @param {Object} options - Fetch options
   * @returns {Promise<Response>} Fetch response
   */
  const authenticatedRequest = useCallback(async (url, options = {}) => {
    const headers = {
      ...getAuthHeaders(),
      ...options.headers
    };

    return fetch(url, {
      ...options,
      credentials: 'include',
      headers
    });
  }, [getAuthHeaders]);

  /**
   * Refresh authentication token
   * @returns {Promise<boolean>} True if token was refreshed successfully
   */
  const refreshToken = async () => {
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setToken(data.token);
        return true;
      } else {
        // Token refresh failed, sign out user
        await signOut();
        return false;
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      await signOut();
      return false;
    }
  };

  /**
   * Check if user has specific permission
   * @param {string} permission - Permission to check
   * @returns {boolean} True if user has permission
   */
  const hasPermission = useCallback((permission) => {
    if (!user || !user.permissions) return false;
    return user.permissions.includes(permission);
  }, [user]);

  /**
   * Check if user has specific role
   * @param {string} role - Role to check
   * @returns {boolean} True if user has role
   */
  const hasRole = useCallback((role) => {
    if (!user || !user.roles) return false;
    return user.roles.includes(role);
  }, [user]);

  /**
   * Get user profile information
   * @returns {Object|null} User profile or null
   */
  const getUserProfile = useCallback(() => {
    return user ? {
      id: user.id,
      email: user.email,
      name: user.name,
      roles: user.roles || [],
      permissions: user.permissions || [],
      lastLogin: user.last_login,
      createdAt: user.created_at
    } : null;
  }, [user]);

  /**
   * Update user profile
   * @param {Object} profileData - Profile data to update
   * @returns {Promise<Object>} Update result
   */
  const updateProfile = async (profileData) => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await authenticatedRequest('/api/user/profile', {
        method: 'PUT',
        body: JSON.stringify(profileData)
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setUser(prevUser => ({
          ...prevUser,
          ...data.user
        }));
        return {
          success: true,
          user: data.user
        };
      } else {
        const errorMessage = data.error || 'Profile update failed';
        setError(errorMessage);
        return {
          success: false,
          error: errorMessage
        };
      }
    } catch (error) {
      console.error('Profile update error:', error);
      const errorMessage = 'Network error. Please try again.';
      setError(errorMessage);
      return {
        success: false,
        error: errorMessage
      };
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Clear authentication error
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    token,
    error,

    // Methods
    signIn,
    signOut,
    checkAuthStatus,
    getToken,
    getAuthHeaders,
    authenticatedRequest,
    refreshToken,
    hasPermission,
    hasRole,
    getUserProfile,
    updateProfile,
    clearError
  };
};

/**
 * Higher-order component for protecting routes
 * @param {React.Component} WrappedComponent - Component to protect
 * @param {Object} options - Protection options
 * @returns {React.Component} Protected component
 */
export const withAuth = (WrappedComponent, options = {}) => {
  const { 
    requireAuth = true, 
    requiredRoles = [], 
    requiredPermissions = [],
    redirectTo = '/login'
  } = options;

  return function ProtectedComponent(props) {
    const auth = useAuth();

    // Show loading spinner while checking authentication
    if (auth.isLoading) {
      return (
        <div className="auth-loading">
          <div className="loading-spinner"></div>
          <p>Checking authentication...</p>
        </div>
      );
    }

    // Redirect if authentication is required but user is not authenticated
    if (requireAuth && !auth.isAuthenticated) {
      window.location.href = redirectTo;
      return null;
    }

    // Check role requirements
    if (requiredRoles.length > 0 && !requiredRoles.some(role => auth.hasRole(role))) {
      return (
        <div className="auth-error">
          <h2>Access Denied</h2>
          <p>You don't have the required role to access this page.</p>
        </div>
      );
    }

    // Check permission requirements
    if (requiredPermissions.length > 0 && !requiredPermissions.some(permission => auth.hasPermission(permission))) {
      return (
        <div className="auth-error">
          <h2>Access Denied</h2>
          <p>You don't have the required permissions to access this page.</p>
        </div>
      );
    }

    // Render the protected component
    return <WrappedComponent {...props} auth={auth} />;
  };
};

/**
 * Hook for checking authentication status without managing state
 * @returns {Object} Authentication utilities
 */
export const useAuthCheck = () => {
  const checkAuth = useCallback(async () => {
    try {
      const response = await fetch('/api/auth/status', {
        method: 'GET',
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        return {
          authenticated: data.authenticated,
          user: data.user,
          token: data.token
        };
      } else {
        return {
          authenticated: false,
          user: null,
          token: null
        };
      }
    } catch (error) {
      console.error('Auth check error:', error);
      return {
        authenticated: false,
        user: null,
        token: null,
        error: error.message
      };
    }
  }, []);

  return { checkAuth };
};

/**
 * Utility function to get authentication token from localStorage or session
 * @returns {string|null} JWT token or null
 */
export const getStoredToken = () => {
  try {
    return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
  } catch (error) {
    console.error('Failed to get stored token:', error);
    return null;
  }
};

/**
 * Utility function to store authentication token
 * @param {string} token - JWT token to store
 * @param {boolean} persistent - Whether to store persistently
 */
export const storeToken = (token, persistent = false) => {
  try {
    if (persistent) {
      localStorage.setItem('auth_token', token);
    } else {
      sessionStorage.setItem('auth_token', token);
    }
  } catch (error) {
    console.error('Failed to store token:', error);
  }
};

/**
 * Utility function to remove stored authentication token
 */
export const removeStoredToken = () => {
  try {
    localStorage.removeItem('auth_token');
    sessionStorage.removeItem('auth_token');
  } catch (error) {
    console.error('Failed to remove stored token:', error);
  }
};
