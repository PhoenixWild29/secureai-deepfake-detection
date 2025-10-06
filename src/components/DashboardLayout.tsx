"use client"

import React from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import DashboardNavigation from '@/components/DashboardNavigation';
import { useDashboardNavigation } from '@/components/DashboardNavigation';

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

/**
 * DashboardLayout component
 * Main layout wrapper for dashboard pages with navigation
 */
export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const { collapsed, mobileOpen, toggleMobile, setMobileOpen } = useDashboardNavigation();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Navigation */}
      <DashboardNavigation
        collapsed={collapsed}
        showMobileToggle={true}
        mobileOpen={mobileOpen}
        onMobileChange={setMobileOpen}
        className="lg:static lg:inset-auto"
      />

      {/* Main content */}
      <div className={`transition-all duration-300 ease-in-out ${
        collapsed ? 'lg:ml-16' : 'lg:ml-64'
      }`}>
        <main className="min-h-screen">
          {children}
        </main>
      </div>
    </div>
  );
};

/**
 * Dashboard page wrapper with authentication
 */
export default function DashboardLayoutWrapper({ children }: DashboardLayoutProps) {
  return (
    <AuthProvider>
      <DashboardLayout>
        {children}
      </DashboardLayout>
    </AuthProvider>
  );
}