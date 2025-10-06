/**
 * Navigation Configuration
 * Centralized configuration for dashboard navigation structure and role-based access
 */

export interface NavigationItemConfig {
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
  /** Navigation path */
  path: string;
  /** Icon name or component */
  icon?: string;
  /** Optional badge text or count */
  badge?: string | number;
  /** Required user roles to access this item */
  requiredRoles?: string[];
  /** Whether this item is disabled */
  disabled?: boolean;
  /** Whether this is an external link */
  external?: boolean;
  /** Description for accessibility */
  description?: string;
  /** Child navigation items */
  children?: NavigationItemConfig[];
  /** Whether children are expanded by default */
  expanded?: boolean;
  /** Order priority for sorting */
  order?: number;
}

export interface NavigationGroupConfig {
  /** Group identifier */
  id: string;
  /** Group title */
  title: string;
  /** Group icon */
  icon?: string;
  /** Whether group is collapsible */
  collapsible?: boolean;
  /** Whether group is expanded by default */
  expanded?: boolean;
  /** Required roles to see this group */
  requiredRoles?: string[];
  /** Navigation items in this group */
  items: NavigationItemConfig[];
  /** Order priority for sorting */
  order?: number;
}

export interface NavigationConfig {
  /** All navigation groups */
  groups: NavigationGroupConfig[];
  /** Default expanded state for collapsible groups */
  defaultExpanded?: boolean;
  /** Whether to show group titles */
  showGroupTitles?: boolean;
}

/**
 * Default navigation configuration
 * Defines the complete navigation structure with role-based access control
 */
export const navigationConfig: NavigationConfig = {
  groups: [
    {
      id: 'main',
      title: 'Main',
      icon: 'home',
      collapsible: false,
      expanded: true,
      order: 1,
      items: [
        {
          id: 'dashboard',
          label: 'Dashboard',
          path: '/dashboard',
          icon: 'home',
          description: 'Main dashboard overview',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 1,
        },
        {
          id: 'analytics',
          label: 'Analytics',
          path: '/dashboard/analytics',
          icon: 'chart-bar',
          description: 'Analytics and insights',
          requiredRoles: ['analyst', 'admin'],
          order: 2,
        },
      ],
    },
    {
      id: 'analysis',
      title: 'Analysis',
      icon: 'magnifying-glass',
      collapsible: true,
      expanded: true,
      order: 2,
      items: [
        {
          id: 'upload',
          label: 'Upload Video',
          path: '/dashboard/upload',
          icon: 'cloud-arrow-up',
          description: 'Upload video for analysis',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 1,
        },
        {
          id: 'batch-analysis',
          label: 'Batch Analysis',
          path: '/dashboard/batch',
          icon: 'layers',
          description: 'Batch video analysis',
          requiredRoles: ['analyst', 'admin'],
          order: 2,
        },
        {
          id: 'analysis-history',
          label: 'Analysis History',
          path: '/dashboard/history',
          icon: 'clock',
          description: 'View analysis history',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 3,
        },
        {
          id: 'analysis-detail',
          label: 'Analysis Detail',
          path: '/dashboard/analysis',
          icon: 'document-magnifying-glass',
          description: 'Detailed analysis monitoring',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 4,
        },
        {
          id: 'progress-tracker',
          label: 'Progress Tracker',
          path: '/dashboard/progress',
          icon: 'chart-bar-square',
          description: 'Real-time analysis progress tracking',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 5,
        },
        {
          id: 'real-time-analysis',
          label: 'Real-time Analysis',
          path: '/dashboard/realtime',
          icon: 'play',
          description: 'Real-time video analysis',
          requiredRoles: ['analyst', 'admin'],
          order: 6,
        },
      ],
    },
    {
      id: 'results',
      title: 'Results',
      icon: 'document-text',
      collapsible: true,
      expanded: true,
      order: 3,
      items: [
        {
          id: 'recent-results',
          label: 'Recent Results',
          path: '/dashboard/results/recent',
          icon: 'clock',
          description: 'Recent analysis results',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 1,
        },
        {
          id: 'export-results',
          label: 'Export Results',
          path: '/dashboard/results/export',
          icon: 'arrow-down-tray',
          description: 'Export analysis results',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 2,
        },
        {
          id: 'reports',
          label: 'Reports',
          path: '/dashboard/reports',
          icon: 'document-chart-bar',
          description: 'Generate and view reports',
          requiredRoles: ['analyst', 'admin'],
          order: 3,
        },
      ],
    },
    {
      id: 'blockchain',
      title: 'Blockchain',
      icon: 'link',
      collapsible: true,
      expanded: false,
      order: 4,
      items: [
        {
          id: 'verification',
          label: 'Verification',
          path: '/dashboard/blockchain/verification',
          icon: 'shield-check',
          description: 'Blockchain verification status',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 1,
        },
        {
          id: 'transactions',
          label: 'Transactions',
          path: '/dashboard/blockchain/transactions',
          icon: 'receipt',
          description: 'Blockchain transaction history',
          requiredRoles: ['analyst', 'admin'],
          order: 2,
        },
        {
          id: 'smart-contracts',
          label: 'Smart Contracts',
          path: '/dashboard/blockchain/contracts',
          icon: 'code-bracket',
          description: 'Smart contract management',
          requiredRoles: ['admin'],
          order: 3,
        },
      ],
    },
    {
      id: 'monitoring',
      title: 'Monitoring',
      icon: 'chart-pie',
      collapsible: true,
      expanded: false,
      order: 5,
      items: [
        {
          id: 'system-health',
          label: 'System Health',
          path: '/dashboard/monitoring/health',
          icon: 'heart',
          description: 'System health monitoring',
          requiredRoles: ['analyst', 'admin'],
          order: 1,
        },
        {
          id: 'performance',
          label: 'Performance',
          path: '/dashboard/monitoring/performance',
          icon: 'chart-bar',
          description: 'Performance metrics',
          requiredRoles: ['analyst', 'admin'],
          order: 2,
        },
        {
          id: 'alerts',
          label: 'Alerts',
          path: '/dashboard/monitoring/alerts',
          icon: 'bell',
          description: 'System alerts and notifications',
          badge: 3,
          requiredRoles: ['analyst', 'admin'],
          order: 3,
        },
      ],
    },
    {
      id: 'settings',
      title: 'Settings',
      icon: 'cog-6-tooth',
      collapsible: true,
      expanded: false,
      order: 6,
      items: [
        {
          id: 'user-preferences',
          label: 'User Preferences',
          path: '/dashboard/settings/preferences',
          icon: 'user',
          description: 'User preferences and settings',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 1,
        },
        {
          id: 'notifications',
          label: 'Notifications',
          path: '/dashboard/settings/notifications',
          icon: 'bell',
          description: 'Notification preferences',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 2,
        },
        {
          id: 'api-keys',
          label: 'API Keys',
          path: '/dashboard/settings/api-keys',
          icon: 'key',
          description: 'API key management',
          requiredRoles: ['analyst', 'admin'],
          order: 3,
        },
        {
          id: 'system-config',
          label: 'System Configuration',
          path: '/dashboard/settings/system',
          icon: 'cog-6-tooth',
          description: 'System configuration',
          requiredRoles: ['admin'],
          order: 4,
        },
        {
          id: 'user-management',
          label: 'User Management',
          path: '/dashboard/settings/users',
          icon: 'users',
          description: 'User account management',
          requiredRoles: ['admin'],
          order: 5,
        },
      ],
    },
    {
      id: 'help',
      title: 'Help & Support',
      icon: 'question-mark-circle',
      collapsible: true,
      expanded: false,
      order: 7,
      items: [
        {
          id: 'documentation',
          label: 'Documentation',
          path: '/dashboard/help/documentation',
          icon: 'book-open',
          description: 'User documentation and guides',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 1,
        },
        {
          id: 'support',
          label: 'Support',
          path: '/dashboard/help/support',
          icon: 'lifebuoy',
          description: 'Contact support team',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 2,
        },
        {
          id: 'feedback',
          label: 'Feedback',
          path: '/dashboard/help/feedback',
          icon: 'chat-bubble-left-right',
          description: 'Submit feedback and suggestions',
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 3,
        },
        {
          id: 'status',
          label: 'System Status',
          path: 'https://status.secureai.com',
          icon: 'signal',
          description: 'System status and uptime',
          external: true,
          requiredRoles: ['user', 'analyst', 'admin'],
          order: 4,
        },
      ],
    },
  ],
  defaultExpanded: true,
  showGroupTitles: true,
};

