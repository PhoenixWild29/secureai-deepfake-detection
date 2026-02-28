/**
 * Responsive Dashboard Layout Component
 * Mobile-optimized layout with touch-friendly interactions and responsive design patterns
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import { measureComponentRender } from '@/utils/performanceMonitor';
import styles from './DashboardLayout.module.css';

// Component props
interface DashboardLayoutProps {
  children: React.ReactNode;
  className?: string;
  showSidebar?: boolean;
  sidebarCollapsed?: boolean;
  onSidebarToggle?: (collapsed: boolean) => void;
  enableTouchGestures?: boolean;
  enableKeyboardNavigation?: boolean;
  enablePerformanceMonitoring?: boolean;
}

// Layout state
interface LayoutState {
  sidebarCollapsed: boolean;
  sidebarVisible: boolean;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  touchDevice: boolean;
  orientation: 'portrait' | 'landscape';
  viewportWidth: number;
  viewportHeight: number;
}

// Breakpoint configuration
const BREAKPOINTS = {
  mobile: 640,
  tablet: 768,
  desktop: 1024,
  wide: 1280,
  ultraWide: 1920,
};

// Touch gesture configuration
const TOUCH_CONFIG = {
  swipeThreshold: 50,
  longPressThreshold: 500,
  doubleTapThreshold: 300,
};

/**
 * Responsive Dashboard Layout Component
 */
