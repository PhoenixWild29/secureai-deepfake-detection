import React, { useState, useEffect, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';
import { useAuth } from '@/contexts/AuthContext';
import { NavigationItem, NavigationItemGroup } from './NavigationItem';
import { navigationConfig, filterNavigationByRoles, isNavigationItemActive } from '@/data/navigationConfig';

export interface DashboardNavigationProps {
  /** Whether the navigation is collapsed */
  collapsed?: boolean;
  /** Callback when collapse state changes */
  onCollapseChange?: (collapsed: boolean) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the mobile menu toggle */
  showMobileToggle?: boolean;
  /** Whether the mobile menu is open */
  mobileOpen?: boolean;
  /** Callback when mobile menu state changes */
  onMobileChange?: (open: boolean) => void;
}

/**
 * DashboardNavigation component
 * Main sidebar navigation with role-based filtering and collapsible functionality
 */
export const DashboardNavigation: React.FC<DashboardNavigationProps> = ({
  collapsed = false,
  onCollapseChange,
  className = '',
  showMobileToggle = true,
  mobileOpen = false,
  onMobileChange,
}) => {
  const { user, hasRole, theme } = useAuth();
  const pathname = usePathname();
  
  const [internalCollapsed, setInternalCollapsed] = useState(collapsed);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Sync internal state with props
  useEffect(() => {
    setInternalCollapsed(collapsed);
  }, [collapsed]);

  // Initialize expanded groups based on config
  useEffect(() => {
    const initialExpanded = new Set(
      navigationConfig.groups
        .filter(group => group.expanded !== false)
        .map(group => group.id)
    );
    setExpandedGroups(initialExpanded);
  }, []);

  // Filter navigation based on user roles
  const filteredConfig = React.useMemo(() => {
    if (!user?.roles) {
      return { groups: [] };
    }
    return filterNavigationByRoles(navigationConfig, user.roles);
  }, [user?.roles]);

  const handleCollapseToggle = useCallback(() => {
    const newCollapsed = !internalCollapsed;
    setInternalCollapsed(newCollapsed);
    onCollapseChange?.(newCollapsed);
  }, [internalCollapsed, onCollapseChange]);

  const handleGroupToggle = useCallback((groupId: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  }, []);

  const handleItemToggle = useCallback((itemId: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  }, []);

  const handleItemClick = useCallback((path: string, external?: boolean) => {
    if (external) {
      window.open(path, '_blank', 'noopener,noreferrer');
    } else {
      // TODO: Implement navigation using Next.js router
      console.log('Navigate to:', path);
    }
  }, []);

  const sidebarClasses = `
    fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700
    transform transition-transform duration-300 ease-in-out
    ${internalCollapsed ? '-translate-x-full lg:translate-x-0 lg:w-16' : 'translate-x-0'}
    ${mobileOpen ? 'translate-x-0' : 'lg:translate-x-0'}
    ${className}
  `;

  const overlayClasses = `
    fixed inset-0 z-40 bg-gray-600 bg-opacity-75 transition-opacity duration-300 ease-in-out
    ${mobileOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}
    lg:hidden
  `;

  return (
    <>
      {/* Mobile overlay */}
      {showMobileToggle && (
        <div
          className={overlayClasses}
          onClick={() => onMobileChange?.(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <div className={sidebarClasses}>
        {/* Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
          {!internalCollapsed && (
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">SA</span>
                </div>
              </div>
              <div className="ml-3">
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                  SecureAI
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  DeepFake Detection
                </p>
              </div>
            </div>
          )}

          {/* Collapse toggle */}
          <button
            onClick={handleCollapseToggle}
            className="p-2 rounded-md text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:text-gray-300 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label={internalCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={internalCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {internalCollapsed ? (
              <Bars3Icon className="w-5 h-5" />
            ) : (
              <XMarkIcon className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-4" role="navigation" aria-label="Main navigation">
          <div className="px-3 space-y-1">
            {filteredConfig.groups.map((group) => (
              <NavigationItemGroup
                key={group.id}
                title={group.title}
                collapsible={group.collapsible}
                expanded={expandedGroups.has(group.id)}
                onToggle={() => handleGroupToggle(group.id)}
                className={internalCollapsed ? 'hidden' : ''}
              >
                {group.items.map((item) => (
                  <NavigationItem
                    key={item.id}
                    id={item.id}
                    label={item.label}
                    path={item.path}
                    icon={item.icon}
                    badge={item.badge}
                    isActive={isNavigationItemActive(item, pathname)}
                    disabled={item.disabled}
                    external={item.external}
                    description={item.description}
                    onClick={() => handleItemClick(item.path, item.external)}
                    className="mb-1"
                  />
                ))}
              </NavigationItemGroup>
            ))}

            {/* Collapsed state - show only icons */}
            {internalCollapsed && (
              <div className="space-y-1">
                {filteredConfig.groups.map((group) =>
                  group.items.map((item) => (
                    <NavigationItem
                      key={item.id}
                      id={item.id}
                      label={item.label}
                      path={item.path}
                      icon={item.icon}
                      badge={item.badge}
                      isActive={isNavigationItemActive(item, pathname)}
                      disabled={item.disabled}
                      external={item.external}
                      description={item.description}
                      onClick={() => handleItemClick(item.path, item.external)}
                      className="mb-1"
                    />
                  ))
                )}
              </div>
            )}
          </div>
        </nav>

        {/* Footer */}
        {!internalCollapsed && (
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                {user?.avatar ? (
                  <img
                    className="w-8 h-8 rounded-full"
                    src={user.avatar}
                    alt={user.name}
                  />
                ) : (
                  <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      {user?.name?.charAt(0) || 'U'}
                    </span>
                  </div>
                )}
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {user?.name || 'Guest'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {user?.roles?.[0] || 'User'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mobile menu button */}
      {showMobileToggle && (
        <button
          className="fixed top-4 left-4 z-50 p-2 rounded-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 lg:hidden"
          onClick={() => onMobileChange?.(!mobileOpen)}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileOpen}
        >
          <Bars3Icon className="w-6 h-6" />
        </button>
      )}
    </>
  );
};

/**
 * Hook to use dashboard navigation state
 */
export const useDashboardNavigation = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => !prev);
  }, []);

  const toggleMobile = useCallback(() => {
    setMobileOpen(prev => !prev);
  }, []);

  return {
    collapsed,
    mobileOpen,
    toggleCollapsed,
    toggleMobile,
    setCollapsed,
    setMobileOpen,
  };
};

export default DashboardNavigation;