"use client"

import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  BarChart,
  Bar,
  Area,
  AreaChart,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  Users, 
  Activity, 
  Clock, 
  Eye, 
  MousePointer,
  RefreshCw,
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  UserCheck,
  Zap
} from 'lucide-react';
import { analyticsService, type UserEngagementMetric } from '@/services/analyticsService';

interface UserEngagementChartProps {
  data: UserEngagementMetric[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

type ChartType = 'line' | 'bar' | 'area' | 'scatter' | 'pie';
type MetricFilter = 'all' | 'active_users' | 'session_duration' | 'page_views' | 'feature_usage' | 'analysis_volume';
type TimeGrouping = 'hour' | 'day' | 'week' | 'month';

export default function UserEngagementChart({ 
  data, 
  isLoading = false, 
  error = null, 
  onRefresh,
  className 
}: UserEngagementChartProps) {
  const [chartType, setChartType] = useState<ChartType>('line');
  const [metricFilter, setMetricFilter] = useState<MetricFilter>('all');
  const [timeGrouping, setTimeGrouping] = useState<TimeGrouping>('day');
  const [showUniqueUsers, setShowUniqueUsers] = useState(true);

  // Process and aggregate data
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Group by time period
    const groupedData = data.reduce((acc, item) => {
      const timestamp = new Date(item.timestamp);
      let key: string;

      switch (timeGrouping) {
        case 'hour':
          key = `${timestamp.getHours()}:00`;
          break;
        case 'day':
          key = timestamp.toISOString().split('T')[0];
          break;
        case 'week':
          const weekStart = new Date(timestamp);
          weekStart.setDate(timestamp.getDate() - timestamp.getDay());
          key = weekStart.toISOString().split('T')[0];
          break;
        case 'month':
          key = `${timestamp.getMonth() + 1}/${timestamp.getFullYear()}`;
          break;
        default:
          key = timestamp.toISOString().split('T')[0];
      }

      if (!acc[key]) {
        acc[key] = {
          timestamp: key,
          active_users: new Set(),
          session_duration: 0,
          page_views: 0,
          feature_usage: new Map(),
          analysis_volume: 0,
          total_sessions: 0,
          avg_session_duration: 0,
        };
      }

      // Aggregate metrics
      if (item.user_id) {
        acc[key].active_users.add(item.user_id);
      }

      if (item.duration_seconds) {
        acc[key].session_duration += item.duration_seconds;
        acc[key].total_sessions += 1;
      }

      if (item.metric_name === 'page_view') {
        acc[key].page_views += item.value;
      }

      if (item.feature_used) {
        const current = acc[key].feature_usage.get(item.feature_used) || 0;
        acc[key].feature_usage.set(item.feature_used, current + item.value);
      }

      if (item.metric_name === 'analysis_count') {
        acc[key].analysis_volume += item.value;
      }

      return acc;
    }, {} as Record<string, any>);

    // Convert to array and calculate averages
    return Object.values(groupedData)
      .map((item: any) => ({
        ...item,
        active_users: showUniqueUsers ? item.active_users.size : item.active_users.size,
        avg_session_duration: item.total_sessions > 0 ? item.session_duration / item.total_sessions : 0,
        feature_usage_count: Array.from(item.feature_usage.values()).reduce((sum: number, val: number) => sum + val, 0),
      }))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [data, timeGrouping, showUniqueUsers]);

  // Calculate engagement metrics
  const engagementMetrics = useMemo(() => {
    if (!data || data.length === 0) return null;

    const uniqueUsers = new Set(data.map(item => item.user_id)).size;
    const totalSessions = data.filter(item => item.session_id).length;
    const totalDuration = data.reduce((sum, item) => sum + (item.duration_seconds || 0), 0);
    const avgSessionDuration = totalSessions > 0 ? totalDuration / totalSessions : 0;
    const totalPageViews = data.filter(item => item.metric_name === 'page_view').reduce((sum, item) => sum + item.value, 0);
    const totalAnalyses = data.filter(item => item.metric_name === 'analysis_count').reduce((sum, item) => sum + item.value, 0);

    // Feature usage analysis
    const featureUsage = data.reduce((acc, item) => {
      if (item.feature_used) {
        acc[item.feature_used] = (acc[item.feature_used] || 0) + item.value;
      }
      return acc;
    }, {} as Record<string, number>);

    const topFeatures = Object.entries(featureUsage)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);

    return {
      uniqueUsers,
      totalSessions,
      avgSessionDuration,
      totalPageViews,
      totalAnalyses,
      topFeatures,
      engagementScore: Math.min(100, (uniqueUsers * 0.3 + totalSessions * 0.2 + avgSessionDuration * 0.3 + totalPageViews * 0.2)),
    };
  }, [data]);

  // Chart colors
  const colors = {
    active_users: '#10b981',
    session_duration: '#f59e0b',
    page_views: '#3b82f6',
    feature_usage: '#8b5cf6',
    analysis_volume: '#ef4444',
  };

  // Render chart based on type
  const renderChart = () => {
    if (processedData.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          <div className="text-center">
            <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No user engagement data available</p>
          </div>
        </div>
      );
    }

    const commonProps = {
      data: processedData,
      margin: { top: 20, right: 30, left: 20, bottom: 5 },
    };

