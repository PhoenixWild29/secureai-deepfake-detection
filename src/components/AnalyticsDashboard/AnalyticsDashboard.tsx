"use client"

import React, { useState, useEffect, useCallback } from 'react';
import { DashboardLayout } from '@/components/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Server, 
  Download, 
  RefreshCw, 
  Calendar,
  Filter,
  Settings,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
  Eye,
  FileText
} from 'lucide-react';

// Import sub-components
import { PerformanceTrendsChart } from './PerformanceTrendsChart';
import { UserEngagementChart } from './UserEngagementChart';
import { SystemUtilizationChart } from './SystemUtilizationChart';
import { DateRangeSelector } from './DateRangeSelector';
import { ExportButton } from './ExportButton';

// Import services and hooks
import { analyticsService } from '@/services/analyticsService';
import { useAnalyticsData } from '@/hooks/useAnalyticsData';
import type { 
  AnalyticsRequest, 
  AnalyticsResponse, 
  DateRangeType,
  ExportFormat 
} from '@/services/analyticsService';

interface AnalyticsDashboardProps {
  className?: string;
}

export default function AnalyticsDashboard({ className }: AnalyticsDashboardProps) {
  // State management
  const [selectedDateRange, setSelectedDateRange] = useState<DateRangeType>('last_30_days');
  const [customDateRange, setCustomDateRange] = useState<{ start: Date | null; end: Date | null }>({
    start: null,
    end: null,
  });
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('pdf');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Custom hook for analytics data
  const {
    analyticsData,
    isLoading,
    error,
    refreshData,
    exportData,
  } = useAnalyticsData({
    dateRange: selectedDateRange,
    customDateRange: customDateRange,
    includeTrends: true,
    includePredictions: false,
  });

  // Handle date range change
  const handleDateRangeChange = useCallback((range: DateRangeType, custom?: { start: Date | null; end: Date | null }) => {
    setSelectedDateRange(range);
    if (custom) {
      setCustomDateRange(custom);
    }
    setLastRefresh(new Date());
  }, []);

  // Handle export
  const handleExport = useCallback(async (format: ExportFormat) => {
    setIsExporting(true);
    try {
      await exportData(format, {
        dateRange: selectedDateRange,
        customDateRange: customDateRange,
        includeTrends: true,
        includePredictions: false,
      });
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setIsExporting(false);
    }
  }, [exportData, selectedDateRange, customDateRange]);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    await refreshData();
    setLastRefresh(new Date());
  }, [refreshData]);

  // Get system health status
  const getSystemHealthStatus = () => {
    if (!analyticsData) return { status: 'unknown', color: 'text-gray-600', icon: Activity };
    
    const systemUtilization = analyticsData.system_utilization;
    if (systemUtilization.length === 0) return { status: 'no data', color: 'text-gray-600', icon: Activity };
    
    // Check for critical system issues
    const criticalMetrics = systemUtilization.filter(metric => 
      metric.value > (metric.threshold_critical || 90)
    );
    
    if (criticalMetrics.length > 0) {
      return { status: 'critical issues', color: 'text-red-600', icon: AlertTriangle };
    }
    
    const warningMetrics = systemUtilization.filter(metric => 
      metric.value > (metric.threshold_warning || 80)
    );
    
    if (warningMetrics.length > 0) {
      return { status: 'warnings', color: 'text-yellow-600', icon: AlertTriangle };
    }
    
    return { status: 'healthy', color: 'text-green-600', icon: CheckCircle };
  };

  const systemHealth = getSystemHealthStatus();
  const SystemHealthIcon = systemHealth.icon;

  return (
    <DashboardLayout>
      <div className={`space-y-6 ${className || ''}`}>
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
            <p className="text-muted-foreground">
              Comprehensive analytics and data visualization for detection performance, user engagement, and system utilization
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleRefresh}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <ExportButton
              onExport={handleExport}
              isLoading={isExporting}
              availableFormats={['pdf', 'csv', 'excel']}
              defaultFormat={exportFormat}
            />
          </div>
        </div>

        {/* Date Range Selector */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Date Range Selection
            </CardTitle>
            <CardDescription>
              Select the time period for analytics data analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DateRangeSelector
              selectedRange={selectedDateRange}
              customDateRange={customDateRange}
              onRangeChange={handleDateRangeChange}
              presets={[
                { label: 'Last 7 Days', value: 'last_7_days' },
                { label: 'Last 30 Days', value: 'last_30_days' },
                { label: 'Last 90 Days', value: 'last_90_days' },
                { label: 'Last Year', value: 'last_year' },
                { label: 'Custom Range', value: 'custom' },
              ]}
            />
          </CardContent>
        </Card>

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {error}
              <Button 
                variant="outline" 
                size="sm" 
                className="ml-2"
                onClick={handleRefresh}
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Quick Stats Overview */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Detection Accuracy
              </CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData?.detection_performance.length 
                  ? `${analyticsData.detection_performance
                      .filter(m => m.metric_name === 'accuracy_rate')
                      .reduce((acc, m) => acc + Number(m.value), 0) / 
                      analyticsData.detection_performance.filter(m => m.metric_name === 'accuracy_rate').length || 0
                    .toFixed(1)}%`
                  : 'N/A'
                }
              </div>
              <p className="text-xs text-muted-foreground">
                Average over selected period
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Active Users
              </CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData?.user_engagement.length 
                  ? new Set(analyticsData.user_engagement.map(m => m.user_id)).size
                  : '0'
                }
              </div>
              <p className="text-xs text-muted-foreground">
                Unique users in period
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                System Health
              </CardTitle>
              <SystemHealthIcon className={`h-4 w-4 ${systemHealth.color}`} />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${systemHealth.color}`}>
                {systemHealth.status === 'healthy' ? 'Healthy' : 
                 systemHealth.status === 'warnings' ? 'Warning' : 
                 systemHealth.status === 'critical issues' ? 'Critical' : 'Unknown'}
              </div>
              <p className="text-xs text-muted-foreground">
                {systemHealth.status}
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Data Points
              </CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {analyticsData?.total_records.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-muted-foreground">
                Total records analyzed
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Analytics Charts */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Performance Trends Chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Detection Performance Trends
              </CardTitle>
              <CardDescription>
                Success rates, processing times, and accuracy metrics over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PerformanceTrendsChart
                data={analyticsData?.detection_performance || []}
                isLoading={isLoading}
                error={error}
                onRefresh={handleRefresh}
              />
            </CardContent>
          </Card>

          {/* User Engagement Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                User Engagement
              </CardTitle>
              <CardDescription>
                Active users, analysis volume, and feature usage
              </CardDescription>
            </CardHeader>
            <CardContent>
              <UserEngagementChart
                data={analyticsData?.user_engagement || []}
                isLoading={isLoading}
                error={error}
                onRefresh={handleRefresh}
              />
            </CardContent>
          </Card>

          {/* System Utilization Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                System Utilization
              </CardTitle>
              <CardDescription>
                Resource usage, processing capacity, and performance benchmarks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SystemUtilizationChart
                data={analyticsData?.system_utilization || []}
                isLoading={isLoading}
                error={error}
                onRefresh={handleRefresh}
              />
            </CardContent>
          </Card>
        </div>

        {/* Analytics Insights */}
        {analyticsData?.insights && analyticsData.insights.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Analytics Insights
              </CardTitle>
              <CardDescription>
                Key insights and recommendations based on the analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analyticsData.insights.map((insight) => (
                  <div key={insight.insight_id} className="p-4 border rounded-lg">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-semibold text-sm mb-1">{insight.title}</h4>
                        <p className="text-sm text-muted-foreground mb-2">{insight.description}</p>
                        {insight.recommended_actions.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium text-muted-foreground">Recommended Actions:</p>
                            <ul className="text-xs text-muted-foreground list-disc list-inside">
                              {insight.recommended_actions.map((action, index) => (
                                <li key={index}>{action}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 ml-4">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          insight.severity === 'critical' ? 'bg-red-100 text-red-800' :
                          insight.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {insight.severity}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {(Number(insight.confidence) * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Data Classification and Export Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Data Information
            </CardTitle>
            <CardDescription>
              Information about the current analytics data and export options
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Data Classification</h4>
                <p className="text-sm text-muted-foreground">
                  {analyticsData?.data_classification || 'Unknown'}
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Last Updated</h4>
                <p className="text-sm text-muted-foreground">
                  {lastRefresh.toLocaleString()}
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Export Formats</h4>
                <p className="text-sm text-muted-foreground">
                  {analyticsData?.export_formats?.join(', ') || 'PDF, CSV, Excel'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

