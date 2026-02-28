import React, { useState } from 'react';
import { useNavigation } from '../hooks/useNavigation';
import BreadcrumbNavigation from './BreadcrumbNavigation';

/**
 * NavigationStateManagementDemo Component
 * 
 * Comprehensive demo component for testing the navigation state management
 * and routing integration implementation.
 */

const NavigationStateManagementDemo = () => {
  const navigation = useNavigation({
    enableDataPrefetching: true,
    enableHistoryTracking: true,
    enablePerformanceTracking: true,
    maxHistoryItems: 10,
    prefetchDelay: 100
  });

  const [testPath, setTestPath] = useState('/dashboard');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Test paths for demonstration
  const testPaths = [
    { path: '/', label: 'Home' },
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/analytics', label: 'Analytics' },
    { path: '/analytics/reports', label: 'Analytics Reports' },
    { path: '/videos', label: 'Videos' },
    { path: '/videos/upload', label: 'Video Upload' },
    { path: '/videos/analysis/123', label: 'Analysis Details' },
    { path: '/batch', label: 'Batch Processing' },
    { path: '/batch/processing', label: 'Batch Processing Status' },
    { path: '/reports', label: 'Reports' },
    { path: '/reports/monthly', label: 'Monthly Reports' },
    { path: '/settings', label: 'Settings' },
    { path: '/settings/profile', label: 'Profile Settings' },
    { path: '/settings/profile/security', label: 'Security Settings' },
    { path: '/notifications', label: 'Notifications' },
    { path: '/help', label: 'Help & Support' },
    { path: '/help/documentation/api', label: 'API Documentation' }
  ];

  // Handle test navigation
  const handleTestNavigation = (path) => {
    navigation.handleNavigate(path);
    setTestPath(path);
  };

  // Handle navigation with options
  const handleNavigationWithOptions = (path, options = {}) => {
    navigation.handleNavigate(path, options);
    setTestPath(path);
  };

  // Get navigation suggestions
  const suggestions = navigation.getSuggestions(5);

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem', color: '#1f2937' }}>
        Navigation State Management Demo
      </h1>

      {/* Current Navigation State */}
      <div style={{ 
        background: '#f0f9ff', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #bae6fd'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#1e40af' }}>
          📊 Current Navigation State
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <strong>Current Path:</strong> {navigation.currentPath}
          </div>
          <div>
            <strong>Is Navigating:</strong> {navigation.isNavigating ? 'Yes' : 'No'}
          </div>
          <div>
            <strong>Is Collapsed:</strong> {navigation.isCollapsed ? 'Yes' : 'No'}
          </div>
          <div>
            <strong>Mobile Menu Open:</strong> {navigation.isMobileMenuOpen ? 'Yes' : 'No'}
          </div>
          <div>
            <strong>History Items:</strong> {navigation.navigationHistory.length}
          </div>
          <div>
            <strong>Breadcrumbs:</strong> {navigation.breadcrumbs.length}
          </div>
        </div>

        {navigation.navigationError && (
          <div style={{ 
            marginTop: '1rem', 
            padding: '0.75rem', 
            background: '#fef2f2', 
            border: '1px solid #fecaca',
            borderRadius: '0.25rem',
            color: '#dc2626'
          }}>
            <strong>Navigation Error:</strong> {navigation.navigationError.message}
          </div>
        )}
      </div>

      {/* Breadcrumb Navigation */}
      <div style={{ 
        background: 'white', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#374151' }}>
          🧭 Breadcrumb Navigation
        </h2>
        
        <BreadcrumbNavigation
          useNavigationHook={true}
          className="demo-breadcrumbs"
          maxItems={6}
        />
      </div>

      {/* Navigation Controls */}
      <div style={{ 
        background: '#f9fafb', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #e5e7eb'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#374151' }}>
          🎮 Navigation Controls
        </h2>
        
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <button
            onClick={() => navigation.toggleCollapse()}
            style={{
              padding: '0.5rem 1rem',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Toggle Collapse
          </button>
          
          <button
            onClick={() => navigation.toggleMobileMenu()}
            style={{
              padding: '0.5rem 1rem',
              background: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Toggle Mobile Menu
          </button>
          
          <button
            onClick={() => navigation.navigateToParent()}
            style={{
              padding: '0.5rem 1rem',
              background: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Navigate to Parent
          </button>
          
          <button
            onClick={() => navigation.navigateBack()}
            style={{
              padding: '0.5rem 1rem',
              background: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Navigate Back
          </button>
          
          <button
            onClick={() => navigation.clearHistory()}
            style={{
              padding: '0.5rem 1rem',
              background: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Clear History
          </button>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
            Test Navigation Path:
          </label>
          <select 
            value={testPath} 
            onChange={(e) => setTestPath(e.target.value)}
            style={{
              padding: '0.5rem',
              borderRadius: '0.25rem',
              border: '1px solid #d1d5db',
              fontSize: '0.875rem',
              marginRight: '1rem'
            }}
          >
            {testPaths.map(testPath => (
              <option key={testPath.path} value={testPath.path}>
                {testPath.path} - {testPath.label}
              </option>
            ))}
          </select>
          
          <button
            onClick={() => handleTestNavigation(testPath)}
            style={{
              padding: '0.5rem 1rem',
              background: '#059669',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Navigate
          </button>
        </div>

        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          style={{
            padding: '0.5rem 1rem',
            background: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '0.25rem',
            cursor: 'pointer'
          }}
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced Options
        </button>

        {showAdvanced && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: '#f3f4f6', borderRadius: '0.25rem' }}>
            <h3 style={{ marginBottom: '0.5rem' }}>Advanced Navigation Options:</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              <button
                onClick={() => handleNavigationWithOptions(testPath, { replace: true })}
                style={{
                  padding: '0.25rem 0.5rem',
                  background: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                Replace Navigation
              </button>
              
              <button
                onClick={() => handleNavigationWithOptions(testPath, { prefetch: false })}
                style={{
                  padding: '0.25rem 0.5rem',
                  background: '#f59e0b',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                No Prefetch
              </button>
              
              <button
                onClick={() => handleNavigationWithOptions(testPath, { addToHistory: false })}
                style={{
                  padding: '0.25rem 0.5rem',
                  background: '#8b5cf6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem'
                }}
              >
                No History
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Navigation History */}
      <div style={{ 
        background: '#fef3c7', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #f59e0b'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#92400e' }}>
          📚 Navigation History ({navigation.navigationHistory.length} items)
        </h2>
        
        {navigation.navigationHistory.length === 0 ? (
          <p style={{ color: '#92400e', fontStyle: 'italic' }}>
            No navigation history yet. Start navigating to see history entries.
          </p>
        ) : (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {navigation.navigationHistory.map((entry, index) => (
              <div key={index} style={{ 
                padding: '0.5rem', 
                marginBottom: '0.5rem', 
                background: 'white', 
                borderRadius: '0.25rem',
                border: '1px solid #e5e7eb',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <strong>{entry.label}</strong> - {entry.path}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Navigation Suggestions */}
      {suggestions.length > 0 && (
        <div style={{ 
          background: '#ecfdf5', 
          padding: '1.5rem', 
          borderRadius: '0.5rem',
          marginBottom: '2rem',
          border: '1px solid #a7f3d0'
        }}>
          <h2 style={{ marginBottom: '1rem', color: '#065f46' }}>
            💡 Navigation Suggestions
          </h2>
          
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleTestNavigation(suggestion.path)}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                {suggestion.label} ({suggestion.count}x)
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      <div style={{ 
        background: '#f3f4f6', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        marginBottom: '2rem',
        border: '1px solid #d1d5db'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#374151' }}>
          ⚡ Performance Metrics
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
          {testPaths.slice(0, 5).map(testPath => {
            const metrics = navigation.getPerformanceMetrics(testPath.path);
            return (
              <div key={testPath.path} style={{ 
                padding: '0.75rem', 
                background: 'white', 
                borderRadius: '0.25rem',
                border: '1px solid #e5e7eb'
              }}>
                <div style={{ fontWeight: '500', fontSize: '0.875rem' }}>
                  {testPath.label}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {metrics ? `${metrics.toFixed(2)}ms` : 'No data'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Configuration */}
      <div style={{ 
        background: '#f0f9ff', 
        padding: '1.5rem', 
        borderRadius: '0.5rem',
        border: '1px solid #bae6fd'
      }}>
        <h2 style={{ marginBottom: '1rem', color: '#1e40af' }}>
          ⚙️ Navigation Configuration
        </h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <strong>Data Prefetching:</strong> {navigation.config.enableDataPrefetching ? 'Enabled' : 'Disabled'}
          </div>
          <div>
            <strong>History Tracking:</strong> {navigation.config.enableHistoryTracking ? 'Enabled' : 'Disabled'}
          </div>
          <div>
            <strong>Performance Tracking:</strong> {navigation.config.enablePerformanceTracking ? 'Enabled' : 'Disabled'}
          </div>
          <div>
            <strong>Max History Items:</strong> {navigation.config.maxHistoryItems}
          </div>
          <div>
            <strong>Prefetch Delay:</strong> {navigation.config.prefetchDelay}ms
          </div>
        </div>
      </div>
    </div>
  );
};

export default NavigationStateManagementDemo;
