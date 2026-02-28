"use client"

import React from 'react';
import DashboardLayoutWrapper from '@/components/DashboardLayout';
import DashboardOverview from '@/pages/DashboardOverview';

export default function DashboardPage() {
  return (
    <DashboardLayoutWrapper>
      <DashboardOverview />
    </DashboardLayoutWrapper>
  );
}
