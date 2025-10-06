"use client"

import React from 'react';
import { Clock, CheckCircle, XCircle, AlertCircle, Eye, Download, ExternalLink } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { AnalysisSummary } from '@/services/dashboardApi';
import { dashboardApiUtils } from '@/services/dashboardApi';
import { useAnalysisStatusUpdates } from '@/hooks/useWebSocketUpdates';

interface AnalysisSummaryListProps {
  analyses: AnalysisSummary[];
  isLoading?: boolean;
  error?: string | null;
  onViewDetails?: (analysisId: string) => void;
  onDownloadResults?: (analysisId: string) => void;
  onRefresh?: () => void;
  className?: string;
}

export function AnalysisSummaryList({
  analyses,
  isLoading = false,
  error = null,
  onViewDetails,
  onDownloadResults,
  onRefresh,
  className,
}: AnalysisSummaryListProps) {
  // Handle empty state
  if (!isLoading && !error && analyses.length === 0) {
    return (
      <Card className={cn("w-full", className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5" />
            Recent Analyses
          </CardTitle>
          <CardDescription>
            Your recent deepfake detection analyses will appear here
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Eye className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold text-muted-foreground mb-2">
              No analyses yet
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Upload your first video to start detecting deepfakes
            </p>
            <Button onClick={onRefresh} variant="outline">
              <Clock className="h-4 w-4 mr-2" />
              Refresh
            </Button>
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
            <Eye className="h-5 w-5" />
            Recent Analyses
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
            <h3 className="text-lg font-semibold text-red-600 mb-2">
              Failed to load analyses
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {error}
            </p>
            <Button onClick={onRefresh} variant="outline">
              <Clock className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Recent Analyses
            </CardTitle>
            <CardDescription>
              Last {analyses.length} completed analyses
            </CardDescription>
          </div>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
            >
              <Clock className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <AnalysisSummarySkeleton key={index} />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {analyses.map((analysis) => (
              <AnalysisSummaryItem
                key={analysis.id}
                analysis={analysis}
                onViewDetails={onViewDetails}
                onDownloadResults={onDownloadResults}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface AnalysisSummaryItemProps {
  analysis: AnalysisSummary;
  onViewDetails?: (analysisId: string) => void;
  onDownloadResults?: (analysisId: string) => void;
}

function AnalysisSummaryItem({
  analysis,
  onViewDetails,
  onDownloadResults,
}: AnalysisSummaryItemProps) {
  const { status: realtimeStatus, progress } = useAnalysisStatusUpdates(analysis.id);
  
  // Use real-time status if available, otherwise use stored status
  const currentStatus = realtimeStatus || analysis.status;
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-blue-600 animate-spin" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    return dashboardApiUtils.getStatusColor(status);
  };

  const getResultBadge = () => {
    if (!analysis.result || currentStatus !== 'completed') {
      return null;
    }

    const { is_fake, confidence_score } = analysis.result;
    const badgeColor = dashboardApiUtils.getResultBadgeColor(is_fake, confidence_score);
    
    return (
      <Badge className={cn("text-xs font-medium", badgeColor)}>
        {is_fake ? 'Deepfake Detected' : 'Authentic'}
        <span className="ml-1">
          ({dashboardApiUtils.formatConfidenceScore(confidence_score)})
        </span>
      </Badge>
    );
  };

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="flex-shrink-0">
          {getStatusIcon(currentStatus)}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-medium text-sm truncate">
              {analysis.filename}
            </h4>
            <Badge className={cn("text-xs", getStatusColor(currentStatus))}>
              {currentStatus}
            </Badge>
          </div>
          
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>{dashboardApiUtils.formatTimestamp(analysis.timestamp)}</span>
            {analysis.result && (
              <span>
                {dashboardApiUtils.formatProcessingTime(analysis.result.processing_time_seconds)}
              </span>
            )}
            {currentStatus === 'processing' && progress > 0 && (
              <span>{Math.round(progress * 100)}% complete</span>
            )}
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-2 flex-shrink-0">
        {getResultBadge()}
        
        <div className="flex items-center gap-1">
          {onViewDetails && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewDetails(analysis.id)}
              className="h-8 w-8 p-0"
            >
              <Eye className="h-4 w-4" />
            </Button>
          )}
          
          {onDownloadResults && analysis.result && currentStatus === 'completed' && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDownloadResults(analysis.id)}
              className="h-8 w-8 p-0"
            >
              <Download className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function AnalysisSummarySkeleton() {
  return (
    <div className="flex items-center gap-4 p-4 border rounded-lg">
      <div className="h-4 w-4 bg-muted rounded animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
        <div className="h-3 bg-muted rounded animate-pulse w-1/2" />
      </div>
      <div className="flex gap-2">
        <div className="h-6 w-16 bg-muted rounded animate-pulse" />
        <div className="h-8 w-8 bg-muted rounded animate-pulse" />
      </div>
    </div>
  );
}

export default AnalysisSummaryList;
