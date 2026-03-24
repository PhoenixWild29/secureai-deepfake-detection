import React, { useState, useEffect } from 'react';
import './MobileNavigation.css';

/**
 * MobileNavigation Component
 * 
 * A mobile-optimized navigation component that provides touch-friendly interactions
 * and responsive design patterns for screens smaller than md breakpoint.
 * 
 * Features:
 * - Hamburger menu button that toggles full-screen navigation overlay
 * - Touch-friendly navigation items with larger tap targets (py-3)
 * - Smooth open/close animations
 * - Backdrop blur and overlay background
 * - Auto-close when navigation item is selected
 * - 44px minimum touch targets for accessibility compliance
 */

const MobileNavigation = ({ 
  navigationItems = [], 
  onNavigate = () => {},
  className = "",
  logo = null,
  userMenu = null 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);

  // Close mobile menu when navigation item is selected
  const handleNavigationClick = (item) => {
    setIsOpen(false);
    onNavigate(item);
  };

  // Toggle mobile menu with animation handling
  const toggleMenu = () => {
    if (isOpen) {
      setIsAnimating(true);
      setTimeout(() => {
        setIsOpen(false);
        setIsAnimating(false);
      }, 150); // Match CSS transition duration
    } else {
      setIsOpen(true);
    }
  };

  // Close menu when clicking outside
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      toggleMenu();
    }
  };

  // Close menu on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        toggleMenu();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when menu is open
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  // Default navigation items if none provided
  const defaultNavigationItems = [
    { id: 'dashboard', label: 'Dashboard', href: '/dashboard', icon: '📊' },
    { id: 'analytics', label: 'Analytics', href: '/analytics', icon: '📈' },
    { id: 'videos', label: 'Videos', href: '/videos', icon: '🎥' },
    { id: 'settings', label: 'Settings', href: '/settings', icon: '⚙️' },
    { id: 'help', label: 'Help', href: '/help', icon: '❓' }
  ];

  const navItems = navigationItems.length > 0 ? navigationItems : defaultNavigationItems;

  return (
    <div className={`mobile-navigation ${className}`}>
      {/* Hamburger Menu Button */}
      <button
        className="mobile-nav-toggle"
        onClick={toggleMenu}
        aria-label={isOpen ? 'Close navigation menu' : 'Open navigation menu'}
        aria-expanded={isOpen}
        aria-controls="mobile-nav-overlay"
      >
        <div className={`hamburger ${isOpen ? 'active' : ''}`}>
          <span className="hamburger-line"></span>
          <span className="hamburger-line"></span>
          <span className="hamburger-line"></span>
        </div>
      </button>

      {/* Full-Screen Navigation Overlay */}
      {isOpen && (
        <div
          id="mobile-nav-overlay"
          className={`mobile-nav-overlay ${isAnimating ? 'closing' : 'opening'}`}
          onClick={handleBackdropClick}
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-nav-title"
        >
          {/* Navigation Content */}
          <nav className="mobile-nav-content">
            {/* Header Section */}
            <div className="mobile-nav-header">
              {logo && (
                <div className="mobile-nav-logo">
                  {logo}
                </div>
              )}
              <h2 id="mobile-nav-title" className="mobile-nav-title">
                Navigation
              </h2>
            </div>

            {/* Navigation Items */}
            <ul className="mobile-nav-list">
              {navItems.map((item) => (
                <li key={item.id} className="mobile-nav-item">
                  <button
                    className="mobile-nav-link"
                    onClick={() => handleNavigationClick(item)}
                    aria-label={`Navigate to ${item.label}`}
                  >
                    {item.icon && (
                      <span className="mobile-nav-icon" aria-hidden="true">
                        {item.icon}
                      </span>
                    )}
                    <span className="mobile-nav-label">{item.label}</span>
                    {item.badge && (
                      <span className="mobile-nav-badge" aria-label={`${item.badge} notifications`}>
                        {item.badge}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>

            {/* User Menu Section */}
            {userMenu && (
              <div className="mobile-nav-user">
                {userMenu}
              </div>
            )}

            {/* Footer Section */}
            <div className="mobile-nav-footer">
              <div className="mobile-nav-version">
                SecureAI Dashboard v1.0
              </div>
            </div>
          </nav>
        </div>
      )}
    </div>
  );
};

export default MobileNavigation;
