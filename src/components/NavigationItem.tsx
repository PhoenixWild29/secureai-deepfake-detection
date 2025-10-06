import React from 'react';
import { ChevronRightIcon, ChevronDownIcon } from '@heroicons/react/24/outline';

export interface NavigationItemProps {
  /** Unique identifier for the navigation item */
  id: string;
  /** Display label for the navigation item */
  label: string;
  /** Navigation path/URL */
  path: string;
  /** Icon component or icon name */
  icon?: React.ComponentType<{ className?: string }> | string;
  /** Optional badge text or count */
  badge?: string | number;
  /** Whether this item is currently active */
  isActive?: boolean;
  /** Whether this item has children (for expandable sections) */
  hasChildren?: boolean;
  /** Whether children are expanded */
  isExpanded?: boolean;
  /** Callback when item is clicked */
  onClick?: () => void;
  /** Callback when item is expanded/collapsed */
  onToggle?: () => void;
  /** Required user roles to see this item */
  requiredRoles?: string[];
  /** Whether the item is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Whether this is an external link */
  external?: boolean;
  /** Description for accessibility */
  description?: string;
}

/**
 * NavigationItem component for individual navigation links
 * Implements WCAG 2.2 AA accessibility standards
 */
export const NavigationItem: React.FC<NavigationItemProps> = ({
  id,
  label,
  path,
  icon: Icon,
  badge,
  isActive = false,
  hasChildren = false,
  isExpanded = false,
  onClick,
  onToggle,
  disabled = false,
  className = '',
  external = false,
  description,
}) => {
  const handleClick = () => {
    if (disabled) return;
    
    if (hasChildren && onToggle) {
      onToggle();
    } else if (onClick) {
      onClick();
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (disabled) return;

    switch (event.key) {
      case 'Enter':
      case ' ':
        event.preventDefault();
        handleClick();
        break;
      case 'ArrowRight':
        if (hasChildren && !isExpanded) {
          event.preventDefault();
          onToggle?.();
        }
        break;
      case 'ArrowLeft':
        if (hasChildren && isExpanded) {
          event.preventDefault();
          onToggle?.();
        }
        break;
    }
  };

  const baseClasses = `
    group flex items-center justify-between w-full px-3 py-2 text-sm font-medium rounded-md
    transition-all duration-200 ease-in-out
    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
    ${disabled 
      ? 'text-gray-400 cursor-not-allowed' 
      : isActive 
        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200' 
        : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
    }
  `;

  const iconClasses = `
    flex-shrink-0 w-5 h-5 mr-3
    ${disabled 
      ? 'text-gray-400' 
      : isActive 
        ? 'text-blue-600 dark:text-blue-400' 
        : 'text-gray-500 group-hover:text-gray-700 dark:text-gray-400 dark:group-hover:text-gray-200'
    }
  `;

  const labelClasses = `
    flex-1 text-left truncate
    ${disabled ? 'text-gray-400' : ''}
  `;

  const badgeClasses = `
    inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
    ${isActive 
      ? 'bg-blue-200 text-blue-800 dark:bg-blue-800 dark:text-blue-200' 
      : 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  `;

  const chevronClasses = `
    flex-shrink-0 w-4 h-4 ml-2 transition-transform duration-200
    ${disabled ? 'text-gray-400' : 'text-gray-500 group-hover:text-gray-700 dark:text-gray-400 dark:group-hover:text-gray-200'}
    ${isExpanded ? 'rotate-90' : ''}
  `;

  return (
    <div className={`navigation-item ${className}`}>
      <button
        id={`nav-item-${id}`}
        className={baseClasses}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-current={isActive ? 'page' : undefined}
        aria-expanded={hasChildren ? isExpanded : undefined}
        aria-describedby={description ? `nav-item-${id}-desc` : undefined}
        role={hasChildren ? 'button' : 'menuitem'}
        tabIndex={disabled ? -1 : 0}
      >
        <div className="flex items-center min-w-0 flex-1">
          {/* Icon */}
          {Icon && (
            <div className={iconClasses}>
              {typeof Icon === 'string' ? (
                <span className="text-lg" aria-hidden="true">
                  {Icon}
                </span>
              ) : (
                <Icon className="w-5 h-5" aria-hidden="true" />
              )}
            </div>
          )}

          {/* Label */}
          <span className={labelClasses}>
            {label}
          </span>

          {/* Badge */}
          {badge !== undefined && badge !== null && (
            <span className={badgeClasses} aria-label={`${badge} notifications`}>
              {badge}
            </span>
          )}

          {/* External link indicator */}
          {external && (
            <span className="ml-2 text-xs text-gray-400" aria-label="External link">
              ↗
            </span>
          )}
        </div>

        {/* Expand/Collapse chevron */}
        {hasChildren && (
          <div className="flex items-center">
            {isExpanded ? (
              <ChevronDownIcon className={chevronClasses} aria-hidden="true" />
            ) : (
              <ChevronRightIcon className={chevronClasses} aria-hidden="true" />
            )}
          </div>
        )}
      </button>

      {/* Description for screen readers */}
      {description && (
        <div
          id={`nav-item-${id}-desc`}
          className="sr-only"
          aria-live="polite"
        >
          {description}
        </div>
      )}
    </div>
  );
};

/**
 * NavigationItemGroup component for grouping related navigation items
 */
export interface NavigationItemGroupProps {
  /** Group title */
  title: string;
  /** Child navigation items */
  children: React.ReactNode;
  /** Whether the group is collapsible */
  collapsible?: boolean;
  /** Whether the group is expanded */
  expanded?: boolean;
  /** Callback when group is toggled */
  onToggle?: () => void;
  /** Additional CSS classes */
  className?: string;
}

export const NavigationItemGroup: React.FC<NavigationItemGroupProps> = ({
  title,
  children,
  collapsible = false,
  expanded = true,
  onToggle,
  className = '',
}) => {
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (!collapsible) return;

    switch (event.key) {
      case 'Enter':
      case ' ':
        event.preventDefault();
        onToggle?.();
        break;
    }
  };

  return (
    <div className={`navigation-item-group ${className}`}>
      {collapsible ? (
        <button
          className="w-full px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md transition-colors duration-200"
          onClick={onToggle}
          onKeyDown={handleKeyDown}
          aria-expanded={expanded}
          aria-controls={`nav-group-${title.toLowerCase().replace(/\s+/g, '-')}`}
        >
          <div className="flex items-center justify-between">
            <span>{title}</span>
            <ChevronDownIcon 
              className={`w-4 h-4 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} 
              aria-hidden="true" 
            />
          </div>
        </button>
      ) : (
        <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">
          {title}
        </div>
      )}
      
      {expanded && (
        <div 
          id={`nav-group-${title.toLowerCase().replace(/\s+/g, '-')}`}
          className="mt-1 space-y-1"
          role="group"
          aria-labelledby={collapsible ? undefined : `nav-group-title-${title.toLowerCase().replace(/\s+/g, '-')}`}
        >
          {children}
        </div>
      )}
    </div>
  );
};

export default NavigationItem;
