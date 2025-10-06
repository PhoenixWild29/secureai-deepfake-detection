"use client"

import React, { useState, useCallback, useRef } from 'react';
import { Upload, FileVideo, AlertCircle, CheckCircle, X, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { dashboardApi } from '@/services/dashboardApi';

interface EmbeddedUploadProps {
  onUploadSuccess?: (videoId: string, filename: string) => void;
  onUploadError?: (error: string) => void;
  onAnalysisStarted?: (analysisId: string) => void;
  maxFileSize?: number; // in MB
  allowedFormats?: string[];
  className?: string;
}

interface UploadProgress {
  stage: 'uploading' | 'processing' | 'analyzing' | 'completed' | 'error';
  progress: number;
  message: string;
  videoId?: string;
  analysisId?: string;
}

export function EmbeddedUpload({
  onUploadSuccess,
  onUploadError,
  onAnalysisStarted,
  maxFileSize = 500, // 500MB default
  allowedFormats = ['mp4', 'avi', 'mov', 'mkv', 'webm'],
  className,
}: EmbeddedUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Validate file
  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > maxFileSize) {
      return `File size exceeds ${maxFileSize}MB limit`;
    }

    // Check file format
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (!extension || !allowedFormats.includes(extension)) {
      return `Unsupported file format. Allowed formats: ${allowedFormats.join(', ')}`;
    }

    return null;
  }, [maxFileSize, allowedFormats]);

  // Handle file upload
  const handleFileUpload = useCallback(async (file: File) => {
    // Validate file
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      onUploadError?.(validationError);
      return;
    }

    setError(null);
    setUploadedFile(file);

    try {
      // Start upload progress
      setUploadProgress({
        stage: 'uploading',
        progress: 0,
        message: 'Uploading video file...',
      });

      // Upload file
      const uploadResponse = await dashboardApi.uploadFile(file, {
        source: 'dashboard_upload',
        timestamp: new Date().toISOString(),
      });

      if (!uploadResponse.success || !uploadResponse.data) {
        throw new Error(uploadResponse.error || 'Upload failed');
      }

      const { video_id, filename } = uploadResponse.data;

      // Update progress
      setUploadProgress({
        stage: 'processing',
        progress: 50,
        message: 'Processing video...',
        videoId: video_id,
      });

      // Start analysis
      const analysisResponse = await dashboardApi.startAnalysis(video_id, filename);

      if (!analysisResponse.success || !analysisResponse.data) {
        throw new Error(analysisResponse.error || 'Failed to start analysis');
      }

      const { analysis_id } = analysisResponse.data;

      // Update progress
      setUploadProgress({
        stage: 'analyzing',
        progress: 75,
        message: 'Analysis in progress...',
        videoId: video_id,
        analysisId: analysis_id,
      });

      // Notify success
      onUploadSuccess?.(video_id, filename);
      onAnalysisStarted?.(analysis_id);

      // Complete progress
      setUploadProgress({
        stage: 'completed',
        progress: 100,
        message: 'Upload and analysis started successfully!',
        videoId: video_id,
        analysisId: analysis_id,
      });

      // Clear progress after delay
      setTimeout(() => {
        setUploadProgress(null);
        setUploadedFile(null);
      }, 3000);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
      setUploadProgress({
        stage: 'error',
        progress: 0,
        message: errorMessage,
      });
      onUploadError?.(errorMessage);

      // Clear error after delay
      setTimeout(() => {
        setError(null);
        setUploadProgress(null);
        setUploadedFile(null);
      }, 5000);
    }
  }, [validateFile, onUploadSuccess, onUploadError, onAnalysisStarted]);

  // Handle drag and drop
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  // Handle file input change
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  // Handle click to open file dialog
  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  // Clear upload
  const clearUpload = useCallback(() => {
    setUploadedFile(null);
    setUploadProgress(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Get stage icon
  const getStageIcon = (stage: UploadProgress['stage']) => {
    switch (stage) {
      case 'uploading':
      case 'processing':
      case 'analyzing':
        return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Upload className="h-4 w-4" />;
    }
  };

  // Get stage color
  const getStageColor = (stage: UploadProgress['stage']) => {
    switch (stage) {
      case 'completed':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      default:
        return 'text-blue-600';
    }
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Video
        </CardTitle>
        <CardDescription>
          Drag and drop or click to upload a video for deepfake analysis
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Upload Area */}
        <div
          className={cn(
            "relative border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer",
            isDragOver 
              ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20" 
              : "border-muted-foreground/25 hover:border-muted-foreground/50",
            uploadProgress && "pointer-events-none opacity-75"
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={allowedFormats.map(format => `.${format}`).join(',')}
            onChange={handleFileInputChange}
            className="hidden"
            disabled={!!uploadProgress}
          />

          {uploadProgress ? (
            <div className="space-y-4">
              <div className="flex items-center justify-center">
                {getStageIcon(uploadProgress.stage)}
              </div>
              <div className="space-y-2">
                <p className={`font-medium ${getStageColor(uploadProgress.stage)}`}>
                  {uploadProgress.message}
                </p>
                <Progress value={uploadProgress.progress} className="w-full" />
                {uploadProgress.stage === 'completed' && (
                  <div className="flex items-center justify-center gap-2">
                    <Badge variant="outline" className="text-green-600">
                      Video ID: {uploadProgress.videoId}
                    </Badge>
                    {uploadProgress.analysisId && (
                      <Badge variant="outline" className="text-blue-600">
                        Analysis ID: {uploadProgress.analysisId}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              {uploadProgress.stage === 'error' && (
                <Button variant="outline" size="sm" onClick={clearUpload}>
                  <X className="h-4 w-4 mr-2" />
                  Clear
                </Button>
              )}
            </div>
          ) : uploadedFile ? (
            <div className="space-y-4">
              <FileVideo className="h-12 w-12 mx-auto text-blue-600" />
              <div>
                <p className="font-medium">{uploadedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={clearUpload}>
                <X className="h-4 w-4 mr-2" />
                Remove
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
              <div>
                <p className="font-medium">Choose a video file or drag and drop</p>
                <p className="text-sm text-muted-foreground">
                  Supports {allowedFormats.join(', ')} files up to {maxFileSize}MB
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Upload Info */}
        <div className="mt-4 space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center justify-between">
            <span>Maximum file size:</span>
            <span>{maxFileSize}MB</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Supported formats:</span>
            <span>{allowedFormats.join(', ')}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Processing time:</span>
            <span>Typically 30-120 seconds</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default EmbeddedUpload;
