import React, { useState, useEffect } from 'react';
import { generateEnhancedBreadcrumbs, navigateToPath, getCurrentPathname } from '../utils/urlUtils';
import { useNavigation } from '../hooks/useNavigation';

/**
 * BreadcrumbNavigation Component
 * 
 * A contextual breadcrumb navigation component that shows users their current
 * location within the dashboard hierarchy and provides quick navigation to
 * parent sections.
 * 
 * Features:
 * - Horizontal breadcrumb trail with Home icon and chevron separators
 * - Automatic URL parsing with human-readable labels
 * - Clickable navigation for non-active items
 * - Accessibility compliance with ARIA labels and semantic markup
 * - Consistent styling with text-sm, muted colors, and hover effects
 * - Smooth transitions for interactive states
 */

const BreadcrumbNavigation = ({ 
  pathname = null,
  onNavigate = null,
  className = "",
  showHomeIcon = true,
  maxItems = 5,
  separator = "chevron-right",
  useNavigationHook = true
}) => {
  // Use navigation hook if enabled
  const navigation = useNavigationHook ? useNavigation() : null;
  
  // Fallback state for when not using navigation hook
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [currentPath, setCurrentPath] = useState('/');

  // Update breadcrumbs when pathname changes (fallback mode)
  useEffect(() => {
    if (useNavigationHook && navigation) {
      // Use breadcrumbs from navigation hook
      return;
    }
    
    const path = pathname || getCurrentPathname();
    setCurrentPath(path);
    
    const generatedBreadcrumbs = generateEnhancedBreadcrumbs(path);
    
    // Limit breadcrumbs if maxItems is specified
    let displayBreadcrumbs = generatedBreadcrumbs;
    if (maxItems && generatedBreadcrumbs.length > maxItems) {
      // Keep first item (Home) and last few items
      const firstItem = generatedBreadcrumbs[0];
      const lastItems = generatedBreadcrumbs.slice(-(maxItems - 1));
      displayBreadcrumbs = [firstItem, ...lastItems];
    }
    
    setBreadcrumbs(displayBreadcrumbs);
  }, [pathname, maxItems, useNavigationHook, navigation]);

  // Handle breadcrumb item click
  const handleBreadcrumbClick = (breadcrumb) => {
    if (breadcrumb.isActive) {
      return; // Don't navigate if it's the current page
    }

    // Use navigation hook if available
    if (useNavigationHook && navigation) {
      navigation.handleNavigate(breadcrumb.path);
      return;
    }

    // Fallback to provided onNavigate or default navigation
    if (onNavigate && typeof onNavigate === 'function') {
      onNavigate(breadcrumb.path);
    } else {
      navigateToPath(breadcrumb.path);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (event, breadcrumb) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleBreadcrumbClick(breadcrumb);
    }
  };

  // Render chevron separator
  const renderSeparator = () => {
    if (separator === 'chevron-right') {
      return (
        <svg 
          className="breadcrumb-separator" 
          width="16" 
          height="16" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="9,18 15,12 9,6"></polyline>
        </svg>
      );
    }
    
    if (separator === 'slash') {
      return <span className="breadcrumb-separator" aria-hidden="true">/</span>;
    }
    
    return <span className="breadcrumb-separator" aria-hidden="true">›</span>;
  };

  // Get breadcrumbs from navigation hook or fallback state
  const displayBreadcrumbs = useNavigationHook && navigation ? navigation.breadcrumbs : breadcrumbs;
  const displayCurrentPath = useNavigationHook && navigation ? navigation.currentPath : currentPath;

  // Don't render if we're on the home page and showHomeIcon is false
  if (!showHomeIcon && displayCurrentPath === '/') {
    return null;
  }

  // Don't render if there's only one breadcrumb and it's home
  if (displayBreadcrumbs.length <= 1 && displayBreadcrumbs[0]?.path === '/') {
    return null;
  }

  return (
    <nav 
      className={`breadcrumb-navigation ${className}`}
      aria-label="Breadcrumb"
      role="navigation"
    >
      <ol className="breadcrumb-list">
        {displayBreadcrumbs.map((breadcrumb, index) => (
          <li key={breadcrumb.path} className="breadcrumb-item">
            {index > 0 && renderSeparator()}
            
            {breadcrumb.isActive ? (
              // Active breadcrumb (current page) - not clickable
              <span 
                className="breadcrumb-link breadcrumb-link--active"
                aria-current="page"
                title={breadcrumb.description || breadcrumb.label}
              >
                {breadcrumb.icon && (
                  <span className="breadcrumb-icon" aria-hidden="true">
                    {breadcrumb.icon}
                  </span>
                )}
                <span className="breadcrumb-label">{breadcrumb.label}</span>
              </span>
            ) : (
              // Inactive breadcrumb - clickable
              <button
                className="breadcrumb-link breadcrumb-link--inactive"
                onClick={() => handleBreadcrumbClick(breadcrumb)}
                onKeyDown={(e) => handleKeyDown(e, breadcrumb)}
                title={`Navigate to ${breadcrumb.label}`}
                aria-label={`Navigate to ${breadcrumb.label}`}
                type="button"
              >
                {breadcrumb.icon && (
                  <span className="breadcrumb-icon" aria-hidden="true">
                    {breadcrumb.icon}
                  </span>
                )}
                <span className="breadcrumb-label">{breadcrumb.label}</span>
              </button>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
};

export default BreadcrumbNavigation;
