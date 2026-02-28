"use client"

import React, { useState, useEffect, useCallback } from 'react';
import { DashboardLayout } from '@/components/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Shield, 
  Activity, 
  TrendingUp, 
  AlertTriangle, 
  Users, 
  Database,
  BarChart3,
  Bell,
  Eye,
  FileText,
  Settings,
  Server,
  Upload,
  Clock,
  CheckCircle,
  RefreshCw,
  Zap
} from 'lucide-react';

// Import existing components
import { AnalysisSummaryList } from '@/components/dashboard/AnalysisSummaryList';
import { PerformanceMetricsCard } from '@/components/dashboard/PerformanceMetricsCard';
import { EmbeddedUpload } from '@/components/dashboard/EmbeddedUpload';
import { QuickAccessNavigation } from '@/components/dashboard/QuickAccessNavigation';

// Import hooks and services
import { useAnalysisData } from '@/hooks/useAnalysisData';
import { useWebSocketUpdates } from '@/hooks/useWebSocketUpdates';
import { useSystemStatusMonitoring } from '@/hooks/useWebSocketUpdates';
import { dashboardApi } from '@/services/dashboardApi';
import type { AnalysisSummary, PerformanceMetrics } from '@/services/dashboardApi';

interface DashboardOverviewProps {
  className?: string;
}

