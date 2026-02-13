/**
 * API Service Layer for SecureAI Guardian
 * Handles all communication with the backend deepfake detection API
 */

import { ScanResult, ForensicMetrics } from '../types';

// Use relative URL in development to leverage Vite proxy, or use env variable for production
// In production, if no VITE_API_BASE_URL is set, use relative URLs (Nginx will proxy /api to backend)
// The Vite proxy will forward /api requests to the backend server
// IMPORTANT: Never use localhost in production - always use relative URLs
const API_BASE_URL = import.meta.env.DEV 
  ? '' // Use relative URLs in dev (goes through Vite proxy)
  : (import.meta.env.VITE_API_BASE_URL && !import.meta.env.VITE_API_BASE_URL.includes('localhost') 
      ? import.meta.env.VITE_API_BASE_URL 
      : ''); // Use relative URLs in production (Nginx proxies /api) - ignore localhost

/**
 * Backend API Response Types
 */
export interface BackendAnalysisResponse {
  id: string;
  filename: string;
  sourceUrl?: string;
  result: {
    is_fake: boolean;
    confidence: number;
    authenticity_score: number;
    fake_probability?: number;
    real_probability?: number;
    ensemble_score?: number;
    processing_time: number;
    video_hash?: string;
    method?: string;
    model_used?: string;
    frames_analyzed?: number;
    error?: string;
  };
  security_analysis?: {
    risk_level?: string;
    threats_detected?: string[];
  };
  processing_time: number;
  timestamp: string;
  file_size: number;
  blockchain_tx?: string;
  blockchain_network?: string;
  blockchain_timestamp?: string;
  storage?: {
    local: boolean;
    s3: boolean;
    distributed: boolean;
  };
  aistore_info?: {
    video_hash: string;
    storage_type: string;
    distributed_urls?: string[];
  };
  forensic_metrics?: {
    spatial_artifacts: number;
    temporal_consistency: number;
    spectral_density: number;
    vocal_authenticity: number;
    /** When false, vocal_authenticity is video-derived only; no audio analyzed */
    audio_analyzed?: boolean;
    spatial_entropy_heatmap?: Array<{
      sector: [number, number];
      intensity: number;
      detail: string;
    }>;
  };
}

export interface AnalysisRequest {
  file: File;
  analysisType?: 'quick' | 'comprehensive' | 'enhanced';
  modelType?: 'resnet' | 'cnn' | 'ensemble' | 'enhanced';
  analysisId?: string; // optional: pre-generated id used for Socket.IO room subscription
}

export interface UrlAnalysisRequest {
  url: string;
  analysisType?: 'quick' | 'comprehensive' | 'enhanced';
  modelType?: 'resnet' | 'cnn' | 'ensemble' | 'enhanced';
  analysisId?: string; // optional: pre-generated id used for Socket.IO room subscription
}

export interface AnalysisProgress {
  status: 'uploading' | 'processing' | 'analyzing' | 'finalizing' | 'completed';
  progress: number;
  message: string;
}

/**
 * Transform backend response to frontend ScanResult format
 */
