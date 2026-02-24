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
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Clock, 
  Target, 
  RefreshCw,
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react';
import { analyticsService, type DetectionPerformanceMetric } from '@/services/analyticsService';

interface PerformanceTrendsChartProps {
  data: DetectionPerformanceMetric[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

type ChartType = 'line' | 'bar' | 'area' | 'pie';
type MetricFilter = 'all' | 'accuracy_rate' | 'processing_time' | 'success_rate' | 'precision' | 'recall' | 'f1_score';

export default function PerformanceTrendsChart({ 
  data, 
  isLoading = false, 
  error = null, 
  onRefresh,
  className 
}: PerformanceTrendsChartProps) {
  const [chartType, setChartType] = useState<ChartType>('line');
  const [metricFilter, setMetricFilter] = useState<MetricFilter>('all');
  const [timeRange, setTimeRange] = useState<'hour' | 'day' | 'week' | 'month'>('day');

  // Process and filter data
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Filter by metric type
    let filteredData = data;
    if (metricFilter !== 'all') {
      filteredData = data.filter(item => item.metric_name === metricFilter);
    }

    // Group by timestamp and aggregate
    const groupedData = filteredData.reduce((acc, item) => {
      const timestamp = new Date(item.timestamp);
      const key = timeRange === 'hour' 
        ? `${timestamp.getHours()}:00`
        : timeRange === 'day'
        ? timestamp.toISOString().split('T')[0]
        : timeRange === 'week'
        ? `Week ${Math.ceil(timestamp.getDate() / 7)}`
        : `${timestamp.getMonth() + 1}/${timestamp.getFullYear()}`;

      if (!acc[key]) {
        acc[key] = {
          timestamp: key,
          accuracy_rate: 0,
          processing_time: 0,
          success_rate: 0,
          precision: 0,
          recall: 0,
          f1_score: 0,
          count: 0,
        };
      }

      acc[key][item.metric_name] = item.value;
      acc[key].count += 1;

      return acc;
    }, {} as Record<string, any>);

    return Object.values(groupedData).sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [data, metricFilter, timeRange]);

  // Calculate summary statistics
  const summaryStats = useMemo(() => {
    if (!data || data.length === 0) return null;

    const metrics = ['accuracy_rate', 'processing_time', 'success_rate', 'precision', 'recall', 'f1_score'];
    const stats: Record<string, { avg: number; min: number; max: number; trend: 'up' | 'down' | 'stable' }> = {};

    metrics.forEach(metric => {
      const values = data
        .filter(item => item.metric_name === metric)
        .map(item => item.value);

      if (values.length > 0) {
        const avg = values.reduce((sum, val) => sum + val, 0) / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        
        // Calculate trend (simple comparison of first half vs second half)
        const mid = Math.floor(values.length / 2);
        const firstHalfAvg = values.slice(0, mid).reduce((sum, val) => sum + val, 0) / mid;
        const secondHalfAvg = values.slice(mid).reduce((sum, val) => sum + val, 0) / (values.length - mid);
        
        let trend: 'up' | 'down' | 'stable' = 'stable';
        if (secondHalfAvg > firstHalfAvg * 1.05) trend = 'up';
        else if (secondHalfAvg < firstHalfAvg * 0.95) trend = 'down';

        stats[metric] = { avg, min, max, trend };
      }
    });

    return stats;
  }, [data]);

  // Chart colors
  const colors = {
    accuracy_rate: '#10b981',
    processing_time: '#f59e0b',
    success_rate: '#3b82f6',
    precision: '#8b5cf6',
    recall: '#ef4444',
    f1_score: '#06b6d4',
  };

  // Render chart based on type
  const renderChart = () => {
    if (processedData.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          <div className="text-center">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No data available for the selected time range</p>
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
                  analyticsService.formatMetricValue(value, 'percent'),
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              {metricFilter === 'all' ? (
                <>
                  <Line type="monotone" dataKey="accuracy_rate" stroke={colors.accuracy_rate} strokeWidth={2} />
                  <Line type="monotone" dataKey="success_rate" stroke={colors.success_rate} strokeWidth={2} />
                  <Line type="monotone" dataKey="precision" stroke={colors.precision} strokeWidth={2} />
                  <Line type="monotone" dataKey="recall" stroke={colors.recall} strokeWidth={2} />
                  <Line type="monotone" dataKey="f1_score" stroke={colors.f1_score} strokeWidth={2} />
                </>
              ) : (
                <Line 
                  type="monotone" 
                  dataKey={metricFilter} 
                  stroke={colors[metricFilter as keyof typeof colors]} 
                  strokeWidth={2} 
                />
              )}
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
                  analyticsService.formatMetricValue(value, 'percent'),
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              {metricFilter === 'all' ? (
                <>
                  <Bar dataKey="accuracy_rate" fill={colors.accuracy_rate} />
                  <Bar dataKey="success_rate" fill={colors.success_rate} />
                  <Bar dataKey="precision" fill={colors.precision} />
                  <Bar dataKey="recall" fill={colors.recall} />
                  <Bar dataKey="f1_score" fill={colors.f1_score} />
                </>
              ) : (
                <Bar dataKey={metricFilter} fill={colors[metricFilter as keyof typeof colors]} />
              )}
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
                  analyticsService.formatMetricValue(value, 'percent'),
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              {metricFilter === 'all' ? (
                <>
                  <Area type="monotone" dataKey="accuracy_rate" stackId="1" stroke={colors.accuracy_rate} fill={colors.accuracy_rate} fillOpacity={0.6} />
                  <Area type="monotone" dataKey="success_rate" stackId="1" stroke={colors.success_rate} fill={colors.success_rate} fillOpacity={0.6} />
                  <Area type="monotone" dataKey="precision" stackId="1" stroke={colors.precision} fill={colors.precision} fillOpacity={0.6} />
                  <Area type="monotone" dataKey="recall" stackId="1" stroke={colors.recall} fill={colors.recall} fillOpacity={0.6} />
                  <Area type="monotone" dataKey="f1_score" stackId="1" stroke={colors.f1_score} fill={colors.f1_score} fillOpacity={0.6} />
                </>
              ) : (
                <Area 
                  type="monotone" 
                  dataKey={metricFilter} 
                  stroke={colors[metricFilter as keyof typeof colors]} 
                  fill={colors[metricFilter as keyof typeof colors]} 
                  fillOpacity={0.6} 
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'pie':
        const pieData = Object.entries(colors).map(([metric, color]) => ({
          name: metric.replace('_', ' ').toUpperCase(),
          value: summaryStats?.[metric]?.avg || 0,
          color,
        }));

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
              <Tooltip formatter={(value: number) => analyticsService.formatMetricValue(value, 'percent')} />
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
          <span className="text-sm font-medium">Metric:</span>
          <select
            value={metricFilter}
            onChange={(e) => setMetricFilter(e.target.value as MetricFilter)}
            className="px-3 py-1 border rounded-md text-sm"
          >
            <option value="all">All Metrics</option>
            <option value="accuracy_rate">Accuracy Rate</option>
            <option value="processing_time">Processing Time</option>
            <option value="success_rate">Success Rate</option>
            <option value="precision">Precision</option>
            <option value="recall">Recall</option>
            <option value="f1_score">F1 Score</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Time Range:</span>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-3 py-1 border rounded-md text-sm"
          >
            <option value="hour">Hourly</option>
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
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

      {/* Summary Statistics */}
      {summaryStats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Object.entries(summaryStats).map(([metric, stats]) => (
            <Card key={metric} className="p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground capitalize">
                    {metric.replace('_', ' ')}
                  </p>
                  <p className="text-lg font-semibold">
                    {analyticsService.formatMetricValue(stats.avg, 'percent')}
                  </p>
                </div>
                <div className="flex items-center">
                  {stats.trend === 'up' && <TrendingUp className="h-4 w-4 text-green-600" />}
                  {stats.trend === 'down' && <TrendingDown className="h-4 w-4 text-red-600" />}
                  {stats.trend === 'stable' && <Activity className="h-4 w-4 text-blue-600" />}
                </div>
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                Min: {analyticsService.formatMetricValue(stats.min, 'percent')} | 
                Max: {analyticsService.formatMetricValue(stats.max, 'percent')}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-medium">Error loading performance data</span>
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
            <p className="text-muted-foreground">Loading performance data...</p>
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
            <span>{processedData.length} data points</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4 text-blue-600" />
            <span>Updated {analyticsService.getDataFreshnessStatus(5).message.toLowerCase()}</span>
          </div>
          <div className="flex items-center gap-1">
            <Target className="h-4 w-4 text-purple-600" />
            <span>Accuracy: {summaryStats?.accuracy_rate?.avg.toFixed(1)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
