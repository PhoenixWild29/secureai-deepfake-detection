/**
 * useDashboardState Hook
 * Manages dashboard widget configurations, user preferences, and cross-feature data coordination
 * with persistent storage and optimistic updates
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  WidgetConfig, 
  UserPreferences, 
  DashboardState, 
  DashboardStateActions,
  UseDashboardStateReturn,
  DEFAULT_WIDGET_CONFIG,
  DEFAULT_USER_PREFERENCES,
  DASHBOARD_QUERY_KEYS,
  DashboardOptimisticUpdate
} from '@/types/dashboard';
import { getDashboardApiService } from '@/services/dashboardApi';
import { getAuthUtils } from '@/utils/auth';
import { optimisticUpdateUtils, invalidateDashboardQueries } from '@/queryClient';

// Hook configuration
interface UseDashboardStateConfig {
  userId: string;
  enableOptimisticUpdates?: boolean;
  enableAutoSave?: boolean;
  autoSaveDelay?: number;
  enableLocalStorage?: boolean;
  enableServerSync?: boolean;
}

// Default configuration
const DEFAULT_CONFIG: Partial<UseDashboardStateConfig> = {
  enableOptimisticUpdates: true,
  enableAutoSave: true,
  autoSaveDelay: 2000,
  enableLocalStorage: true,
  enableServerSync: true,
};

/**
 * Main dashboard state management hook
 */
