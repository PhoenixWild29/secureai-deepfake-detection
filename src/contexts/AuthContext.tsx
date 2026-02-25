import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface User {
  /** Unique user identifier */
  id: string;
  /** User email address */
  email: string;
  /** User display name */
  name: string;
  /** User avatar URL */
  avatar?: string;
  /** User roles */
  roles: string[];
  /** User permissions */
  permissions?: string[];
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** Last login timestamp */
  lastLogin?: Date;
  /** User preferences */
  preferences?: UserPreferences;
}

export interface UserPreferences {
  /** Theme preference */
  theme: 'light' | 'dark' | 'system';
  /** Language preference */
  language: string;
  /** Timezone */
  timezone: string;
  /** Navigation preferences */
  navigation: {
    sidebarCollapsed: boolean;
    sidebarWidth: number;
    showBreadcrumbs: boolean;
    showPageTitles: boolean;
  };
  /** Notification preferences */
  notifications: {
    email: boolean;
    inApp: boolean;
    push: boolean;
  };
}

export interface AuthContextType {
  /** Current user */
  user: User | null;
  /** Whether user is loading */
  isLoading: boolean;
  /** Authentication error */
  error: string | null;
  /** Login function */
  login: (email: string, password: string) => Promise<void>;
  /** Logout function */
  logout: () => Promise<void>;
  /** Update user preferences */
  updatePreferences: (preferences: Partial<UserPreferences>) => Promise<void>;
  /** Refresh user data */
  refreshUser: () => Promise<void>;
  /** Check if user has specific role */
  hasRole: (role: string) => boolean;
  /** Check if user has specific permission */
  hasPermission: (permission: string) => boolean;
  /** Current theme */
  theme: 'light' | 'dark';
  /** Toggle theme */
  toggleTheme: () => void;
  /** Set theme */
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export interface AuthProviderProps {
  children: ReactNode;
  /** Initial user data (for SSR or testing) */
  initialUser?: User | null;
}

/**
 * AuthProvider component that provides authentication context
 * Manages user state, authentication, and theme settings
 */
export const AuthProvider: React.FC<AuthProviderProps> = ({
  children,
  initialUser = null,
}) => {
  const [user, setUser] = useState<User | null>(initialUser);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [theme, setThemeState] = useState<'light' | 'dark'>('light');

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | 'system' | null;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    
    if (savedTheme === 'system' || !savedTheme) {
      setThemeState(systemTheme);
    } else {
      setThemeState(savedTheme);
    }
  }, []);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme === 'system' || !savedTheme) {
        setThemeState(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
  }, [theme]);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual authentication API call
      // This is a mock implementation
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock user data based on email
      const mockUser: User = {
        id: 'user-123',
        email,
        name: email.split('@')[0],
        avatar: `https://ui-avatars.com/api/?name=${email.split('@')[0]}&background=random`,
        roles: email.includes('admin') ? ['admin'] : email.includes('analyst') ? ['analyst'] : ['user'],
        permissions: [],
        isAuthenticated: true,
        lastLogin: new Date(),
        preferences: {
          theme: 'system',
          language: 'en-US',
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          navigation: {
            sidebarCollapsed: false,
            sidebarWidth: 256,
            showBreadcrumbs: true,
            showPageTitles: true,
          },
          notifications: {
            email: true,
            inApp: true,
            push: false,
          },
        },
      };

      setUser(mockUser);
      localStorage.setItem('user', JSON.stringify(mockUser));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual logout API call
      await new Promise(resolve => setTimeout(resolve, 500));

      setUser(null);
      localStorage.removeItem('user');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Logout failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const updatePreferences = async (preferences: Partial<UserPreferences>): Promise<void> => {
    if (!user) return;

    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 500));

      const updatedUser = {
        ...user,
        preferences: {
          ...user.preferences,
          ...preferences,
        },
      };

      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update preferences');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async (): Promise<void> => {
    if (!user) return;

    setIsLoading(true);
    setError(null);

    try {
      // TODO: Replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 500));

      // In a real implementation, this would fetch fresh user data from the API
      const savedUser = localStorage.getItem('user');
      if (savedUser) {
        setUser(JSON.parse(savedUser));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh user data');
    } finally {
      setIsLoading(false);
    }
  };

  const hasRole = (role: string): boolean => {
    return user?.roles.includes(role) ?? false;
  };

  const hasPermission = (permission: string): boolean => {
    return user?.permissions?.includes(permission) ?? false;
  };

  const toggleTheme = (): void => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const setTheme = (newTheme: 'light' | 'dark' | 'system'): void => {
    localStorage.setItem('theme', newTheme);
    
    if (newTheme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      setThemeState(systemTheme);
    } else {
      setThemeState(newTheme);
    }
  };

  // Initialize user from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser && !user) {
      try {
        const parsedUser = JSON.parse(savedUser);
        setUser(parsedUser);
      } catch (err) {
        console.error('Failed to parse saved user data:', err);
        localStorage.removeItem('user');
      }
    }
  }, [user]);

  const value: AuthContextType = {
    user,
    isLoading,
    error,
    login,
    logout,
    updatePreferences,
    refreshUser,
    hasRole,
    hasPermission,
    theme,
    toggleTheme,
    setTheme,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * Hook to use authentication context
 * @throws Error if used outside of AuthProvider
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

/**
 * Hook to get current user
 * @returns Current user or null if not authenticated
 */
export const useUser = (): User | null => {
  const { user } = useAuth();
  return user;
};

/**
 * Hook to check if user has specific role
 * @param role Role to check
 * @returns True if user has the role
 */
export const useHasRole = (role: string): boolean => {
  const { hasRole } = useAuth();
  return hasRole(role);
};

/**
 * Hook to check if user has specific permission
 * @param permission Permission to check
 * @returns True if user has the permission
 */
export const useHasPermission = (permission: string): boolean => {
  const { hasPermission } = useAuth();
  return hasPermission(permission);
};

/**
 * Hook to get current theme
 * @returns Current theme
 */
export const useTheme = (): 'light' | 'dark' => {
  const { theme } = useAuth();
  return theme;
};

export default AuthContext;
