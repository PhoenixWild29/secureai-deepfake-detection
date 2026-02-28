import React from 'react';
import Layout from './Layout';
import MobileNavigation from './MobileNavigation';

/**
 * Demo Component for Testing Mobile Navigation
 * 
 * This component demonstrates the mobile navigation implementation
 * and can be used for testing responsive behavior.
 */

const MobileNavigationDemo = () => {
  // Custom navigation items for testing
  const navigationItems = [
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
      icon: '📈',
      badge: '3'
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

  // Custom logo component
  const customLogo = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
      <div style={{
        width: '40px',
        height: '40px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: '1.5rem'
      }}>
        🛡️
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: '1.25rem', fontWeight: '700', color: '#1f2937', lineHeight: '1.2' }}>
          SecureAI
        </span>
        <span style={{ fontSize: '0.75rem', color: '#6b7280', lineHeight: '1.2' }}>
          DeepFake Detection
        </span>
      </div>
    </div>
  );

  // Custom user menu
  const customUserMenu = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px' }}>
      <div style={{
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'white',
        fontSize: '1.25rem'
      }}>
        👤
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '0.875rem', fontWeight: '600', color: '#374151', lineHeight: '1.2' }}>
          John Doe
        </div>
        <div style={{ fontSize: '0.75rem', color: '#6b7280', lineHeight: '1.2' }}>
          Administrator
        </div>
      </div>
    </div>
  );

  return (
    <Layout
      navigationItems={navigationItems}
      logo={customLogo}
      userMenu={customUserMenu}
    >
      <div style={{ padding: '2rem' }}>
        <h1 style={{ marginBottom: '1rem', color: '#1f2937' }}>
          Mobile Navigation Demo
        </h1>
        
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ marginBottom: '1rem', color: '#374151' }}>
            Responsive Navigation Testing
          </h2>
          <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
            This demo showcases the mobile navigation implementation with responsive design patterns.
            Resize your browser window or test on different devices to see the navigation adapt.
          </p>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', color: '#374151' }}>
            Features Implemented
          </h3>
          <ul style={{ listStyle: 'disc', marginLeft: '2rem', color: '#6b7280' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Hamburger Menu:</strong> Toggles full-screen navigation overlay on mobile devices
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Touch-Friendly:</strong> Navigation items with larger tap targets (py-3) and 44px minimum touch targets
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Smooth Animations:</strong> Open/close animations with backdrop blur effects
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Auto-Close:</strong> Mobile menu automatically closes when navigation item is selected
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Responsive Breakpoints:</strong> Desktop navigation on md+ screens, mobile navigation on smaller screens
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Accessibility:</strong> Proper ARIA labels, keyboard navigation, and focus management
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Backdrop Blur:</strong> Visual separation with bg-background/80 backdrop-blur-sm
            </li>
          </ul>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', color: '#374151' }}>
            Testing Instructions
          </h3>
          <ol style={{ listStyle: 'decimal', marginLeft: '2rem', color: '#6b7280' }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Desktop Testing:</strong> On screens 768px and wider, you should see the desktop navigation sidebar
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Mobile Testing:</strong> On screens smaller than 768px, you should see a hamburger menu button
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Touch Testing:</strong> Click/tap the hamburger menu to open the full-screen navigation overlay
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Navigation Testing:</strong> Click/tap any navigation item to see the menu auto-close
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Keyboard Testing:</strong> Use Tab to navigate and Enter/Space to activate menu items
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Escape Key:</strong> Press Escape to close the mobile menu
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <strong>Backdrop Testing:</strong> Click outside the navigation overlay to close it
            </li>
          </ol>
        </div>

        <div style={{ 
          background: '#f3f4f6', 
          padding: '1rem', 
          borderRadius: '0.5rem',
          border: '1px solid #e5e7eb'
        }}>
          <h4 style={{ marginBottom: '0.5rem', color: '#374151' }}>
            Current Screen Size
          </h4>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
            Width: {window.innerWidth}px | 
            Breakpoint: {window.innerWidth < 768 ? 'Mobile' : 'Desktop'} | 
            Navigation: {window.innerWidth < 768 ? 'Mobile (Hamburger)' : 'Desktop (Sidebar)'}
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default MobileNavigationDemo;
