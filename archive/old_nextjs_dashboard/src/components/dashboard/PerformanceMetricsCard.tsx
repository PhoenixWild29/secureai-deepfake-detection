"use client"

import React from 'react';
import { BarChart3, TrendingUp, Clock, CheckCircle, XCircle, Activity, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { PerformanceMetrics } from '@/services/dashboardApi';
import { dashboardApiUtils } from '@/services/dashboardApi';

interface PerformanceMetricsCardProps {
  metrics: PerformanceMetrics | null;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

export function PerformanceMetricsCard({
  metrics,
  isLoading = false,
  error = null,
  onRefresh,
  className,
}: PerformanceMetricsCardProps) {
  // Handle loading state
  if (isLoading) {
    return (
      <Card className={cn("w-full", className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Performance Metrics
          </CardTitle>
          <CardDescription>
            Key performance indicators and statistics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <MetricSkeleton key={index} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Handle error state
  if (error) {
    return (
      <Card className={cn("w-full", className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Performance Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
            <h3 className="text-lg font-semibold text-red-600 mb-2">
              Failed to load metrics
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {error}
            </p>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Try again
              </button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Handle empty state
  if (!metrics) {
    return (
      <Card className={cn("w-full", className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Performance Metrics
          </CardTitle>
          <CardDescription>
            Key performance indicators and statistics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <BarChart3 className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold text-muted-foreground mb-2">
              No data available
            </h3>
            <p className="text-sm text-muted-foreground">
              Performance metrics will appear here once you start analyzing videos
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    total_analyses,
    fake_detected,
    authentic_detected,
    success_rate,
    avg_processing_time,
    last_updated,
  } = metrics;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Performance Metrics
            </CardTitle>
            <CardDescription>
              Key performance indicators and statistics
            </CardDescription>
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Last updated: {dashboardApiUtils.formatTimestamp(last_updated)}
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricItem
            title="Total Analyses"
            value={total_analyses.toLocaleString()}
            icon={<Activity className="h-4 w-4" />}
            description="Videos processed"
            trend="neutral"
          />
          
          <MetricItem
            title="Success Rate"
            value={`${success_rate.toFixed(1)}%`}
            icon={<CheckCircle className="h-4 w-4" />}
            description="Successful detections"
            trend={success_rate >= 90 ? "positive" : success_rate >= 70 ? "neutral" : "negative"}
          />
          
          <MetricItem
            title="Deepfakes Detected"
            value={fake_detected.toLocaleString()}
            icon={<XCircle className="h-4 w-4" />}
            description="Manipulated videos"
            trend="neutral"
          />
          
          <MetricItem
            title="Avg Processing Time"
            value={dashboardApiUtils.formatProcessingTime(avg_processing_time)}
            icon={<Clock className="h-4 w-4" />}
            description="Per analysis"
            trend={avg_processing_time < 60 ? "positive" : avg_processing_time < 300 ? "neutral" : "negative"}
          />
        </div>
        
        {/* Additional metrics row */}
        <div className="mt-6 pt-6 border-t">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {authentic_detected.toLocaleString()}
              </div>
              <div className="text-sm text-muted-foreground">
                Authentic Videos
              </div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {fake_detected > 0 ? ((fake_detected / total_analyses) * 100).toFixed(1) : '0.0'}%
              </div>
              <div className="text-sm text-muted-foreground">
                Deepfake Rate
              </div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {total_analyses > 0 ? (avg_processing_time * total_analyses / 3600).toFixed(1) : '0.0'}h
              </div>
              <div className="text-sm text-muted-foreground">
                Total Processing Time
              </div>
            </div>
          </div>
        </div>
        
        {/* Performance insights */}
        {total_analyses > 0 && (
          <div className="mt-6 pt-6 border-t">
            <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Performance Insights
            </h4>
            <div className="space-y-2">
              {success_rate >= 95 && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Excellent detection accuracy ({success_rate.toFixed(1)}%)
                </div>
              )}
              
              {avg_processing_time < 60 && (
                <div className="flex items-center gap-2 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Fast processing time ({dashboardApiUtils.formatProcessingTime(avg_processing_time)})
                </div>
              )}
              
              {fake_detected > 0 && (
                <div className="flex items-center gap-2 text-sm text-orange-600">
                  <AlertTriangle className="h-4 w-4" />
                  {fake_detected} deepfake{fake_detected !== 1 ? 's' : ''} detected
                </div>
              )}
              
              {total_analyses >= 100 && (
                <div className="flex items-center gap-2 text-sm text-blue-600">
                  <Activity className="h-4 w-4" />
                  High volume processing ({total_analyses} analyses)
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface MetricItemProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  description: string;
  trend: 'positive' | 'negative' | 'neutral';
}

function MetricItem({ title, value, icon, description, trend }: MetricItemProps) {
  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'positive':
        return 'text-green-600';
      case 'negative':
        return 'text-red-600';
      default:
        return 'text-blue-600';
    }
  };

  return (
    <div className="flex flex-col items-center text-center p-4 bg-muted/50 rounded-lg">
      <div className={cn("mb-2", getTrendColor(trend))}>
        {icon}
      </div>
      <div className="text-2xl font-bold mb-1">
        {value}
      </div>
      <div className="text-sm font-medium text-foreground mb-1">
        {title}
      </div>
      <div className="text-xs text-muted-foreground">
        {description}
      </div>
    </div>
  );
}

function MetricSkeleton() {
  return (
    <div className="flex flex-col items-center text-center p-4 bg-muted/50 rounded-lg">
      <div className="h-4 w-4 bg-muted rounded animate-pulse mb-2" />
      <div className="h-8 w-16 bg-muted rounded animate-pulse mb-1" />
      <div className="h-4 w-20 bg-muted rounded animate-pulse mb-1" />
      <div className="h-3 w-16 bg-muted rounded animate-pulse" />
    </div>
  );
}

export default PerformanceMetricsCard;