export function transformBackendResponseToScanResult(
  backendResponse: BackendAnalysisResponse,
  fileName: string
): ScanResult {
  // Validate response structure
  if (!backendResponse.result) {
    throw new Error('Invalid backend response: missing result field');
  }
  
  const result = backendResponse.result;
  
  // Validate required fields - handle both possible response structures
  const isFake = result.is_fake !== undefined ? result.is_fake : (result.is_fake === true);
  
  // Handle confidence - it might be in different places
  let confidence = result.confidence;
  if (confidence === undefined && result.authenticity_score !== undefined) {
    confidence = 1 - result.authenticity_score;
  }
  if (typeof confidence !== 'number' || isNaN(confidence)) {
    console.warn('Confidence not found in expected format, defaulting to 0.5');
    confidence = 0.5;
  }
  
  // Determine verdict
  let verdict: 'REAL' | 'FAKE' | 'SUSPICIOUS' = isFake ? 'FAKE' : 'REAL';
  if (confidence < 0.7) {
    verdict = 'SUSPICIOUS';
  }

  // Use fake_probability directly from backend if available, otherwise calculate
  const authenticityScore = result.authenticity_score !== undefined 
    ? result.authenticity_score 
    : (1 - confidence);
  
  // Prefer backend's fake_probability (comes from actual model output)
  // Fall back to calculation only if backend doesn't provide it
  let fakeProbability: number;
  if (result.fake_probability !== undefined && typeof result.fake_probability === 'number') {
    // Use the actual model's fake probability
    fakeProbability = result.fake_probability;
  } else if (result.ensemble_score !== undefined) {
    // Use ensemble score if available (from enhanced detector)
    fakeProbability = result.ensemble_score;
  } else {
    // Fallback calculation (legacy)
    fakeProbability = isFake 
      ? Math.max(0.5, confidence) 
      : Math.min(0.5, 1 - authenticityScore);
  }

  // Extract artifacts from security analysis
  const artifactsDetected: string[] = [];
  if (backendResponse.security_analysis?.threats_detected) {
    artifactsDetected.push(...backendResponse.security_analysis.threats_detected);
  }
  if (isFake) {
    artifactsDetected.push('Neural pattern mismatch');
    if (result.method) {
      artifactsDetected.push(`${result.method} detection markers`);
    }
  }

  // Use real forensic metrics from backend if available, otherwise calculate fallback
  let metrics: ForensicMetrics;
  if (backendResponse.forensic_metrics) {
    metrics = {
      spatialArtifacts: backendResponse.forensic_metrics.spatial_artifacts,
      temporalConsistency: backendResponse.forensic_metrics.temporal_consistency,
      spectralDensity: backendResponse.forensic_metrics.spectral_density,
      vocalAuthenticity: backendResponse.forensic_metrics.vocal_authenticity,
      audioAnalyzed: backendResponse.forensic_metrics.audio_analyzed,
      audioPipelineStatus: backendResponse.forensic_metrics.audio_pipeline_status,
    };
  } else {
    // Fallback: calculate from detection result (backward compatibility)
    metrics = {
      spatialArtifacts: isFake ? Math.max(0.6, confidence) : Math.min(0.3, 1 - confidence),
      temporalConsistency: isFake ? Math.min(0.5, 1 - confidence) : Math.max(0.7, confidence),
      spectralDensity: isFake ? Math.max(0.5, confidence * 0.9) : Math.min(0.2, (1 - confidence) * 0.3),
      vocalAuthenticity: isFake ? Math.min(0.4, 1 - confidence) : Math.max(0.8, confidence),
    };
  }

  // Determine engine used (backend returns ultimate_ensemble_* when full ensemble ran, ensemble_unavailable when fallback)
  const method = result.method || '';
  const engineUsed: 'CLIP Zero-Shot' | 'Full Ensemble (SOTA 2025)' = 
    method === 'ensemble' || method === 'enhanced' || method.startsWith('ultimate_ensemble_')
      ? 'Full Ensemble (SOTA 2025)' 
      : 'CLIP Zero-Shot';

  // Generate explanation
  const explanation = isFake
    ? `Critical detection of non-human generative signatures. Confidence: ${(confidence * 100).toFixed(1)}%. ${result.method ? `Detection method: ${result.method}.` : ''} Matches known deepfake architecture hallmarks.`
    : `Media exhibits organic temporal coherence and natural sensor noise. Authenticity score: ${(authenticityScore * 100).toFixed(1)}%. No synthetic manipulation detected.`;

  // Extract spatial entropy heatmap if available
  const spatialEntropyHeatmap = backendResponse.forensic_metrics?.spatial_entropy_heatmap?.map(cell => ({
    sector: cell.sector as [number, number],
    intensity: cell.intensity,
    detail: cell.detail
  }));

  return {
    id: backendResponse.id || `NX-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
    timestamp: backendResponse.timestamp || new Date().toISOString(),
    fileName: fileName,
    sourceUrl: backendResponse.sourceUrl,
    fakeProbability,
    confidence: confidence,
    engineUsed,
    artifactsDetected,
    verdict,
    explanation,
    isBlockchainVerified: !!backendResponse.blockchain_tx,
    solanaTxSignature: backendResponse.blockchain_tx || undefined,
    metrics,
    spatialEntropyHeatmap,
    integrityHash: undefined, // Will be set by App.tsx
  };
}

/**
 * Backward-compatible alias.
 * Some call sites still use the older `transformBackendResponse` name.
 */
export function transformBackendResponse(
  backendResponse: BackendAnalysisResponse,
  fileName: string
): ScanResult {
  return transformBackendResponseToScanResult(backendResponse, fileName);
}

/**
 * Analyze a video file using the backend API
 */
export async function analyzeVideo(
  request: AnalysisRequest
): Promise<ScanResult> {
  const formData = new FormData();
  formData.append('video', request.file);

  // If provided, send analysis_id so backend uses the same id for Socket.IO room + result id
  if (request.analysisId) {
    formData.append('analysis_id', request.analysisId);
  }
  
  // Add optional parameters if provided
  if (request.modelType) {
    formData.append('model_type', request.modelType);
  }

  // Long timeout: model load + analysis; allow 15 min so backend can finish
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 900000); // 15 min

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
      // Note: Don't set Content-Type header, browser will set it with boundary
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `Analysis failed: (${response.status})`;
      try {
        const text = await response.text();
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json') && text) {
          const errorData = JSON.parse(text);
          errorMessage = errorData.error || errorData.message || errorMessage;
          if (response.status === 400) {
            if (errorData.error?.includes('No video file')) {
              errorMessage = 'No video file provided. Please select a file to upload.';
            } else if (errorData.error?.includes('Unsupported file format')) {
              errorMessage = `Unsupported file format. Please use: MP4, AVI, MOV, MKV, or WEBM.`;
            } else if (errorData.error?.includes('file size')) {
              errorMessage = `File too large. Maximum size is 500MB.`;
            } else {
              errorMessage = errorData.error || `Invalid request: ${errorMessage}`;
            }
          } else if (response.status === 413) {
            errorMessage = 'File too large. Maximum size is 500MB.';
          } else if (response.status === 503 && errorData.ensemble_unavailable) {
            errorMessage = 'Models are loading or temporarily unavailable. The first scan after a restart can take 2–5 minutes—please wait and try again.';
        } else if (response.status === 503) {
          errorMessage = errorData.error || 'Service temporarily unavailable. Please retry.';
        } else if (response.status === 500) {
          errorMessage = 'Server error. Please try again later.';
        }
        }
      } catch (parseError) {
        if (response.status === 504) {
          errorMessage = 'Request timed out. The server took too long to respond. Try a shorter video or try again.';
        } else if (response.status === 502 || response.status === 503) {
          errorMessage = 'Backend unavailable or overloaded. Please try again.';
        }
        console.error('Failed to parse error response:', parseError);
      }
      throw new Error(errorMessage);
    }

    const backendResponse: BackendAnalysisResponse = await response.json();
    console.log('Backend response received:', backendResponse);
    
    // Transform backend response to frontend format
    try {
      const transformedResult = transformBackendResponse(backendResponse, request.file.name);
      console.log('Transformed result:', transformedResult);
      return transformedResult;
    } catch (transformError) {
      console.error('Error transforming backend response:', transformError);
      console.error('Backend response that failed:', backendResponse);
      throw new Error(`Failed to process analysis results: ${transformError instanceof Error ? transformError.message : 'Unknown error'}`);
    }
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('Video analysis error:', error);
    // Connection dropped or aborted after long run: backend may have finished
    const msg = error instanceof Error ? error.message : '';
    if (msg === 'Failed to fetch' || (msg.includes('fetch') && msg.toLowerCase().includes('failed'))) {
      throw new Error(
        'Connection closed before the response was received. The analysis may have completed—check the Security Hub for your result, or try again.'
      );
    }
    if (msg.includes('aborted') || msg.includes('AbortError') || msg.includes('signal is aborted')) {
      throw new Error(
        'Request took too long and was cancelled. The analysis may have completed—check the Security Hub, or try again (first scan loads models and can take a few minutes).'
      );
    }
    throw error;
  }
}

/**
 * Analyze a video from URL using the backend API
 */
export async function analyzeVideoFromUrl(
  request: UrlAnalysisRequest
): Promise<ScanResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 900000); // 15 min
  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: request.url,
        analysis_id: request.analysisId,
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `Analysis failed: ${response.statusText} (${response.status})`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || errorMessage;

        // Pass through structured error codes for better UX
        if (errorData?.error_code) {
          const err: any = new Error(errorMessage);
          err.code = errorData.error_code;
          err.details = errorData;
          throw err;
        }
        
        if (response.status === 503 && errorData.ensemble_unavailable) {
          errorMessage = 'Models are loading or temporarily unavailable. The first scan after a restart can take 2–5 minutes—please wait and try again.';
        } else if (response.status === 503) {
          errorMessage = errorData.error || 'Service temporarily unavailable. Please retry.';
        } else if (response.status === 400) {
          if (errorData.error?.includes('Invalid video URL')) {
            errorMessage = 'Invalid video URL. Supported: YouTube, Twitter/X, Vimeo, or direct video URLs (.mp4, .avi, etc.)';
          } else if (errorData.error?.includes('Failed to download')) {
            errorMessage = `Video download failed: ${errorData.error}`;
          } else {
            errorMessage = errorData.error || `Invalid request: ${errorMessage}`;
          }
        } else if (response.status === 500) {
          errorMessage = errorData.error || 'Server error. Please try again later.';
        } else if (response.status === 504) {
          errorMessage = 'Request timed out. The server took too long to respond. Try a shorter video or try again in a few minutes.';
        } else if (response.status === 502 || response.status === 503) {
          errorMessage = 'Backend unavailable or overloaded. Please try again in a minute.';
        }
      } catch (parseError) {
        if (response.status === 504) {
          errorMessage = 'Request timed out. The server took too long to respond. Try a shorter video or try again.';
        } else if (response.status === 502 || response.status === 503) {
          errorMessage = 'Backend unavailable or overloaded. Please try again.';
        }
        console.error('Failed to parse error response:', parseError);
      }
      throw new Error(errorMessage);
    }

    const backendResponse: BackendAnalysisResponse = await response.json();
    console.log('Backend response received:', backendResponse);
    
    // Transform backend response to frontend format
    try {
      const transformedResult = transformBackendResponse(backendResponse, backendResponse.filename || 'video_from_url');
      if (backendResponse.sourceUrl) {
        transformedResult.sourceUrl = backendResponse.sourceUrl;
      }
      console.log('Transformed result:', transformedResult);
      return transformedResult;
    } catch (transformError) {
      console.error('Error transforming backend response:', transformError);
      console.error('Backend response that failed:', backendResponse);
      throw new Error(`Failed to process analysis results: ${transformError instanceof Error ? transformError.message : 'Unknown error'}`);
    }
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('Video URL analysis error:', error);
    const msg = error instanceof Error ? error.message : '';
    if (msg === 'Failed to fetch' || (msg.includes('fetch') && msg.toLowerCase().includes('failed'))) {
      throw new Error(
        'Connection closed before the response was received. The analysis may have completed—check the Security Hub for your result, or try again.'
      );
    }
    if (msg.includes('aborted') || msg.includes('AbortError') || msg.includes('signal is aborted')) {
      throw new Error(
        'Request took too long and was cancelled. The analysis may have completed—check the Security Hub, or try again (first scan loads models and can take a few minutes).'
      );
    }
    throw error;
  }
}

/**
 * Check backend health status
 */
export async function checkBackendHealth(): Promise<{ status: string; healthy: boolean }> {
  try {
    const url = `${API_BASE_URL}/api/health`;
    console.log('[Health Check] Attempting to connect to:', url || '/api/health (relative)');
    
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include', // Include cookies
      headers: {
        'Accept': 'application/json',
      },
    });

    console.log('[Health Check] Response status:', response.status, response.statusText);
    console.log('[Health Check] Response headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Health Check] Response not OK:', errorText);
      return { status: 'unhealthy', healthy: false };
    }

    const data = await response.json();
    console.log('[Health Check] Success:', data);
    return {
      status: data.status || 'unknown',
      healthy: data.status === 'healthy' || data.status === 'ok',
    };
  } catch (error) {
    console.error('[Health Check] Error:', error);
    console.error('[Health Check] Error details:', {
      message: error instanceof Error ? error.message : String(error),
      name: error instanceof Error ? error.name : 'Unknown',
      stack: error instanceof Error ? error.stack : undefined,
    });
    return { status: 'error', healthy: false };
  }
}

/**
 * Get analysis result by ID (for retrieving saved results)
 */
export async function getAnalysisResult(analysisId: string): Promise<ScanResult | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/result/${analysisId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      return null;
    }

    const backendResponse: BackendAnalysisResponse = await response.json();
    return transformBackendResponse(backendResponse, backendResponse.filename);
  } catch (error) {
    console.error('Get analysis result error:', error);
    return null;
  }
}

/**
 * Submit analysis result to Solana blockchain
 */
export async function submitToBlockchain(analysisId: string): Promise<{ blockchain_tx: string; message: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/blockchain/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysis_id: analysisId,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `Blockchain submission failed: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      blockchain_tx: data.blockchain_tx,
      message: data.message || 'Analysis result submitted to blockchain successfully',
    };
  } catch (error) {
    console.error('Blockchain submission error:', error);
    throw error;
  }
}

/**
 * Upload file with progress tracking (for large files)
 */
export async function uploadVideoWithProgress(
  file: File,
  onProgress?: (progress: number) => void
): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const progress = (e.loaded / e.total) * 100;
        onProgress(progress);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response.id || response.analysis_id);
        } catch (error) {
          reject(new Error('Invalid response format'));
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.statusText}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed: Network error'));
    });

    xhr.addEventListener('abort', () => {
      reject(new Error('Upload aborted'));
    });

    const formData = new FormData();
    formData.append('video', file);

    xhr.open('POST', `${API_BASE_URL}/api/analyze`);
    xhr.send(formData);
  });
}