export const useDashboardState = (config: UseDashboardStateConfig): UseDashboardStateReturn => {
  const {
    userId,
    enableOptimisticUpdates = true,
    enableAutoSave = true,
    autoSaveDelay = 2000,
    enableLocalStorage = true,
    enableServerSync = true,
  } = { ...DEFAULT_CONFIG, ...config };

  // Services
  const apiService = getDashboardApiService();
  const authUtils = getAuthUtils();
  const queryClient = useQueryClient();

  // State
  const [optimisticUpdates, setOptimisticUpdates] = useState<Map<string, DashboardOptimisticUpdate>>(new Map());
  const [pendingUpdates, setPendingUpdates] = useState<string[]>([]);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Set auth token
  useEffect(() => {
    const token = localStorage.getItem('auth_token'); // In real app, get from auth context
    if (token) {
      apiService.setAuthToken(token);
      authUtils.setUserToken(token, userId);
    }
  }, [userId, apiService, authUtils]);

  // Widgets query
  const {
    data: widgets = [],
    isLoading: widgetsLoading,
    error: widgetsError,
    refetch: refetchWidgets,
  } = useQuery({
    queryKey: DASHBOARD_QUERY_KEYS.widgets(),
    queryFn: () => apiService.getWidgets(userId),
    enabled: enableServerSync,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 30 * 1000, // 30 seconds
    onError: (error) => {
      console.error('Failed to fetch widgets:', error);
    },
  });

  // User preferences query
  const {
    data: preferences = null,
    isLoading: preferencesLoading,
    error: preferencesError,
    refetch: refetchPreferences,
  } = useQuery({
    queryKey: DASHBOARD_QUERY_KEYS.userPreferences(userId),
    queryFn: () => apiService.getUserPreferences(userId),
    enabled: enableServerSync,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes
    onError: (error) => {
      console.error('Failed to fetch preferences:', error);
    },
  });

  // Dashboard state query
  const {
    data: dashboardState = null,
    isLoading: stateLoading,
    error: stateError,
    refetch: refetchState,
  } = useQuery({
    queryKey: DASHBOARD_QUERY_KEYS.all,
    queryFn: () => apiService.loadDashboardState(userId),
    enabled: enableServerSync,
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 2 * 60 * 1000, // 2 minutes
    onError: (error) => {
      console.error('Failed to fetch dashboard state:', error);
    },
  });

  // Widget mutations
  const updateWidgetMutation = useMutation({
    mutationFn: ({ widgetId, updates }: { widgetId: string; updates: Partial<WidgetConfig> }) =>
      apiService.updateWidget(widgetId, updates),
    onSuccess: (data, variables) => {
      // Update cache
      queryClient.setQueryData(
        DASHBOARD_QUERY_KEYS.widget(variables.widgetId),
        data
      );
      invalidateDashboardQueries.widgets();
      
      // Remove from optimistic updates
      setOptimisticUpdates(prev => {
        const newMap = new Map(prev);
        newMap.delete(variables.widgetId);
        return newMap;
      });
    },
    onError: (error, variables) => {
      console.error('Failed to update widget:', error);
      
      // Rollback optimistic update
      const optimisticUpdate = optimisticUpdates.get(variables.widgetId);
      if (optimisticUpdate) {
        queryClient.setQueryData(
          DASHBOARD_QUERY_KEYS.widget(variables.widgetId),
          optimisticUpdate.rollback
        );
        setOptimisticUpdates(prev => {
          const newMap = new Map(prev);
          newMap.delete(variables.widgetId);
          return newMap;
        });
      }
    },
  });

  const addWidgetMutation = useMutation({
    mutationFn: (widget: Omit<WidgetConfig, 'id' | 'createdAt' | 'updatedAt' | 'version'>) =>
      apiService.createWidget(widget),
    onSuccess: (data) => {
      // Update cache
      queryClient.setQueryData(DASHBOARD_QUERY_KEYS.widget(data.id), data);
      invalidateDashboardQueries.widgets();
    },
    onError: (error) => {
      console.error('Failed to add widget:', error);
    },
  });

  const removeWidgetMutation = useMutation({
    mutationFn: (widgetId: string) => apiService.deleteWidget(widgetId),
    onSuccess: (_, widgetId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: DASHBOARD_QUERY_KEYS.widget(widgetId) });
      invalidateDashboardQueries.widgets();
    },
    onError: (error) => {
      console.error('Failed to remove widget:', error);
    },
  });

  // Preferences mutations
  const updatePreferencesMutation = useMutation({
    mutationFn: (updates: Partial<UserPreferences>) =>
      apiService.updateUserPreferences(userId, updates),
    onSuccess: (data) => {
      // Update cache
      queryClient.setQueryData(DASHBOARD_QUERY_KEYS.userPreferences(userId), data);
      invalidateDashboardQueries.preferences();
    },
    onError: (error) => {
      console.error('Failed to update preferences:', error);
    },
  });

  const resetPreferencesMutation = useMutation({
    mutationFn: () => apiService.resetUserPreferences(userId),
    onSuccess: (data) => {
      // Update cache
      queryClient.setQueryData(DASHBOARD_QUERY_KEYS.userPreferences(userId), data);
      invalidateDashboardQueries.preferences();
    },
    onError: (error) => {
      console.error('Failed to reset preferences:', error);
    },
  });

  // State save mutation
  const saveStateMutation = useMutation({
    mutationFn: (state: Partial<DashboardState>) =>
      apiService.saveDashboardState(userId, state),
    onSuccess: () => {
      setLastSaved(new Date());
      setPendingUpdates([]);
    },
    onError: (error) => {
      console.error('Failed to save dashboard state:', error);
    },
  });

  // Auto-save effect
  useEffect(() => {
    if (!enableAutoSave || pendingUpdates.length === 0) {
      return;
    }

    // Clear existing timeout
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    // Set new timeout
    autoSaveTimeoutRef.current = setTimeout(() => {
      const currentState = {
        widgets,
        preferences,
        lastUpdated: new Date(),
      };
      
      saveStateMutation.mutate(currentState);
    }, autoSaveDelay);

    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [pendingUpdates, enableAutoSave, autoSaveDelay, widgets, preferences, saveStateMutation]);

  // Actions
  const updateWidget = useCallback(async (widgetId: string, updates: Partial<WidgetConfig>) => {
    if (enableOptimisticUpdates) {
      // Create optimistic update
      const currentWidget = widgets.find(w => w.id === widgetId);
      if (currentWidget) {
        const optimisticUpdate: DashboardOptimisticUpdate = {
          id: widgetId,
          type: 'update',
          data: { ...currentWidget, ...updates },
          rollback: currentWidget,
          timestamp: new Date(),
          status: 'pending',
        };

        setOptimisticUpdates(prev => new Map(prev).set(widgetId, optimisticUpdate));
        setPendingUpdates(prev => [...prev, widgetId]);

        // Update cache optimistically
        queryClient.setQueryData(
          DASHBOARD_QUERY_KEYS.widget(widgetId),
          optimisticUpdate.data
        );
      }
    }

    // Perform actual update
    updateWidgetMutation.mutate({ widgetId, updates });
  }, [enableOptimisticUpdates, widgets, updateWidgetMutation, queryClient]);

  const addWidget = useCallback(async (widget: Omit<WidgetConfig, 'id' | 'createdAt' | 'updatedAt' | 'version'>) => {
    const widgetWithDefaults = {
      ...DEFAULT_WIDGET_CONFIG,
      ...widget,
    } as Omit<WidgetConfig, 'id' | 'createdAt' | 'updatedAt' | 'version'>;

    if (enableOptimisticUpdates) {
      // Create temporary ID for optimistic update
      const tempId = `temp_${Date.now()}`;
      const optimisticWidget: WidgetConfig = {
        ...widgetWithDefaults,
        id: tempId,
        createdAt: new Date(),
        updatedAt: new Date(),
        version: 1,
      };

      const optimisticUpdate: DashboardOptimisticUpdate = {
        id: tempId,
        type: 'create',
        data: optimisticWidget,
        rollback: null,
        timestamp: new Date(),
        status: 'pending',
      };

      setOptimisticUpdates(prev => new Map(prev).set(tempId, optimisticUpdate));
      setPendingUpdates(prev => [...prev, tempId]);

      // Update cache optimistically
      queryClient.setQueryData(DASHBOARD_QUERY_KEYS.widget(tempId), optimisticWidget);
    }

    // Perform actual creation
    addWidgetMutation.mutate(widgetWithDefaults);
  }, [enableOptimisticUpdates, addWidgetMutation, queryClient]);

  const removeWidget = useCallback(async (widgetId: string) => {
    if (enableOptimisticUpdates) {
      // Create optimistic update
      const currentWidget = widgets.find(w => w.id === widgetId);
      if (currentWidget) {
        const optimisticUpdate: DashboardOptimisticUpdate = {
          id: widgetId,
          type: 'delete',
          data: null,
          rollback: currentWidget,
          timestamp: new Date(),
          status: 'pending',
        };

        setOptimisticUpdates(prev => new Map(prev).set(widgetId, optimisticUpdate));
        setPendingUpdates(prev => [...prev, widgetId]);

        // Remove from cache optimistically
        queryClient.removeQueries({ queryKey: DASHBOARD_QUERY_KEYS.widget(widgetId) });
      }
    }

    // Perform actual deletion
    removeWidgetMutation.mutate(widgetId);
  }, [enableOptimisticUpdates, widgets, removeWidgetMutation, queryClient]);

  const updatePreferences = useCallback(async (updates: Partial<UserPreferences>) => {
    if (enableOptimisticUpdates) {
      // Create optimistic update
      const currentPreferences = preferences || DEFAULT_USER_PREFERENCES as UserPreferences;
      const optimisticPreferences = { ...currentPreferences, ...updates };

      const optimisticUpdate: DashboardOptimisticUpdate = {
        id: 'preferences',
        type: 'update',
        data: optimisticPreferences,
        rollback: currentPreferences,
        timestamp: new Date(),
        status: 'pending',
      };

      setOptimisticUpdates(prev => new Map(prev).set('preferences', optimisticUpdate));
      setPendingUpdates(prev => [...prev, 'preferences']);

      // Update cache optimistically
      queryClient.setQueryData(
        DASHBOARD_QUERY_KEYS.userPreferences(userId),
        optimisticPreferences
      );
    }

    // Perform actual update
    updatePreferencesMutation.mutate(updates);
  }, [enableOptimisticUpdates, preferences, updatePreferencesMutation, queryClient, userId]);

  const resetPreferences = useCallback(async () => {
    resetPreferencesMutation.mutate();
  }, [resetPreferencesMutation]);

  const saveState = useCallback(async () => {
    const currentState = {
      widgets,
      preferences,
      lastUpdated: new Date(),
    };
    
    saveStateMutation.mutate(currentState);
  }, [widgets, preferences, saveStateMutation]);

  const loadState = useCallback(async () => {
    await Promise.all([
      refetchWidgets(),
      refetchPreferences(),
      refetchState(),
    ]);
  }, [refetchWidgets, refetchPreferences, refetchState]);

  const clearState = useCallback(async () => {
    // Clear server state
    await apiService.clearDashboardState(userId);
    
    // Clear local storage
    if (enableLocalStorage) {
      await authUtils.clearUserData();
    }
    
    // Clear cache
    invalidateDashboardQueries.all();
    
    // Clear optimistic updates
    setOptimisticUpdates(new Map());
    setPendingUpdates([]);
  }, [apiService, userId, enableLocalStorage, authUtils]);

  // Local storage sync
  useEffect(() => {
    if (!enableLocalStorage || !authUtils.isAuthenticated()) {
      return;
    }

    const syncToLocalStorage = async () => {
      try {
        if (widgets.length > 0) {
          await authUtils.storeWidgetConfigs(widgets);
        }
        if (preferences) {
          await authUtils.storeUserPreferences(preferences);
        }
      } catch (error) {
        console.error('Failed to sync to local storage:', error);
      }
    };

    syncToLocalStorage();
  }, [widgets, preferences, enableLocalStorage, authUtils]);

  // Load from local storage on mount
  useEffect(() => {
    if (!enableLocalStorage || !authUtils.isAuthenticated()) {
      return;
    }

    const loadFromLocalStorage = async () => {
      try {
        const [localWidgets, localPreferences] = await Promise.all([
          authUtils.getWidgetConfigs(),
          authUtils.getUserPreferences(),
        ]);

        if (localWidgets && localWidgets.length > 0) {
          queryClient.setQueryData(DASHBOARD_QUERY_KEYS.widgets(), localWidgets);
        }
        if (localPreferences) {
          queryClient.setQueryData(DASHBOARD_QUERY_KEYS.userPreferences(userId), localPreferences);
        }
      } catch (error) {
        console.error('Failed to load from local storage:', error);
      }
    };

    loadFromLocalStorage();
  }, [enableLocalStorage, authUtils, queryClient, userId]);

  // Actions object
  const actions: DashboardStateActions = {
    updateWidget,
    addWidget,
    removeWidget,
    updatePreferences,
    resetPreferences,
    saveState,
    loadState,
    clearState,
  };

  // State object
  const state: DashboardState = {
    widgets,
    preferences,
    events: [], // Will be handled by useRealTimeDashboard
    connected: true, // Will be handled by useRealTimeDashboard
    loading: widgetsLoading || preferencesLoading || stateLoading,
    error: widgetsError?.message || preferencesError?.message || stateError?.message || null,
    lastUpdated: lastSaved,
  };

  // Loading states
  const loading = {
    widgets: widgetsLoading,
    preferences: preferencesLoading,
    saving: saveStateMutation.isPending,
  };

  // Error states
  const errors = {
    widgets: widgetsError?.message || null,
    preferences: preferencesError?.message || null,
    general: stateError?.message || null,
  };

  // Optimistic updates
  const optimistic = {
    isUpdating: optimisticUpdates.size > 0,
    pendingUpdates,
  };

  return {
    state,
    actions,
    loading,
    errors,
    optimistic,
  };
};

export default useDashboardState;
