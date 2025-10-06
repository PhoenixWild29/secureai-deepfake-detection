"use client"

import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import DashboardLayoutWrapper from '@/components/DashboardLayout';
import ProcessingStageVisualization from '@/components/ProcessingStageVisualization';
import { AnalysisStatus } from '@/types/processingStage';

export default function AnalysisDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const analysisId = params.id as string;
  
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleStatusChange = (status: AnalysisStatus) => {
    setAnalysisStatus(status);
    console.log('Analysis status updated:', status);
  };

  const handleError = (error: Error) => {
    setError(error.message);
    console.error('Analysis error:', error);
  };

  useEffect(() => {
    if (analysisId) {
      setIsLoading(false);
    }
  }, [analysisId]);

  if (isLoading) {
    return (
      <DashboardLayoutWrapper>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">Loading analysis details...</p>
            </div>
          </div>
        </div>
      </DashboardLayoutWrapper>
    );
  }

  if (error) {
    return (
      <DashboardLayoutWrapper>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
                Error Loading Analysis
              </h3>
              <p className="text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        </div>
      </DashboardLayoutWrapper>
    );
  }

  return (
    <DashboardLayoutWrapper>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Page Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Analysis Details
                </h1>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                  Analysis ID: {analysisId}
                </p>
              </div>
              
              {/* Analysis Status Badge */}
              {analysisStatus && (
                <div className={`px-4 py-2 rounded-full text-sm font-medium ${
                  analysisStatus.status === 'completed' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : analysisStatus.status === 'processing'
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                    : analysisStatus.status === 'failed'
                    ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                }`}>
                  {analysisStatus.status.charAt(0).toUpperCase() + analysisStatus.status.slice(1)}
                </div>
              )}
            </div>
          </div>

          {/* Processing Stage Visualization */}
          <ProcessingStageVisualization
            analysisId={analysisId}
            updateInterval={2000}
            showResourceDetails={true}
            showWorkerAllocation={true}
            showGPUUtilization={true}
            showQueueStatus={true}
            onStatusChange={handleStatusChange}
            onError={handleError}
            className="mb-8"
          />

          {/* Additional Analysis Information */}
          {analysisStatus && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Analysis Summary */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Analysis Summary
                </h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Started:</span>
                    <span className="text-gray-900 dark:text-white">
                      {new Date(analysisStatus.startTime).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Last Update:</span>
                    <span className="text-gray-900 dark:text-white">
                      {new Date(analysisStatus.lastUpdate).toLocaleString()}
                    </span>
                  </div>
                  {analysisStatus.estimatedCompletion && (
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Est. Completion:</span>
                      <span className="text-gray-900 dark:text-white">
                        {new Date(analysisStatus.estimatedCompletion).toLocaleString()}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Current Stage:</span>
                    <span className="text-gray-900 dark:text-white capitalize">
                      {analysisStatus.currentStage.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Overall Progress:</span>
                    <span className="text-gray-900 dark:text-white font-semibold">
                      {Math.round(analysisStatus.overallProgress)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Resource Overview */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Resource Overview
                </h3>
                {analysisStatus.resourceMetrics && (
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">CPU Usage:</span>
                      <span className="text-gray-900 dark:text-white">
                        {Math.round(analysisStatus.resourceMetrics.systemCpuUsage)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Memory Usage:</span>
                      <span className="text-gray-900 dark:text-white">
                        {Math.round(analysisStatus.resourceMetrics.systemMemoryUsagePercentage)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Disk Usage:</span>
                      <span className="text-gray-900 dark:text-white">
                        {Math.round(analysisStatus.resourceMetrics.diskUsagePercentage)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Network I/O:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.resourceMetrics.networkIO.toFixed(1)} MB/s
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Worker and GPU Summary */}
          {analysisStatus && (analysisStatus.workers.length > 0 || analysisStatus.gpus.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Workers Summary */}
              {analysisStatus.workers.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Workers Summary
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Total Workers:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.workers.length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Active Workers:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.workers.filter(w => w.status === 'busy' || w.status === 'active').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Idle Workers:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.workers.filter(w => w.status === 'idle').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Total Tasks Completed:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.workers.reduce((sum, w) => sum + w.tasksCompleted, 0)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* GPU Summary */}
              {analysisStatus.gpus.length > 0 && (
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    GPU Summary
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Total GPUs:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.gpus.length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Active GPUs:</span>
                      <span className="text-gray-900 dark:text-white">
                        {analysisStatus.gpus.filter(g => g.status === 'busy' || g.status === 'active').length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Average Utilization:</span>
                      <span className="text-gray-900 dark:text-white">
                        {Math.round(analysisStatus.gpus.reduce((sum, g) => sum + g.utilization, 0) / analysisStatus.gpus.length)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Average Temperature:</span>
                      <span className="text-gray-900 dark:text-white">
                        {Math.round(analysisStatus.gpus.reduce((sum, g) => sum + g.temperature, 0) / analysisStatus.gpus.length)}°C
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Queue Information */}
          {analysisStatus && analysisStatus.queue && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Queue Information
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {analysisStatus.queue.position}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Position in Queue
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {analysisStatus.queue.totalItems}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Total Items
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {Math.round(analysisStatus.queue.estimatedWaitTime / 60)}m
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Est. Wait Time
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 dark:text-white capitalize">
                    {analysisStatus.queue.priority}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Priority
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Help Section */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-4">
              Understanding the Analysis Process
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2">
                  Processing Stages
                </h4>
                <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                  <li>• <strong>Upload:</strong> Video file is uploaded to the server</li>
                  <li>• <strong>Frame Extraction:</strong> Frames are extracted from the video</li>
                  <li>• <strong>Feature Extraction:</strong> AI features are extracted from frames</li>
                  <li>• <strong>AI Analysis:</strong> Deepfake detection models analyze the content</li>
                  <li>• <strong>Result Processing:</strong> Results are aggregated and processed</li>
                  <li>• <strong>Blockchain Verification:</strong> Results are verified on blockchain</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2">
                  Resource Monitoring
                </h4>
                <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                  <li>• <strong>Workers:</strong> Celery workers processing your analysis</li>
                  <li>• <strong>GPUs:</strong> GPU utilization for AI model inference</li>
                  <li>• <strong>Queue:</strong> Your position in the processing queue</li>
                  <li>• <strong>System Resources:</strong> Overall system performance metrics</li>
                  <li>• <strong>Real-time Updates:</strong> All data updates automatically</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayoutWrapper>
  );
}