/**
 * Role hierarchy for permission checking
 */
export const roleHierarchy: Record<string, number> = {
  'user': 1,
  'analyst': 2,
  'admin': 3,
  'super_admin': 4,
};

/**
 * Check if user has required role for navigation item
 */
export const hasRequiredRole = (userRoles: string[], requiredRoles?: string[]): boolean => {
  if (!requiredRoles || requiredRoles.length === 0) {
    return true; // No role requirement
  }

  if (!userRoles || userRoles.length === 0) {
    return false; // No user roles
  }

  // Check if user has any of the required roles
  return requiredRoles.some(role => userRoles.includes(role));
};

/**
 * Filter navigation items based on user roles
 */
export const filterNavigationByRoles = (
  config: NavigationConfig,
  userRoles: string[]
): NavigationConfig => {
  const filteredGroups = config.groups
    .filter(group => hasRequiredRole(userRoles, group.requiredRoles))
    .map(group => ({
      ...group,
      items: group.items.filter(item => hasRequiredRole(userRoles, item.requiredRoles)),
    }))
    .filter(group => group.items.length > 0) // Remove empty groups
    .sort((a, b) => (a.order || 0) - (b.order || 0));

  return {
    ...config,
    groups: filteredGroups,
  };
};

/**
 * Get navigation item by ID
 */
export const getNavigationItemById = (
  config: NavigationConfig,
  itemId: string
): NavigationItemConfig | null => {
  for (const group of config.groups) {
    for (const item of group.items) {
      if (item.id === itemId) {
        return item;
      }
    }
  }
  return null;
};

/**
 * Get navigation path by ID
 */
export const getNavigationPathById = (
  config: NavigationConfig,
  itemId: string
): string | null => {
  const item = getNavigationItemById(config, itemId);
  return item?.path || null;
};

/**
 * Check if navigation item is active based on current path
 */
export const isNavigationItemActive = (
  item: NavigationItemConfig,
  currentPath: string
): boolean => {
  if (item.path === currentPath) {
    return true;
  }

  // Check for nested paths
  if (currentPath.startsWith(item.path + '/')) {
    return true;
  }

  return false;
};

export default navigationConfig;