export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  className = '',
  showSidebar = true,
  sidebarCollapsed = false,
  onSidebarToggle,
  enableTouchGestures = true,
  enableKeyboardNavigation = true,
  enablePerformanceMonitoring = true,
}) => {
  const router = useRouter();
  const renderTimer = useRef<{ end: () => number } | null>(null);

  // State management
  const [layoutState, setLayoutState] = useState<LayoutState>({
    sidebarCollapsed: sidebarCollapsed,
    sidebarVisible: showSidebar,
    isMobile: false,
    isTablet: false,
    isDesktop: false,
    touchDevice: false,
    orientation: 'portrait',
    viewportWidth: 0,
    viewportHeight: 0,
  });

  // Refs
  const layoutRef = useRef<HTMLDivElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const lastTapRef = useRef<number>(0);

  // Performance monitoring
  useEffect(() => {
    if (enablePerformanceMonitoring) {
      renderTimer.current = measureComponentRender('DashboardLayout');
    }
    
    return () => {
      if (renderTimer.current) {
        renderTimer.current.end();
      }
    };
  }, [enablePerformanceMonitoring]);

  // Responsive breakpoint detection
  const updateLayoutState = useCallback(() => {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    setLayoutState(prev => ({
      ...prev,
      isMobile: width < BREAKPOINTS.mobile,
      isTablet: width >= BREAKPOINTS.mobile && width < BREAKPOINTS.desktop,
      isDesktop: width >= BREAKPOINTS.desktop,
      touchDevice: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
      orientation: width > height ? 'landscape' : 'portrait',
      viewportWidth: width,
      viewportHeight: height,
      sidebarVisible: width >= BREAKPOINTS.tablet ? showSidebar : false,
      sidebarCollapsed: width < BREAKPOINTS.tablet ? true : prev.sidebarCollapsed,
    }));
  }, [showSidebar]);

  // Handle window resize
  useEffect(() => {
    updateLayoutState();
    
    const handleResize = () => {
      updateLayoutState();
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
    };
  }, [updateLayoutState]);

  // Handle sidebar toggle
  const handleSidebarToggle = useCallback(() => {
    const newCollapsed = !layoutState.sidebarCollapsed;
    
    setLayoutState(prev => ({
      ...prev,
      sidebarCollapsed: newCollapsed,
    }));

    onSidebarToggle?.(newCollapsed);
  }, [layoutState.sidebarCollapsed, onSidebarToggle]);

  // Touch gesture handling
  const handleTouchStart = useCallback((event: React.TouchEvent) => {
    if (!enableTouchGestures || !layoutState.touchDevice) return;

    const touch = event.touches[0];
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
  }, [enableTouchGestures, layoutState.touchDevice]);

  const handleTouchEnd = useCallback((event: React.TouchEvent) => {
    if (!enableTouchGestures || !layoutState.touchDevice || !touchStartRef.current) return;

    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    const deltaTime = Date.now() - touchStartRef.current.time;

    // Swipe detection
    if (Math.abs(deltaX) > TOUCH_CONFIG.swipeThreshold && Math.abs(deltaY) < TOUCH_CONFIG.swipeThreshold) {
      if (deltaX > 0 && layoutState.isMobile) {
        // Swipe right - show sidebar
        setLayoutState(prev => ({ ...prev, sidebarVisible: true }));
      } else if (deltaX < 0 && layoutState.isMobile) {
        // Swipe left - hide sidebar
        setLayoutState(prev => ({ ...prev, sidebarVisible: false }));
      }
    }

    // Double tap detection
    if (deltaTime < TOUCH_CONFIG.doubleTapThreshold) {
      const now = Date.now();
      if (now - lastTapRef.current < TOUCH_CONFIG.doubleTapThreshold) {
        // Double tap - toggle sidebar
        handleSidebarToggle();
      }
      lastTapRef.current = now;
    }

    touchStartRef.current = null;
  }, [enableTouchGestures, layoutState.touchDevice, layoutState.isMobile, handleSidebarToggle]);

  // Keyboard navigation
  useEffect(() => {
    if (!enableKeyboardNavigation) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Alt + S to toggle sidebar
      if (event.altKey && event.key === 's') {
        event.preventDefault();
        handleSidebarToggle();
      }

      // Escape to close sidebar on mobile
      if (event.key === 'Escape' && layoutState.isMobile && layoutState.sidebarVisible) {
        setLayoutState(prev => ({ ...prev, sidebarVisible: false }));
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enableKeyboardNavigation, handleSidebarToggle, layoutState.isMobile, layoutState.sidebarVisible]);

  // Focus management
  const handleSidebarFocus = useCallback(() => {
    if (layoutState.isMobile) {
      setLayoutState(prev => ({ ...prev, sidebarVisible: true }));
    }
  }, [layoutState.isMobile]);

  const handleContentFocus = useCallback(() => {
    if (layoutState.isMobile && layoutState.sidebarVisible) {
      setLayoutState(prev => ({ ...prev, sidebarVisible: false }));
    }
  }, [layoutState.isMobile, layoutState.sidebarVisible]);

  // CSS classes based on state
  const getLayoutClasses = () => {
    const classes = [styles.dashboardLayout];
    
    if (className) classes.push(className);
    if (layoutState.isMobile) classes.push(styles.mobile);
    if (layoutState.isTablet) classes.push(styles.tablet);
    if (layoutState.isDesktop) classes.push(styles.desktop);
    if (layoutState.touchDevice) classes.push(styles.touchDevice);
    if (layoutState.orientation === 'landscape') classes.push(styles.landscape);
    if (layoutState.sidebarCollapsed) classes.push(styles.sidebarCollapsed);
    if (layoutState.sidebarVisible) classes.push(styles.sidebarVisible);
    
    return classes.join(' ');
  };

  const getSidebarClasses = () => {
    const classes = [styles.sidebar];
    
    if (layoutState.sidebarCollapsed) classes.push(styles.collapsed);
    if (layoutState.isMobile) classes.push(styles.mobileSidebar);
    if (layoutState.touchDevice) classes.push(styles.touchSidebar);
    
    return classes.join(' ');
  };

  const getContentClasses = () => {
    const classes = [styles.content];
    
    if (layoutState.sidebarVisible && !layoutState.sidebarCollapsed) {
      classes.push(styles.contentWithSidebar);
    }
    if (layoutState.isMobile) classes.push(styles.mobileContent);
    if (layoutState.touchDevice) classes.push(styles.touchContent);
    
    return classes.join(' ');
  };

  return (
    <div
      ref={layoutRef}
      className={getLayoutClasses()}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      data-testid="dashboard-layout"
    >
      {/* Skip link for accessibility */}
      <a href="#main-content" className={styles.skipLink}>
        Skip to main content
      </a>

      {/* Sidebar */}
      {layoutState.sidebarVisible && (
        <aside
          ref={sidebarRef}
          className={getSidebarClasses()}
          onFocus={handleSidebarFocus}
          role="complementary"
          aria-label="Dashboard navigation"
        >
          <div className={styles.sidebarContent}>
            {/* Sidebar toggle button */}
            <button
              className={styles.sidebarToggle}
              onClick={handleSidebarToggle}
              aria-label={layoutState.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-expanded={!layoutState.sidebarCollapsed}
            >
              <span className={styles.toggleIcon}>
                {layoutState.sidebarCollapsed ? '→' : '←'}
              </span>
            </button>

            {/* Sidebar content */}
            <nav className={styles.sidebarNavigation}>
              {/* Navigation items would go here */}
              <div className={styles.navPlaceholder}>
                Navigation Content
              </div>
            </nav>
          </div>

          {/* Mobile overlay */}
          {layoutState.isMobile && layoutState.sidebarVisible && (
            <div
              className={styles.mobileOverlay}
              onClick={() => setLayoutState(prev => ({ ...prev, sidebarVisible: false }))}
              aria-hidden="true"
            />
          )}
        </aside>
      )}

      {/* Main content */}
      <main
        ref={contentRef}
        id="main-content"
        className={getContentClasses()}
        onFocus={handleContentFocus}
        role="main"
        tabIndex={-1}
      >
        {/* Content header */}
        <header className={styles.contentHeader}>
          <div className={styles.headerContent}>
            <h1 className={styles.pageTitle}>Dashboard</h1>
            
            {/* Mobile menu button */}
            {layoutState.isMobile && (
              <button
                className={styles.mobileMenuButton}
                onClick={() => setLayoutState(prev => ({ ...prev, sidebarVisible: !prev.sidebarVisible }))}
                aria-label="Open navigation menu"
                aria-expanded={layoutState.sidebarVisible}
              >
                <span className={styles.menuIcon}>☰</span>
              </button>
            )}
          </div>
        </header>

        {/* Content area */}
        <div className={styles.contentArea}>
          {children}
        </div>
      </main>

      {/* Performance indicator (development only) */}
      {process.env.NODE_ENV === 'development' && (
        <div className={styles.performanceIndicator}>
          <div className={styles.performanceInfo}>
            <span>Viewport: {layoutState.viewportWidth}×{layoutState.viewportHeight}</span>
            <span>Device: {layoutState.touchDevice ? 'Touch' : 'Mouse'}</span>
            <span>Orientation: {layoutState.orientation}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardLayout;
