"use client"

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import DashboardLayoutWrapper from '@/components/DashboardLayout';
import ComprehensiveProgressTracker from '@/components/ComprehensiveProgressTracker';
import { ResultUpdate, ConnectionStatus } from '@/types/progress';

export default function ProgressTrackerPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('sessionId');
  
  const [isConnected, setIsConnected] = useState(false);
  const [lastResult, setLastResult] = useState<ResultUpdate | null>(null);

  const handleComplete = (result: ResultUpdate) => {
    setLastResult(result);
    console.log('Analysis completed:', result);
    
    // Could redirect to results page or show success message
    // router.push(`/dashboard/results/${result.sessionId}`);
  };

  const handleError = (error: Error) => {
    console.error('Progress tracker error:', error);
    // Could show error notification
  };

  const handleConnectionChange = (status: ConnectionStatus) => {
    setIsConnected(status.status === 'connected');
    console.log('Connection status changed:', status);
  };

  return (
    <DashboardLayoutWrapper>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Analysis Progress
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-400">
              Monitor your deepfake detection analysis in real-time
            </p>
          </div>

          {/* Progress Tracker */}
          <ComprehensiveProgressTracker
            sessionId={sessionId || undefined}
            websocketConfig={{
              url: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/ws/progress',
              reconnectInterval: 3000,
              maxReconnectAttempts: 5,
              connectionTimeout: 10000,
              heartbeatInterval: 30000,
            }}
            debounceDelay={300}
            showFrameProgress={true}
            showStatistics={true}
            showTimeline={true}
            onComplete={handleComplete}
            onError={handleError}
            onConnectionChange={handleConnectionChange}
            className="mb-8"
          />

          {/* Additional Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Connection Status Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Connection Status
              </h3>
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`} />
                <span className="text-gray-700 dark:text-gray-300">
                  {isConnected ? 'Connected to server' : 'Disconnected from server'}
                </span>
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Real-time updates are {isConnected ? 'enabled' : 'disabled'}
              </p>
            </div>

            {/* Session Information Card */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Session Information
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Session ID:</span>
                  <span className="text-gray-900 dark:text-white font-mono text-sm">
                    {sessionId || 'Not provided'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Started:</span>
                  <span className="text-gray-900 dark:text-white">
                    {new Date().toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Status:</span>
                  <span className="text-gray-900 dark:text-white">
                    {isConnected ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Results Summary */}
          {lastResult && (
            <div className="mt-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-green-800 dark:text-green-200 mb-4">
                Analysis Complete
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                    {Math.round(lastResult.result.confidence * 100)}%
                  </div>
                  <div className="text-sm text-green-600 dark:text-green-400">
                    Confidence Score
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                    {lastResult.result.isDeepfake ? 'Deepfake' : 'Authentic'}
                  </div>
                  <div className="text-sm text-green-600 dark:text-green-400">
                    Detection Result
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                    {Math.round(lastResult.processingTime / 1000)}s
                  </div>
                  <div className="text-sm text-green-600 dark:text-green-400">
                    Processing Time
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Help Section */}
          <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-4">
              Need Help?
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2">
                  Understanding the Progress
                </h4>
                <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                  <li>• Upload: Video file is being uploaded to the server</li>
                  <li>• Frame Extraction: Frames are being extracted from the video</li>
                  <li>• Feature Extraction: AI features are being extracted</li>
                  <li>• AI Analysis: Deepfake detection models are running</li>
                  <li>• Blockchain Verification: Results are being verified on blockchain</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-blue-700 dark:text-blue-300 mb-2">
                  Troubleshooting
                </h4>
                <ul className="text-sm text-blue-600 dark:text-blue-400 space-y-1">
                  <li>• If connection is lost, the system will automatically reconnect</li>
                  <li>• Processing time varies based on video length and complexity</li>
                  <li>• Frame-level progress shows individual frame processing status</li>
                  <li>• Contact support if analysis fails or takes unusually long</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayoutWrapper>
  );
}
