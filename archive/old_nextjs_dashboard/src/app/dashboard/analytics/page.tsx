"use client"

import React from 'react';
import DashboardLayoutWrapper from '@/components/DashboardLayout';
import AnalyticsDashboard from '@/components/AnalyticsDashboard/AnalyticsDashboard';

export default function AnalyticsPage() {
  return (
    <DashboardLayoutWrapper>
      <AnalyticsDashboard />
    </DashboardLayoutWrapper>
  );
}