    switch (chartType) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              <Line type="monotone" dataKey="active_users" stroke={colors.active_users} strokeWidth={2} />
              <Line type="monotone" dataKey="page_views" stroke={colors.page_views} strokeWidth={2} />
              <Line type="monotone" dataKey="analysis_volume" stroke={colors.analysis_volume} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              <Bar dataKey="active_users" fill={colors.active_users} />
              <Bar dataKey="page_views" fill={colors.page_views} />
              <Bar dataKey="analysis_volume" fill={colors.analysis_volume} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  typeof value === 'number' ? value.toLocaleString() : value,
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              <Area type="monotone" dataKey="active_users" stackId="1" stroke={colors.active_users} fill={colors.active_users} fillOpacity={0.6} />
              <Area type="monotone" dataKey="page_views" stackId="1" stroke={colors.page_views} fill={colors.page_views} fillOpacity={0.6} />
              <Area type="monotone" dataKey="analysis_volume" stackId="1" stroke={colors.analysis_volume} fill={colors.analysis_volume} fillOpacity={0.6} />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <ScatterChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="active_users" name="Active Users" />
              <YAxis dataKey="analysis_volume" name="Analysis Volume" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Scatter dataKey="analysis_volume" fill={colors.analysis_volume} />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'pie':
        const pieData = engagementMetrics?.topFeatures.map(([feature, count], index) => ({
          name: feature.replace('_', ' ').toUpperCase(),
          value: count,
          color: Object.values(colors)[index % Object.values(colors).length],
        })) || [];

        return (
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => value.toLocaleString()} />
            </PieChart>
          </ResponsiveContainer>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`space-y-4 ${className || ''}`}>
      {/* Chart Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Chart Type:</span>
          <div className="flex gap-1">
            {[
              { type: 'line', icon: LineChartIcon, label: 'Line' },
              { type: 'bar', icon: BarChart3, label: 'Bar' },
              { type: 'area', icon: Activity, label: 'Area' },
              { type: 'scatter', icon: MousePointer, label: 'Scatter' },
              { type: 'pie', icon: PieChartIcon, label: 'Pie' },
            ].map(({ type, icon: Icon, label }) => (
              <Button
                key={type}
                variant={chartType === type ? 'default' : 'outline'}
                size="sm"
                onClick={() => setChartType(type as ChartType)}
                className="h-8 px-3"
              >
                <Icon className="h-4 w-4 mr-1" />
                {label}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Time Grouping:</span>
          <select
            value={timeGrouping}
            onChange={(e) => setTimeGrouping(e.target.value as TimeGrouping)}
            className="px-3 py-1 border rounded-md text-sm"
          >
            <option value="hour">Hourly</option>
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showUniqueUsers}
              onChange={(e) => setShowUniqueUsers(e.target.checked)}
              className="rounded"
            />
            Unique Users Only
          </label>
        </div>

        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
            className="h-8 px-3"
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        )}
      </div>

      {/* Engagement Summary */}
      {engagementMetrics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Unique Users</p>
                <p className="text-lg font-semibold">{engagementMetrics.uniqueUsers.toLocaleString()}</p>
              </div>
              <UserCheck className="h-4 w-4 text-blue-600" />
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Total Sessions</p>
                <p className="text-lg font-semibold">{engagementMetrics.totalSessions.toLocaleString()}</p>
              </div>
              <Activity className="h-4 w-4 text-green-600" />
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Avg Session</p>
                <p className="text-lg font-semibold">
                  {Math.floor(engagementMetrics.avgSessionDuration / 60)}m {Math.floor(engagementMetrics.avgSessionDuration % 60)}s
                </p>
              </div>
              <Clock className="h-4 w-4 text-orange-600" />
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Page Views</p>
                <p className="text-lg font-semibold">{engagementMetrics.totalPageViews.toLocaleString()}</p>
              </div>
              <Eye className="h-4 w-4 text-purple-600" />
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Analyses</p>
                <p className="text-lg font-semibold">{engagementMetrics.totalAnalyses.toLocaleString()}</p>
              </div>
              <Zap className="h-4 w-4 text-red-600" />
            </div>
          </Card>

          <Card className="p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Engagement Score</p>
                <p className="text-lg font-semibold">{engagementMetrics.engagementScore.toFixed(0)}%</p>
              </div>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </div>
          </Card>
        </div>
      )}

      {/* Top Features */}
      {engagementMetrics?.topFeatures && engagementMetrics.topFeatures.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top Features Used</CardTitle>
            <CardDescription>Most popular features by usage count</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {engagementMetrics.topFeatures.map(([feature, count], index) => (
                <div key={feature} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      #{index + 1}
                    </Badge>
                    <span className="text-sm font-medium capitalize">
                      {feature.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {count.toLocaleString()} uses
                    </span>
                    <div className="w-20 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ 
                          width: `${(count / engagementMetrics.topFeatures[0][1]) * 100}%` 
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-medium">Error loading user engagement data</span>
            </div>
            <p className="text-sm text-red-600 mt-1">{error}</p>
            {onRefresh && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                className="mt-2"
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                Retry
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 mx-auto mb-4 animate-spin text-muted-foreground" />
            <p className="text-muted-foreground">Loading user engagement data...</p>
          </div>
        </div>
      )}

      {/* Chart */}
      {!isLoading && !error && (
        <Card>
          <CardContent className="p-6">
            {renderChart()}
          </CardContent>
        </Card>
      )}

      {/* Data Quality Indicators */}
      {processedData.length > 0 && (
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <span>{processedData.length} time periods</span>
          </div>
          <div className="flex items-center gap-1">
            <Users className="h-4 w-4 text-blue-600" />
            <span>{engagementMetrics?.uniqueUsers || 0} unique users</span>
          </div>
          <div className="flex items-center gap-1">
            <Activity className="h-4 w-4 text-purple-600" />
            <span>{engagementMetrics?.totalSessions || 0} total sessions</span>
          </div>
        </div>
      )}
    </div>
  );
}
