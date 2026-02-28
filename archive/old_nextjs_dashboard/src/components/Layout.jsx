import React, { useState, useEffect } from 'react';
import MobileNavigation from './MobileNavigation';
import './Layout.css';

/**
 * Layout Component
 * 
 * Main layout component that handles responsive navigation display.
 * Shows mobile navigation on screens smaller than md breakpoint,
 * and desktop navigation on md+ screens.
 */

const Layout = ({ 
  children, 
  navigationItems = [],
  desktopNavigation = null,
  logo = null,
  userMenu = null,
  className = ""
}) => {
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);

  // Handle responsive breakpoint detection
  useEffect(() => {
    const checkScreenSize = () => {
      const width = window.innerWidth;
      setIsMobile(width < 640); // sm breakpoint
      setIsTablet(width >= 640 && width < 768); // md breakpoint
    };

    // Check on mount
    checkScreenSize();

    // Add resize listener
    window.addEventListener('resize', checkScreenSize);

    // Cleanup
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  // Handle navigation item click
  const handleNavigation = (item) => {
    console.log('Navigation clicked:', item);
    // Add your navigation logic here
    // For example: router.push(item.href) or navigate(item.href)
  };

  // Default navigation items
  const defaultNavigationItems = [
    { 
      id: 'dashboard', 
      label: 'Dashboard', 
      href: '/dashboard', 
      icon: '📊',
      active: true 
    },
    { 
      id: 'analytics', 
      label: 'Analytics', 
      href: '/analytics', 
      icon: '📈' 
    },
    { 
      id: 'videos', 
      label: 'Video Analysis', 
      href: '/videos', 
      icon: '🎥' 
    },
    { 
      id: 'batch', 
      label: 'Batch Processing', 
      href: '/batch', 
      icon: '⚡' 
    },
    { 
      id: 'reports', 
      label: 'Reports', 
      href: '/reports', 
      icon: '📋' 
    },
    { 
      id: 'settings', 
      label: 'Settings', 
      href: '/settings', 
      icon: '⚙️' 
    },
    { 
      id: 'help', 
      label: 'Help & Support', 
      href: '/help', 
      icon: '❓' 
    }
  ];

  const navItems = navigationItems.length > 0 ? navigationItems : defaultNavigationItems;

  // Default logo component
  const defaultLogo = (
    <div className="layout-logo">
      <div className="logo-icon">🛡️</div>
      <div className="logo-text">
        <span className="logo-title">SecureAI</span>
        <span className="logo-subtitle">DeepFake Detection</span>
      </div>
    </div>
  );

  // Default user menu
  const defaultUserMenu = (
    <div className="layout-user-menu">
      <div className="user-avatar">
        <span>👤</span>
      </div>
      <div className="user-info">
        <div className="user-name">John Doe</div>
        <div className="user-role">Administrator</div>
      </div>
    </div>
  );

  return (
    <div className={`layout ${className}`}>
      {/* Mobile Navigation - Only visible on screens smaller than md */}
      <div className="layout-mobile-nav">
        <MobileNavigation
          navigationItems={navItems}
          onNavigate={handleNavigation}
          logo={logo || defaultLogo}
          userMenu={userMenu || defaultUserMenu}
        />
      </div>

      {/* Desktop Navigation - Only visible on md+ screens */}
      <div className="layout-desktop-nav">
        {desktopNavigation || (
          <nav className="desktop-navigation">
            <div className="desktop-nav-header">
              {logo || defaultLogo}
            </div>
            <ul className="desktop-nav-list">
              {navItems.map((item) => (
                <li key={item.id} className="desktop-nav-item">
                  <a
                    href={item.href}
                    className={`desktop-nav-link ${item.active ? 'active' : ''}`}
                    onClick={(e) => {
                      e.preventDefault();
                      handleNavigation(item);
                    }}
                  >
                    {item.icon && (
                      <span className="desktop-nav-icon" aria-hidden="true">
                        {item.icon}
                      </span>
                    )}
                    <span className="desktop-nav-label">{item.label}</span>
                    {item.badge && (
                      <span className="desktop-nav-badge">{item.badge}</span>
                    )}
                  </a>
                </li>
              ))}
            </ul>
            <div className="desktop-nav-footer">
              {userMenu || defaultUserMenu}
            </div>
          </nav>
        )}
      </div>

      {/* Main Content Area */}
      <main className="layout-main">
        <div className="layout-content">
          {children}
        </div>
      </main>

      {/* Screen Size Indicator (for development) */}
      {process.env.NODE_ENV === 'development' && (
        <div className="layout-debug">
          <div className="debug-info">
            <span>Screen: {isMobile ? 'Mobile' : isTablet ? 'Tablet' : 'Desktop'}</span>
            <span>Width: {window.innerWidth}px</span>
            <span>Breakpoint: {isMobile ? '< sm' : isTablet ? 'sm-md' : 'md+'}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default Layout;
