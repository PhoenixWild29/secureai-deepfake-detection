"use client"

import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
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
  RadialBarChart,
  RadialBar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { 
  Server, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Activity, 
  RefreshCw,
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  Zap,
  Thermometer,
  Gauge
} from 'lucide-react';
import { analyticsService, type SystemUtilizationMetric } from '@/services/analyticsService';

interface SystemUtilizationChartProps {
  data: SystemUtilizationMetric[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

type ChartType = 'line' | 'bar' | 'area' | 'radial' | 'pie';
type ResourceFilter = 'all' | 'cpu' | 'memory' | 'disk' | 'network' | 'gpu';
type TimeGrouping = 'minute' | 'hour' | 'day' | 'week';

export default function SystemUtilizationChart({ 
  data, 
  isLoading = false, 
  error = null, 
  onRefresh,
  className 
}: SystemUtilizationChartProps) {
  const [chartType, setChartType] = useState<ChartType>('line');
  const [resourceFilter, setResourceFilter] = useState<ResourceFilter>('all');
  const [timeGrouping, setTimeGrouping] = useState<TimeGrouping>('hour');
  const [showThresholds, setShowThresholds] = useState(true);

  // Process and aggregate data
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Filter by resource type
    let filteredData = data;
    if (resourceFilter !== 'all') {
      filteredData = data.filter(item => 
        item.resource_type.toLowerCase().includes(resourceFilter)
      );
    }

    // Group by time period
    const groupedData = filteredData.reduce((acc, item) => {
      const timestamp = new Date(item.timestamp);
      let key: string;

      switch (timeGrouping) {
        case 'minute':
          key = `${timestamp.getHours()}:${timestamp.getMinutes().toString().padStart(2, '0')}`;
          break;
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
        default:
          key = timestamp.toISOString().split('T')[0];
      }

      if (!acc[key]) {
        acc[key] = {
          timestamp: key,
          cpu_usage: 0,
          memory_usage: 0,
          disk_usage: 0,
          network_usage: 0,
          gpu_usage: 0,
          count: 0,
          cpu_threshold_warning: 80,
          cpu_threshold_critical: 90,
          memory_threshold_warning: 85,
          memory_threshold_critical: 95,
          disk_threshold_warning: 90,
          disk_threshold_critical: 95,
        };
      }

      // Aggregate by resource type
      const resourceType = item.resource_type.toLowerCase();
      if (resourceType.includes('cpu')) {
        acc[key].cpu_usage = item.value;
        acc[key].cpu_threshold_warning = item.threshold_warning || 80;
        acc[key].cpu_threshold_critical = item.threshold_critical || 90;
      } else if (resourceType.includes('memory') || resourceType.includes('ram')) {
        acc[key].memory_usage = item.value;
        acc[key].memory_threshold_warning = item.threshold_warning || 85;
        acc[key].memory_threshold_critical = item.threshold_critical || 95;
      } else if (resourceType.includes('disk') || resourceType.includes('storage')) {
        acc[key].disk_usage = item.value;
        acc[key].disk_threshold_warning = item.threshold_warning || 90;
        acc[key].disk_threshold_critical = item.threshold_critical || 95;
      } else if (resourceType.includes('network') || resourceType.includes('bandwidth')) {
        acc[key].network_usage = item.value;
      } else if (resourceType.includes('gpu')) {
        acc[key].gpu_usage = item.value;
      }

      acc[key].count += 1;
      return acc;
    }, {} as Record<string, any>);

    return Object.values(groupedData)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [data, resourceFilter, timeGrouping]);

  // Calculate system health metrics
  const systemHealth = useMemo(() => {
    if (!data || data.length === 0) return null;

    const latestData = processedData[processedData.length - 1];
    if (!latestData) return null;

    const metrics = [
      { name: 'CPU', value: latestData.cpu_usage, warning: latestData.cpu_threshold_warning, critical: latestData.cpu_threshold_critical },
      { name: 'Memory', value: latestData.memory_usage, warning: latestData.memory_threshold_warning, critical: latestData.memory_threshold_critical },
      { name: 'Disk', value: latestData.disk_usage, warning: latestData.disk_threshold_warning, critical: latestData.disk_threshold_critical },
    ];

    const criticalCount = metrics.filter(m => m.value > m.critical).length;
    const warningCount = metrics.filter(m => m.value > m.warning && m.value <= m.critical).length;
    const healthyCount = metrics.filter(m => m.value <= m.warning).length;

    let overallStatus: 'healthy' | 'warning' | 'critical' = 'healthy';
    if (criticalCount > 0) overallStatus = 'critical';
    else if (warningCount > 0) overallStatus = 'warning';

    const avgUtilization = metrics.reduce((sum, m) => sum + m.value, 0) / metrics.length;

    return {
      overallStatus,
      criticalCount,
      warningCount,
      healthyCount,
      avgUtilization,
      metrics,
    };
  }, [data, processedData]);

  // Chart colors
  const colors = {
    cpu_usage: '#ef4444',
    memory_usage: '#3b82f6',
    disk_usage: '#10b981',
    network_usage: '#f59e0b',
    gpu_usage: '#8b5cf6',
  };

  const statusColors = {
    healthy: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
  };

  // Render chart based on type
  const renderChart = () => {
    if (processedData.length === 0) {
      return (
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          <div className="text-center">
            <Server className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No system utilization data available</p>
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
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  `${value.toFixed(1)}%`,
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              <Line type="monotone" dataKey="cpu_usage" stroke={colors.cpu_usage} strokeWidth={2} />
              <Line type="monotone" dataKey="memory_usage" stroke={colors.memory_usage} strokeWidth={2} />
              <Line type="monotone" dataKey="disk_usage" stroke={colors.disk_usage} strokeWidth={2} />
              <Line type="monotone" dataKey="network_usage" stroke={colors.network_usage} strokeWidth={2} />
              <Line type="monotone" dataKey="gpu_usage" stroke={colors.gpu_usage} strokeWidth={2} />
              {showThresholds && (
                <>
                  <Line type="monotone" dataKey="cpu_threshold_warning" stroke={colors.cpu_usage} strokeDasharray="5 5" strokeWidth={1} />
                  <Line type="monotone" dataKey="cpu_threshold_critical" stroke={colors.cpu_usage} strokeDasharray="10 5" strokeWidth={1} />
                </>
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
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  `${value.toFixed(1)}%`,
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              <Bar dataKey="cpu_usage" fill={colors.cpu_usage} />
              <Bar dataKey="memory_usage" fill={colors.memory_usage} />
              <Bar dataKey="disk_usage" fill={colors.disk_usage} />
              <Bar dataKey="network_usage" fill={colors.network_usage} />
              <Bar dataKey="gpu_usage" fill={colors.gpu_usage} />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis domain={[0, 100]} />
              <Tooltip 
                formatter={(value: number, name: string) => [
                  `${value.toFixed(1)}%`,
                  name.replace('_', ' ').toUpperCase()
                ]}
              />
              <Legend />
              <Area type="monotone" dataKey="cpu_usage" stackId="1" stroke={colors.cpu_usage} fill={colors.cpu_usage} fillOpacity={0.6} />
              <Area type="monotone" dataKey="memory_usage" stackId="1" stroke={colors.memory_usage} fill={colors.memory_usage} fillOpacity={0.6} />
              <Area type="monotone" dataKey="disk_usage" stackId="1" stroke={colors.disk_usage} fill={colors.disk_usage} fillOpacity={0.6} />
              <Area type="monotone" dataKey="network_usage" stackId="1" stroke={colors.network_usage} fill={colors.network_usage} fillOpacity={0.6} />
              <Area type="monotone" dataKey="gpu_usage" stackId="1" stroke={colors.gpu_usage} fill={colors.gpu_usage} fillOpacity={0.6} />
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'radial':
        const radialData = systemHealth?.metrics.map(metric => ({
          name: metric.name,
          value: metric.value,
          fill: metric.value > metric.critical ? statusColors.critical : 
                metric.value > metric.warning ? statusColors.warning : 
                statusColors.healthy,
        })) || [];

        return (
          <ResponsiveContainer width="100%" height={400}>
            <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="80%" data={radialData}>
              <RadialBar dataKey="value" cornerRadius={10} fill="#8884d8" />
              <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, 'Usage']} />
              <Legend />
            </RadialBarChart>
          </ResponsiveContainer>
        );

      case 'pie':
        const pieData = systemHealth?.metrics.map(metric => ({
          name: metric.name,
          value: metric.value,
          fill: metric.value > metric.critical ? statusColors.critical : 
                metric.value > metric.warning ? statusColors.warning : 
                statusColors.healthy,
        })) || [];

        return (
          <ResponsiveContainer width="100%" height={400}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, 'Usage']} />
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
              { type: 'radial', icon: Gauge, label: 'Radial' },
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
          <span className="text-sm font-medium">Resource:</span>
          <select
            value={resourceFilter}
            onChange={(e) => setResourceFilter(e.target.value as ResourceFilter)}
            className="px-3 py-1 border rounded-md text-sm"
          >
            <option value="all">All Resources</option>
            <option value="cpu">CPU</option>
            <option value="memory">Memory</option>
            <option value="disk">Disk</option>
            <option value="network">Network</option>
            <option value="gpu">GPU</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Time Grouping:</span>
          <select
            value={timeGrouping}
            onChange={(e) => setTimeGrouping(e.target.value as TimeGrouping)}
            className="px-3 py-1 border rounded-md text-sm"
          >
            <option value="minute">Minute</option>
            <option value="hour">Hourly</option>
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showThresholds}
              onChange={(e) => setShowThresholds(e.target.checked)}
              className="rounded"
            />
            Show Thresholds
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

      {/* System Health Overview */}
      {systemHealth && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Overall Status</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge 
                    variant={systemHealth.overallStatus === 'healthy' ? 'default' : 
                             systemHealth.overallStatus === 'warning' ? 'secondary' : 'destructive'}
                    className="text-xs"
                  >
                    {systemHealth.overallStatus.toUpperCase()}
                  </Badge>
                </div>
              </div>
              <Server className={`h-5 w-5 ${
                systemHealth.overallStatus === 'healthy' ? 'text-green-600' :
                systemHealth.overallStatus === 'warning' ? 'text-yellow-600' : 'text-red-600'
              }`} />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Utilization</p>
                <p className="text-lg font-semibold">{systemHealth.avgUtilization.toFixed(1)}%</p>
              </div>
              <Gauge className="h-5 w-5 text-blue-600" />
            </div>
            <Progress 
              value={systemHealth.avgUtilization} 
              className="mt-2"
              style={{
                backgroundColor: systemHealth.avgUtilization > 80 ? '#ef4444' : 
                                systemHealth.avgUtilization > 60 ? '#f59e0b' : '#10b981'
              }}
            />
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Critical Issues</p>
                <p className="text-lg font-semibold text-red-600">{systemHealth.criticalCount}</p>
              </div>
              <AlertTriangle className="h-5 w-5 text-red-600" />
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Warnings</p>
                <p className="text-lg font-semibold text-yellow-600">{systemHealth.warningCount}</p>
              </div>
              <TrendingUp className="h-5 w-5 text-yellow-600" />
            </div>
          </Card>
        </div>
      )}

      {/* Resource Utilization Details */}
      {systemHealth && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Resource Utilization Details</CardTitle>
            <CardDescription>Current utilization levels and thresholds</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {systemHealth.metrics.map((metric) => (
                <div key={metric.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {metric.name === 'CPU' && <Cpu className="h-4 w-4 text-red-600" />}
                      {metric.name === 'Memory' && <HardDrive className="h-4 w-4 text-blue-600" />}
                      {metric.name === 'Disk' && <HardDrive className="h-4 w-4 text-green-600" />}
                      <span className="font-medium">{metric.name}</span>
                      <Badge 
                        variant={metric.value > metric.critical ? 'destructive' : 
                                 metric.value > metric.warning ? 'secondary' : 'default'}
                        className="text-xs"
                      >
                        {metric.value > metric.critical ? 'Critical' : 
                         metric.value > metric.warning ? 'Warning' : 'Healthy'}
                      </Badge>
                    </div>
                    <span className="text-sm font-medium">{metric.value.toFixed(1)}%</span>
                  </div>
                  <Progress 
                    value={metric.value} 
                    className="h-2"
                    style={{
                      backgroundColor: metric.value > metric.critical ? '#ef4444' : 
                                      metric.value > metric.warning ? '#f59e0b' : '#10b981'
                    }}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Warning: {metric.warning}%</span>
                    <span>Critical: {metric.critical}%</span>
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
              <span className="font-medium">Error loading system utilization data</span>
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
            <p className="text-muted-foreground">Loading system utilization data...</p>
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
            <Server className="h-4 w-4 text-blue-600" />
            <span>System monitoring active</span>
          </div>
          <div className="flex items-center gap-1">
            <Thermometer className="h-4 w-4 text-purple-600" />
            <span>Avg: {systemHealth?.avgUtilization.toFixed(1)}% utilization</span>
          </div>
        </div>
      )}
    </div>
  );
}
