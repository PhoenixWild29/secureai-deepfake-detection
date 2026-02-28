"use client"

import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Download, 
  FileText, 
  FileSpreadsheet, 
  FileImage, 
  FileJson,
  ChevronDown,
  Check,
  AlertTriangle,
  RefreshCw,
  Loader2,
  ExternalLink,
  Copy,
  Share2
} from 'lucide-react';
import { analyticsService, type ExportFormat } from '@/services/analyticsService';

interface ExportButtonProps {
  onExport: (format: ExportFormat) => Promise<any>;
  isLoading?: boolean;
  availableFormats?: ExportFormat[];
  defaultFormat?: ExportFormat;
  className?: string;
  disabled?: boolean;
  showProgress?: boolean;
}

interface ExportStatus {
  status: 'idle' | 'exporting' | 'completed' | 'error';
  progress?: number;
  message?: string;
  downloadUrl?: string;
  error?: string;
}

export default function ExportButton({
  onExport,
  isLoading = false,
  availableFormats = ['pdf', 'csv', 'excel'],
  defaultFormat = 'pdf',
  className,
  disabled = false,
  showProgress = true,
}: ExportButtonProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [exportStatus, setExportStatus] = useState<ExportStatus>({ status: 'idle' });
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>(defaultFormat);

  // Format configurations
  const formatConfig = {
    pdf: {
      label: 'PDF Report',
      icon: FileText,
      description: 'Formatted report with charts and tables',
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200',
    },
    csv: {
      label: 'CSV Data',
      icon: FileSpreadsheet,
      description: 'Raw data in comma-separated format',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
    },
    excel: {
      label: 'Excel Workbook',
      icon: FileSpreadsheet,
      description: 'Interactive spreadsheet with charts',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
    },
    json: {
      label: 'JSON Data',
      icon: FileJson,
      description: 'Structured data in JSON format',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
    },
  };

  // Handle export
  const handleExport = useCallback(async (format: ExportFormat) => {
    if (disabled || isLoading) return;

    setExportStatus({ status: 'exporting', progress: 0, message: 'Preparing export...' });
    setIsDropdownOpen(false);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setExportStatus(prev => {
          if (prev.progress && prev.progress < 90) {
            return {
              ...prev,
              progress: prev.progress + Math.random() * 10,
              message: prev.progress < 30 ? 'Processing data...' :
                       prev.progress < 60 ? 'Generating report...' :
                       prev.progress < 90 ? 'Finalizing export...' : 'Almost done...'
            };
          }
          return prev;
        });
      }, 200);

      const result = await onExport(format);
      
      clearInterval(progressInterval);
      
      setExportStatus({
        status: 'completed',
        progress: 100,
        message: 'Export completed successfully!',
        downloadUrl: result.download_url || result.url,
      });

      // Auto-hide success message after 5 seconds
      setTimeout(() => {
        setExportStatus({ status: 'idle' });
      }, 5000);

    } catch (error) {
      setExportStatus({
        status: 'error',
        message: 'Export failed',
        error: error instanceof Error ? error.message : 'Unknown error occurred',
      });
    }
  }, [onExport, disabled, isLoading]);

  // Handle format selection
  const handleFormatSelect = useCallback((format: ExportFormat) => {
    setSelectedFormat(format);
    handleExport(format);
  }, [handleExport]);

  // Copy download link
  const copyDownloadLink = useCallback(() => {
    if (exportStatus.downloadUrl) {
      navigator.clipboard.writeText(exportStatus.downloadUrl);
      // You could add a toast notification here
    }
  }, [exportStatus.downloadUrl]);

  // Share export
  const shareExport = useCallback(() => {
    if (exportStatus.downloadUrl && navigator.share) {
      navigator.share({
        title: 'Analytics Export',
        text: 'Check out this analytics export',
        url: exportStatus.downloadUrl,
      });
    }
  }, [exportStatus.downloadUrl]);

  const SelectedFormatIcon = formatConfig[selectedFormat]?.icon || FileText;

  return (
    <div className={`relative ${className || ''}`}>
      {/* Main Export Button */}
      <div className="flex items-center gap-2">
        <Button
          onClick={() => handleExport(selectedFormat)}
          disabled={disabled || isLoading || exportStatus.status === 'exporting'}
          className="flex items-center gap-2"
        >
          {exportStatus.status === 'exporting' ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {exportStatus.status === 'exporting' ? 'Exporting...' : 'Export'}
        </Button>

        {/* Format Dropdown */}
        <div className="relative">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            disabled={disabled || isLoading}
            className="flex items-center gap-1"
          >
            <SelectedFormatIcon className="h-4 w-4" />
            <ChevronDown className="h-3 w-3" />
          </Button>

          {isDropdownOpen && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-white border rounded-lg shadow-lg z-50">
              <div className="p-2">
                <p className="text-xs font-medium text-muted-foreground px-2 py-1">Export Format</p>
                {availableFormats.map((format) => {
                  const config = formatConfig[format];
                  const Icon = config.icon;
                  const isSelected = format === selectedFormat;
                  
                  return (
                    <button
                      key={format}
                      onClick={() => handleFormatSelect(format)}
                      disabled={disabled || isLoading}
                      className={`w-full flex items-center gap-3 p-2 rounded-md hover:bg-muted transition-colors ${
                        isSelected ? 'bg-muted' : ''
                      }`}
                    >
                      <Icon className={`h-4 w-4 ${config.color}`} />
                      <div className="flex-1 text-left">
                        <p className="text-sm font-medium">{config.label}</p>
                        <p className="text-xs text-muted-foreground">{config.description}</p>
                      </div>
                      {isSelected && <Check className="h-4 w-4 text-green-600" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Export Progress */}
      {showProgress && exportStatus.status === 'exporting' && (
        <div className="absolute top-full left-0 right-0 mt-2 p-3 bg-white border rounded-lg shadow-lg z-40">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Exporting {formatConfig[selectedFormat]?.label}</span>
              <span className="text-muted-foreground">
                {exportStatus.progress?.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${exportStatus.progress || 0}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{exportStatus.message}</p>
          </div>
        </div>
      )}

      {/* Export Success */}
      {exportStatus.status === 'completed' && (
        <div className="absolute top-full left-0 right-0 mt-2 p-3 bg-green-50 border border-green-200 rounded-lg shadow-lg z-40">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-green-800">
              <Check className="h-4 w-4" />
              <span className="font-medium text-sm">Export Completed!</span>
            </div>
            <p className="text-xs text-green-600">{exportStatus.message}</p>
            {exportStatus.downloadUrl && (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => window.open(exportStatus.downloadUrl, '_blank')}
                  className="h-6 px-2 text-xs"
                >
                  <ExternalLink className="h-3 w-3 mr-1" />
                  Download
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={copyDownloadLink}
                  className="h-6 px-2 text-xs"
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Copy Link
                </Button>
                {navigator.share && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={shareExport}
                    className="h-6 px-2 text-xs"
                  >
                    <Share2 className="h-3 w-3 mr-1" />
                    Share
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Export Error */}
      {exportStatus.status === 'error' && (
        <div className="absolute top-full left-0 right-0 mt-2 p-3 bg-red-50 border border-red-200 rounded-lg shadow-lg z-40">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-medium text-sm">Export Failed</span>
            </div>
            <p className="text-xs text-red-600">{exportStatus.error}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleExport(selectedFormat)}
              className="h-6 px-2 text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* Click outside to close dropdown */}
      {isDropdownOpen && (
        <div 
          className="fixed inset-0 z-30" 
          onClick={() => setIsDropdownOpen(false)}
        />
      )}
    </div>
  );
}

// Additional utility components for export functionality

export function ExportStatusIndicator({ status, className }: { status: ExportStatus; className?: string }) {
  if (status.status === 'idle') return null;

  return (
    <div className={`p-2 rounded-lg ${className || ''}`}>
      {status.status === 'exporting' && (
        <div className="flex items-center gap-2 text-blue-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Exporting...</span>
        </div>
      )}
      
      {status.status === 'completed' && (
        <div className="flex items-center gap-2 text-green-600">
          <Check className="h-4 w-4" />
          <span className="text-sm">Export completed</span>
        </div>
      )}
      
      {status.status === 'error' && (
        <div className="flex items-center gap-2 text-red-600">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm">Export failed</span>
        </div>
      )}
    </div>
  );
}

export function ExportFormatBadge({ format, className }: { format: ExportFormat; className?: string }) {
  const config = formatConfig[format];
  const Icon = config.icon;

  return (
    <Badge variant="outline" className={`${config.color} ${config.borderColor} ${className || ''}`}>
      <Icon className="h-3 w-3 mr-1" />
      {config.label}
    </Badge>
  );
}
