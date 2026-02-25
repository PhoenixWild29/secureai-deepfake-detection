import React, { useState } from 'react';
import BreadcrumbNavigation from './BreadcrumbNavigation';

/**
 * BreadcrumbNavigationDemo Component
 * 
 * Demo component for testing the breadcrumb navigation implementation.
 * Provides various test paths and interactive controls to verify
 * breadcrumb functionality and accessibility compliance.
 */

const BreadcrumbNavigationDemo = () => {
  const [currentPath, setCurrentPath] = useState('/dashboard');
  const [maxItems, setMaxItems] = useState(4);
  const [separator, setSeparator] = useState('chevron-right');

  // Test paths for demonstration
  const testPaths = [
    { path: '/', label: 'Home' },
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/analytics', label: 'Analytics' },
    { path: '/videos', label: 'Videos' },
    { path: '/videos/upload', label: 'Video Upload' },
    { path: '/videos/analysis/123', label: 'Analysis Details' },
    { path: '/batch/processing', label: 'Batch Processing' },
    { path: '/reports/monthly', label: 'Monthly Reports' },
    { path: '/settings/profile', label: 'Profile Settings' },
    { path: '/settings/profile/security', label: 'Security Settings' },
    { path: '/help/documentation/api', label: 'API Documentation' }
  ];

  // Handle navigation
  const handleNavigate = (path) => {
    console.log('Navigating to:', path);
    setCurrentPath(path);
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem', color: '#1f2937' }}>
        Breadcrumb Navigation Demo
      </h1>

      {/* Demo Controls */}
      <div style={{ 
        background: '#f9fafb', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #e5e7eb'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#374151' }}>
          Demo Controls
        </h2>
        
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Current Path:
            </label>
            <select 
              value={currentPath} 
              onChange={(e) => setCurrentPath(e.target.value)}
              style={{
                padding: '0.5rem',
                borderRadius: '0.25rem',
                border: '1px solid #d1d5db',
                fontSize: '0.875rem'
              }}
            >
              {testPaths.map(testPath => (
                <option key={testPath.path} value={testPath.path}>
                  {testPath.path} - {testPath.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Max Items:
            </label>
            <input
              type="number"
              min="2"
              max="8"
              value={maxItems}
              onChange={(e) => setMaxItems(parseInt(e.target.value))}
              style={{
                padding: '0.5rem',
                borderRadius: '0.25rem',
                border: '1px solid #d1d5db',
                fontSize: '0.875rem',
                width: '80px'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Separator:
            </label>
            <select 
              value={separator} 
              onChange={(e) => setSeparator(e.target.value)}
              style={{
                padding: '0.5rem',
                borderRadius: '0.25rem',
                border: '1px solid #d1d5db',
                fontSize: '0.875rem'
              }}
            >
              <option value="chevron-right">Chevron Right</option>
              <option value="slash">Slash</option>
              <option value="arrow">Arrow</option>
            </select>
          </div>
        </div>

        <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
          <strong>Current Path:</strong> {currentPath}
        </div>
      </div>

      {/* Breadcrumb Navigation Demo */}
      <div style={{ 
        background: 'white', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#374151' }}>
          Breadcrumb Navigation
        </h2>
        
        <BreadcrumbNavigation
          pathname={currentPath}
          onNavigate={handleNavigate}
          maxItems={maxItems}
          separator={separator}
          className="demo-breadcrumbs"
        />
      </div>

      {/* Features List */}
      <div style={{ 
        background: '#f0f9ff', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #bae6fd'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#1e40af' }}>
          ✅ Implemented Features
        </h2>
        <ul style={{ listStyle: 'disc', marginLeft: '2rem', color: '#1e40af' }}>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Horizontal breadcrumb trail</strong> with Home icon and chevron separators
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Automatic URL parsing</strong> with human-readable labels and proper capitalization
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Clickable navigation</strong> for non-active items with smooth transitions
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Accessibility compliance</strong> with ARIA labels, semantic markup, and keyboard navigation
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Consistent styling</strong> with text-sm sizing, muted colors for inactive items
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Active item styling</strong> with foreground color and font-medium weight
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Hover states</strong> with underline effects and smooth color transitions
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Responsive design</strong> with mobile-optimized behavior and ellipsis for long paths
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Dark mode support</strong> and high contrast mode compatibility
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Configurable options</strong> for max items, separator style, and custom navigation
          </li>
        </ul>
      </div>

      {/* Testing Instructions */}
      <div style={{ 
        background: '#fef3c7', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        border: '1px solid #f59e0b'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#92400e' }}>
          🧪 Testing Instructions
        </h2>
        <ol style={{ listStyle: 'decimal', marginLeft: '2rem', color: '#92400e' }}>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Path Testing:</strong> Use the dropdown to change the current path and observe breadcrumb updates
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Click Testing:</strong> Click on inactive breadcrumb items to test navigation
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Keyboard Testing:</strong> Use Tab to navigate and Enter/Space to activate breadcrumb items
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Responsive Testing:</strong> Resize browser window to test mobile behavior and ellipsis functionality
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Max Items Testing:</strong> Adjust max items to see how breadcrumbs truncate on smaller screens
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Separator Testing:</strong> Change separator style to test different visual separators
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Accessibility Testing:</strong> Use screen reader to verify ARIA labels and semantic structure
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            <strong>Focus Testing:</strong> Verify focus indicators and keyboard navigation work properly
          </li>
        </ol>
      </div>

      {/* Console Output */}
      <div style={{ 
        background: '#1f2937', 
        padding: '1rem', 
        borderRadius: '0.5rem',
        marginTop: '2rem'
      }}>
        <h3 style={{ color: '#f9fafb', marginBottom: '0.5rem' }}>
          Console Output
        </h3>
        <p style={{ color: '#9ca3af', fontSize: '0.875rem', fontFamily: 'monospace' }}>
          Check browser console for navigation events and breadcrumb generation logs.
        </p>
      </div>
    </div>
  );
};

export default BreadcrumbNavigationDemo;