export default function DashboardOverview({ className }: DashboardOverviewProps) {
  // State management
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisSummary[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Custom hooks for data fetching
  const {
    analyses,
    metrics,
    isLoading: dataLoading,
    error: dataError,
    refreshData,
  } = useAnalysisData();

  // WebSocket for real-time updates
  const { isConnected: wsConnected, connectionStatus } = useWebSocketUpdates({
    onAnalysisUpdate: (update) => {
      // Update analysis status in real-time
      setRecentAnalyses(prev => 
        prev.map(analysis => 
          analysis.id === update.analysis_id 
            ? { ...analysis, status: update.status as any }
            : analysis
        )
      );
    },
  });

  // System status monitoring
  const { systemStatus, overallStatus } = useSystemStatusMonitoring();

  // Load initial data
  useEffect(() => {
    const loadDashboardData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch recent analyses and performance metrics in parallel
        const [analysesResponse, metricsResponse] = await Promise.all([
          dashboardApi.getAnalysisHistory(10),
          dashboardApi.getPerformanceMetrics(),
        ]);

        if (analysesResponse.success && analysesResponse.data) {
          setRecentAnalyses(analysesResponse.data);
        }

        if (metricsResponse.success && metricsResponse.data) {
          setPerformanceMetrics(metricsResponse.data);
        }

        setLastRefresh(new Date());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  // Handle refresh
  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    await refreshData();
    setLastRefresh(new Date());
    setIsLoading(false);
  }, [refreshData]);

  // Handle analysis view details
  const handleViewDetails = useCallback((analysisId: string) => {
    // Navigate to analysis details page
    window.location.href = `/analysis/${analysisId}`;
  }, []);

  // Handle download results
  const handleDownloadResults = useCallback((analysisId: string) => {
    // Implement download functionality
    console.log('Download results for analysis:', analysisId);
  }, []);

  // Get system health status
  const getSystemHealthStatus = () => {
    if (!wsConnected) return { status: 'disconnected', color: 'text-red-600', icon: AlertTriangle };
    
    switch (overallStatus) {
      case 'healthy':
        return { status: 'All systems operational', color: 'text-green-600', icon: CheckCircle };
      case 'warning':
        return { status: 'Minor issues detected', color: 'text-yellow-600', icon: AlertTriangle };
      case 'error':
        return { status: 'System issues detected', color: 'text-red-600', icon: AlertTriangle };
      default:
        return { status: 'Status unknown', color: 'text-gray-600', icon: Activity };
    }
  };

  const systemHealth = getSystemHealthStatus();
  const SystemHealthIcon = systemHealth.icon;

  return (
    <DashboardLayout>
      <div className={`space-y-6 ${className || ''}`}>
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard Overview</h1>
            <p className="text-muted-foreground">
              Comprehensive system overview and recent analysis summaries
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
            <Button variant="outline" size="sm">
              <BarChart3 className="h-4 w-4 mr-2" />
              View Analytics
            </Button>
            <Button size="sm">
              <Shield className="h-4 w-4 mr-2" />
              New Analysis
            </Button>
          </div>
        </div>

        {/* WebSocket Connection Status */}
        {!wsConnected && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Real-time updates are currently unavailable. Status: {connectionStatus}
            </AlertDescription>
          </Alert>
        )}

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
                Total Analyses
              </CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {performanceMetrics?.total_analyses.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-muted-foreground">
                Videos processed
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Deepfakes Detected
              </CardTitle>
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {performanceMetrics?.fake_detected.toLocaleString() || '0'}
              </div>
              <p className="text-xs text-muted-foreground">
                Manipulated videos
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Success Rate
              </CardTitle>
              <CheckCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {performanceMetrics?.success_rate.toFixed(1) || '0.0'}%
              </div>
              <p className="text-xs text-muted-foreground">
                Detection accuracy
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
                {wsConnected ? '98.5%' : 'Offline'}
              </div>
              <p className="text-xs text-muted-foreground">
                {systemHealth.status}
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Recent Analysis Summaries */}
          <div className="lg:col-span-2">
            <AnalysisSummaryList
              analyses={recentAnalyses}
              isLoading={isLoading || dataLoading}
              error={error || dataError}
              onViewDetails={handleViewDetails}
              onDownloadResults={handleDownloadResults}
              onRefresh={handleRefresh}
            />
          </div>

          {/* Quick Access and Upload */}
          <div className="space-y-6">
            {/* Embedded Upload */}
            <EmbeddedUpload 
              onUploadSuccess={(videoId, filename) => {
                // Handle successful upload
                console.log('Upload successful:', videoId, filename);
                handleRefresh();
              }}
              onUploadError={(error) => {
                console.error('Upload error:', error);
                setError(`Upload failed: ${error}`);
              }}
            />

            {/* Quick Access Navigation */}
            <QuickAccessNavigation 
              onNavigate={(path) => {
                window.location.href = path;
              }}
            />
          </div>
        </div>

        {/* Performance Metrics */}
        <PerformanceMetricsCard
          metrics={performanceMetrics}
          isLoading={isLoading || dataLoading}
          error={error || dataError}
          onRefresh={handleRefresh}
        />

        {/* System Status and Additional Info */}
        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                User Management
              </CardTitle>
              <CardDescription>
                Manage user access and permissions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Active Users</span>
                  <span className="text-sm font-medium">24</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Admin Users</span>
                  <span className="text-sm font-medium">3</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Security Officers</span>
                  <span className="text-sm font-medium">8</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Data Storage
              </CardTitle>
              <CardDescription>
                Storage usage and blockchain status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Storage Used</span>
                  <span className="text-sm font-medium">2.4 TB</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Blockchain Records</span>
                  <span className="text-sm font-medium">15,432</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Last Sync</span>
                  <span className="text-sm font-medium">
                    {lastRefresh.toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Performance
              </CardTitle>
              <CardDescription>
                System performance metrics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Avg Response Time</span>
                  <span className="text-sm font-medium">45ms</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Uptime</span>
                  <span className="text-sm font-medium">99.9%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Processing Speed</span>
                  <span className="text-sm font-medium">
                    {performanceMetrics?.avg_processing_time 
                      ? `${performanceMetrics.avg_processing_time.toFixed(1)}s` 
                      : 'N/A'
                    }
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Last Updated Footer */}
        <div className="flex items-center justify-between text-sm text-muted-foreground pt-4 border-t">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Last updated: {lastRefresh.toLocaleString()}
          </div>
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-1 ${wsConnected ? 'text-green-600' : 'text-red-600'}`}>
              <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {wsConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
