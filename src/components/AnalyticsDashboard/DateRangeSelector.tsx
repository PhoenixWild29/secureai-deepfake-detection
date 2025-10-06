"use client"

import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Calendar, 
  Clock, 
  ChevronDown, 
  Check,
  RefreshCw,
  CalendarDays,
  CalendarRange,
  CalendarCheck
} from 'lucide-react';
import { analyticsService, type DateRangeType, type CustomDateRange } from '@/services/analyticsService';

interface DateRangePreset {
  label: string;
  value: DateRangeType;
  description?: string;
}

interface DateRangeSelectorProps {
  selectedRange: DateRangeType;
  customDateRange: CustomDateRange;
  onRangeChange: (range: DateRangeType, custom?: CustomDateRange) => void;
  presets?: DateRangePreset[];
  className?: string;
  disabled?: boolean;
}

export default function DateRangeSelector({
  selectedRange,
  customDateRange,
  onRangeChange,
  presets = [
    { label: 'Last 7 Days', value: 'last_7_days', description: 'Past week' },
    { label: 'Last 30 Days', value: 'last_30_days', description: 'Past month' },
    { label: 'Last 90 Days', value: 'last_90_days', description: 'Past quarter' },
    { label: 'Last Year', value: 'last_year', description: 'Past year' },
    { label: 'Custom Range', value: 'custom', description: 'Select specific dates' },
  ],
  className,
  disabled = false,
}: DateRangeSelectorProps) {
  const [isCustomPickerOpen, setIsCustomPickerOpen] = useState(false);
  const [tempCustomRange, setTempCustomRange] = useState<CustomDateRange>(customDateRange);

  // Handle preset selection
  const handlePresetSelect = useCallback((preset: DateRangePreset) => {
    if (preset.value === 'custom') {
      setIsCustomPickerOpen(true);
    } else {
      onRangeChange(preset.value);
    }
  }, [onRangeChange]);

  // Handle custom date range selection
  const handleCustomRangeSelect = useCallback(() => {
    if (tempCustomRange.start && tempCustomRange.end) {
      // Validate the custom range
      if (analyticsService.validateDateRange('custom', tempCustomRange)) {
        onRangeChange('custom', tempCustomRange);
        setIsCustomPickerOpen(false);
      } else {
        alert('Invalid date range. Please select a valid start and end date.');
      }
    }
  }, [tempCustomRange, onRangeChange]);

  // Handle custom date input changes
  const handleCustomDateChange = useCallback((field: 'start' | 'end', value: string) => {
    const date = value ? new Date(value) : null;
    setTempCustomRange(prev => ({
      ...prev,
      [field]: date,
    }));
  }, []);

  // Get current range display text
  const getCurrentRangeText = () => {
    if (selectedRange === 'custom' && customDateRange.start && customDateRange.end) {
      const start = customDateRange.start.toLocaleDateString();
      const end = customDateRange.end.toLocaleDateString();
      return `${start} - ${end}`;
    }
    
    const preset = presets.find(p => p.value === selectedRange);
    return preset?.label || 'Select Range';
  };

  // Get range description
  const getRangeDescription = () => {
    if (selectedRange === 'custom' && customDateRange.start && customDateRange.end) {
      const days = Math.ceil((customDateRange.end.getTime() - customDateRange.start.getTime()) / (1000 * 60 * 60 * 24));
      return `${days} days selected`;
    }
    
    const preset = presets.find(p => p.value === selectedRange);
    return preset?.description || '';
  };

  // Quick preset buttons for common ranges
  const quickPresets = [
    { label: 'Today', days: 0 },
    { label: 'Yesterday', days: 1 },
    { label: 'This Week', days: 7 },
    { label: 'This Month', days: 30 },
  ];

  const handleQuickPreset = useCallback((days: number) => {
    const end = new Date();
    const start = new Date();
    
    if (days === 0) {
      // Today - same start and end
      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
    } else {
      start.setDate(start.getDate() - days);
      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
    }

    onRangeChange('custom', { start, end });
  }, [onRangeChange]);

  return (
    <div className={`space-y-4 ${className || ''}`}>
      {/* Current Selection Display */}
      <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
        <div className="flex items-center gap-3">
          <Calendar className="h-5 w-5 text-muted-foreground" />
          <div>
            <p className="font-medium">{getCurrentRangeText()}</p>
            <p className="text-sm text-muted-foreground">{getRangeDescription()}</p>
          </div>
        </div>
        <Badge variant="outline" className="text-xs">
          {selectedRange.replace('_', ' ').toUpperCase()}
        </Badge>
      </div>

      {/* Quick Presets */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-muted-foreground">Quick Select</p>
        <div className="flex flex-wrap gap-2">
          {quickPresets.map((preset) => (
            <Button
              key={preset.label}
              variant="outline"
              size="sm"
              onClick={() => handleQuickPreset(preset.days)}
              disabled={disabled}
              className="h-8 px-3 text-xs"
            >
              <Clock className="h-3 w-3 mr-1" />
              {preset.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Preset Options */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-muted-foreground">Preset Ranges</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {presets.map((preset) => (
            <Button
              key={preset.value}
              variant={selectedRange === preset.value ? 'default' : 'outline'}
              onClick={() => handlePresetSelect(preset)}
              disabled={disabled}
              className="justify-start h-auto p-3"
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  {preset.value === 'custom' ? (
                    <CalendarRange className="h-4 w-4" />
                  ) : (
                    <CalendarDays className="h-4 w-4" />
                  )}
                  <div className="text-left">
                    <p className="font-medium">{preset.label}</p>
                    {preset.description && (
                      <p className="text-xs text-muted-foreground">{preset.description}</p>
                    )}
                  </div>
                </div>
                {selectedRange === preset.value && (
                  <Check className="h-4 w-4" />
                )}
              </div>
            </Button>
          ))}
        </div>
      </div>

      {/* Custom Date Range Picker */}
      {isCustomPickerOpen && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CalendarRange className="h-5 w-5" />
              Custom Date Range
            </CardTitle>
            <CardDescription>
              Select specific start and end dates for your analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Start Date</label>
                <input
                  type="date"
                  value={tempCustomRange.start?.toISOString().split('T')[0] || ''}
                  onChange={(e) => handleCustomDateChange('start', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  max={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">End Date</label>
                <input
                  type="date"
                  value={tempCustomRange.end?.toISOString().split('T')[0] || ''}
                  onChange={(e) => handleCustomDateChange('end', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  max={new Date().toISOString().split('T')[0]}
                  min={tempCustomRange.start?.toISOString().split('T')[0]}
                />
              </div>
            </div>

            {/* Date Range Validation */}
            {tempCustomRange.start && tempCustomRange.end && (
              <div className="p-3 bg-muted rounded-lg">
                <div className="flex items-center gap-2 text-sm">
                  <CalendarCheck className="h-4 w-4 text-green-600" />
                  <span>
                    Selected: {tempCustomRange.start.toLocaleDateString()} - {tempCustomRange.end.toLocaleDateString()}
                  </span>
                  <Badge variant="outline" className="text-xs">
                    {Math.ceil((tempCustomRange.end.getTime() - tempCustomRange.start.getTime()) / (1000 * 60 * 60 * 24))} days
                  </Badge>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setIsCustomPickerOpen(false)}
                disabled={disabled}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCustomRangeSelect}
                disabled={disabled || !tempCustomRange.start || !tempCustomRange.end}
              >
                <Check className="h-4 w-4 mr-1" />
                Apply Range
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Date Range Information */}
      <div className="p-3 bg-muted/30 rounded-lg">
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4 mt-0.5" />
          <div>
            <p className="font-medium">Date Range Guidelines</p>
            <ul className="mt-1 space-y-1 text-xs">
              <li>• Maximum range: 2 years</li>
              <li>• Minimum range: 1 day</li>
              <li>• Data availability may vary by time period</li>
              <li>• Custom ranges are stored for the session</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Recent Selections */}
      {customDateRange.start && customDateRange.end && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-green-800">
            <Check className="h-4 w-4" />
            <span className="font-medium">Custom range applied successfully</span>
          </div>
          <p className="text-xs text-green-600 mt-1">
            Analysis will include data from {customDateRange.start.toLocaleDateString()} to {customDateRange.end.toLocaleDateString()}
          </p>
        </div>
      )}
    </div>
  );
}
