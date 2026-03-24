/**
 * URL Utilities for Breadcrumb Navigation
 * 
 * Provides utility functions for parsing URL paths and generating
 * human-readable breadcrumb segments for navigation.
 */

/**
 * Transforms a URL segment into a human-readable label
 * @param {string} segment - The URL segment to transform
 * @returns {string} - Human-readable label
 */
export const formatSegmentLabel = (segment) => {
  if (!segment) return '';
  
  // Handle special cases
  const specialCases = {
    'dashboard': 'Dashboard',
    'analytics': 'Analytics',
    'videos': 'Videos',
    'batch': 'Batch Processing',
    'reports': 'Reports',
    'settings': 'Settings',
    'help': 'Help & Support',
    'upload': 'Upload',
    'analysis': 'Analysis',
    'results': 'Results',
    'export': 'Export',
    'profile': 'Profile',
    'admin': 'Administration',
    'users': 'Users',
    'logs': 'Logs',
    'api': 'API',
    'docs': 'Documentation'
  };

  // Check if it's a special case
  if (specialCases[segment.toLowerCase()]) {
    return specialCases[segment.toLowerCase()];
  }

  // Default transformation: capitalize and replace hyphens/underscores
  return segment
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
    .trim();
};

/**
 * Parses a URL path and generates breadcrumb items
 * @param {string} pathname - The current URL pathname
 * @returns {Array} - Array of breadcrumb items with label, path, and isActive properties
 */
export const generateBreadcrumbs = (pathname) => {
  if (!pathname || pathname === '/') {
    return [
      {
        label: 'Home',
        path: '/',
        isActive: true,
        icon: '🏠'
      }
    ];
  }

  // Split path into segments and filter out empty strings
  const segments = pathname.split('/').filter(segment => segment.length > 0);
  
  const breadcrumbs = [
    {
      label: 'Home',
      path: '/',
      isActive: false,
      icon: '🏠'
    }
  ];

  // Build breadcrumb items for each segment
  let currentPath = '';
  
  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    const isLast = index === segments.length - 1;
    
    breadcrumbs.push({
      label: formatSegmentLabel(segment),
      path: currentPath,
      isActive: isLast,
      icon: null
    });
  });

  return breadcrumbs;
};

/**
 * Gets the current pathname from window.location
 * @returns {string} - Current pathname
 */
export const getCurrentPathname = () => {
  if (typeof window !== 'undefined') {
    return window.location.pathname;
  }
  return '/';
};

/**
 * Navigates to a specific path
 * @param {string} path - The path to navigate to
 * @param {Function} navigate - Optional navigation function (e.g., from React Router)
 */
export const navigateToPath = (path, navigate = null) => {
  if (navigate && typeof navigate === 'function') {
    navigate(path);
  } else if (typeof window !== 'undefined') {
    window.location.href = path;
  }
};

/**
 * Checks if a path is the root/home path
 * @param {string} path - The path to check
 * @returns {boolean} - True if path is root
 */
export const isRootPath = (path) => {
  return path === '/' || path === '';
};

/**
 * Gets the parent path of a given path
 * @param {string} path - The current path
 * @returns {string} - The parent path
 */
export const getParentPath = (path) => {
  if (isRootPath(path)) {
    return '/';
  }
  
  const segments = path.split('/').filter(segment => segment.length > 0);
  if (segments.length <= 1) {
    return '/';
  }
  
  return '/' + segments.slice(0, -1).join('/');
};

/**
 * Validates if a path is valid for navigation
 * @param {string} path - The path to validate
 * @returns {boolean} - True if path is valid
 */
export const isValidPath = (path) => {
  if (!path || typeof path !== 'string') {
    return false;
  }
  
  // Basic validation - should start with / and not contain invalid characters
  return /^\/[a-zA-Z0-9\-_\/]*$/.test(path);
};

/**
 * Gets breadcrumb configuration for specific routes
 * @param {string} pathname - The current pathname
 * @returns {Object} - Configuration object with custom labels, icons, etc.
 */
export const getBreadcrumbConfig = (pathname) => {
  const configs = {
    '/dashboard': {
      customLabel: 'Dashboard',
      icon: '📊',
      description: 'Main dashboard overview'
    },
    '/analytics': {
      customLabel: 'Analytics',
      icon: '📈',
      description: 'Data analytics and insights'
    },
    '/videos': {
      customLabel: 'Video Analysis',
      icon: '🎥',
      description: 'Video upload and analysis'
    },
    '/batch': {
      customLabel: 'Batch Processing',
      icon: '⚡',
      description: 'Batch video processing'
    },
    '/reports': {
      customLabel: 'Reports',
      icon: '📋',
      description: 'Analysis reports and exports'
    },
    '/settings': {
      customLabel: 'Settings',
      icon: '⚙️',
      description: 'Application settings'
    },
    '/help': {
      customLabel: 'Help & Support',
      icon: '❓',
      description: 'Help documentation and support'
    }
  };

  return configs[pathname] || null;
};

/**
 * Enhanced breadcrumb generation with custom configurations
 * @param {string} pathname - The current URL pathname
 * @returns {Array} - Array of enhanced breadcrumb items
 */
export const generateEnhancedBreadcrumbs = (pathname) => {
  const basicBreadcrumbs = generateBreadcrumbs(pathname);
  
  return basicBreadcrumbs.map(breadcrumb => {
    const config = getBreadcrumbConfig(breadcrumb.path);
    
    if (config) {
      return {
        ...breadcrumb,
        label: config.customLabel,
        icon: config.icon,
        description: config.description
      };
    }
    
    return breadcrumb;
  });
};
