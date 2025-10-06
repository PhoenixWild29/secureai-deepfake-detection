/**
 * Error Recovery Service
 * API service for error recovery operations and retry management
 */

import { 
  ErrorInfo, 
  RetryAttempt, 
  RetryConfiguration, 
  RetryResult,
  ErrorLogEntry,
  TroubleshootingStep,
  ERROR_TYPE_CONFIGS 
} from '@/types/errorRecovery';

export interface ErrorRecoveryServiceConfig {
  /** Base URL for the API */
  baseUrl: string;
  /** Default timeout for requests */
  timeout: number;
  /** Retry configuration */
  retry: {
    attempts: number;
    delay: number;
  };
}

export interface RetryRequest {
  /** Analysis ID */
  analysisId: string;
  /** Retry configuration */
  configuration: RetryConfiguration;
  /** User ID initiating retry */
  userId?: string;
}

export interface RetryResponse {
  /** Retry attempt ID */
  retryId: string;
  /** Retry status */
  status: 'initiated' | 'failed';
  /** Response message */
  message: string;
  /** Estimated completion time */
  estimatedCompletion?: Date;
}

export class ErrorRecoveryService {
  private config: Required<ErrorRecoveryServiceConfig>;

  constructor(config: Partial<ErrorRecoveryServiceConfig> = {}) {
    this.config = {
      baseUrl: config.baseUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000'),
      timeout: config.timeout || 10000,
      retry: {
        attempts: config.retry?.attempts || 3,
        delay: config.retry?.delay || 1000,
      },
    };
  }

  /**
   * Initiate a retry operation
   */
  public async initiateRetry(request: RetryRequest): Promise<RetryResponse> {
    const url = `${this.config.baseUrl}/api/v1/analysis/${request.analysisId}/retry`;
    
    try {
      const response = await this.fetchWithRetry(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Failed to initiate retry: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformRetryResponse(data);
    } catch (error) {
      console.error('Error initiating retry:', error);
      throw error;
    }
  }

  /**
   * Get retry attempt status
   */
  public async getRetryStatus(retryId: string): Promise<RetryAttempt> {
    const url = `${this.config.baseUrl}/api/v1/retry/${retryId}/status`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get retry status: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformRetryAttempt(data);
    } catch (error) {
      console.error('Error getting retry status:', error);
      throw error;
    }
  }

  /**
   * Get retry history for an analysis
   */
  public async getRetryHistory(analysisId: string): Promise<RetryAttempt[]> {
    const url = `${this.config.baseUrl}/api/v1/analysis/${analysisId}/retry-history`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get retry history: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data.map((attempt: any) => this.transformRetryAttempt(attempt));
    } catch (error) {
      console.error('Error getting retry history:', error);
      throw error;
    }
  }

  /**
   * Get error logs for an analysis
   */
  public async getErrorLogs(analysisId: string, errorId?: string): Promise<ErrorLogEntry[]> {
    const url = errorId 
      ? `${this.config.baseUrl}/api/v1/error/${errorId}/logs`
      : `${this.config.baseUrl}/api/v1/analysis/${analysisId}/error-logs`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get error logs: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data.map((log: any) => this.transformErrorLogEntry(log));
    } catch (error) {
      console.error('Error getting error logs:', error);
      throw error;
    }
  }

  /**
   * Get troubleshooting steps for an error type
   */
  public async getTroubleshootingSteps(errorType: string): Promise<TroubleshootingStep[]> {
    // For now, return steps from the configuration
    // In a real implementation, this might fetch from an API
    const config = ERROR_TYPE_CONFIGS[errorType as keyof typeof ERROR_TYPE_CONFIGS];
    return config?.troubleshootingSteps || [];
  }

  /**
   * Mark a troubleshooting step as completed
   */
  public async completeTroubleshootingStep(
    stepId: string, 
    analysisId: string, 
    userId?: string
  ): Promise<void> {
    const url = `${this.config.baseUrl}/api/v1/troubleshooting/${stepId}/complete`;
    
    try {
      const response = await this.fetchWithRetry(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          analysisId,
          userId,
          completedAt: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to complete troubleshooting step: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error completing troubleshooting step:', error);
      throw error;
    }
  }

  /**
   * Cancel a retry operation
   */
  public async cancelRetry(retryId: string): Promise<void> {
    const url = `${this.config.baseUrl}/api/v1/retry/${retryId}/cancel`;
    
    try {
      const response = await this.fetchWithRetry(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to cancel retry: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error cancelling retry:', error);
      throw error;
    }
  }

  /**
   * Get error details
   */
  public async getErrorDetails(errorId: string): Promise<ErrorInfo> {
    const url = `${this.config.baseUrl}/api/v1/error/${errorId}`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to get error details: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformErrorInfo(data);
    } catch (error) {
      console.error('Error getting error details:', error);
      throw error;
    }
  }

  /**
   * Dismiss an error
   */
  public async dismissError(errorId: string, userId?: string): Promise<void> {
    const url = `${this.config.baseUrl}/api/v1/error/${errorId}/dismiss`;
    
    try {
      const response = await this.fetchWithRetry(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId,
          dismissedAt: new Date().toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to dismiss error: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error dismissing error:', error);
      throw error;
    }
  }

  /**
   * Fetch with retry logic
   */
  private async fetchWithRetry(url: string, options: RequestInit = {}): Promise<Response> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= this.config.retry.attempts; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        return response;
      } catch (error) {
        lastError = error as Error;
        
        if (attempt < this.config.retry.attempts) {
          await this.delay(this.config.retry.delay * attempt);
        }
      }
    }

    throw lastError || new Error('Max retry attempts exceeded');
  }

  /**
   * Delay utility
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Transform retry response from API
   */
  private transformRetryResponse(data: any): RetryResponse {
    return {
      retryId: data.retry_id,
      status: data.status,
      message: data.message,
      ...(data.estimated_completion && { estimatedCompletion: new Date(data.estimated_completion) }),
    };
  }

  /**
   * Transform retry attempt from API
   */
  private transformRetryAttempt(data: any): RetryAttempt {
    return {
      id: data.id,
      attemptNumber: data.attempt_number,
      scope: data.scope,
      timestamp: new Date(data.timestamp),
      status: data.status,
      ...(data.result && { result: this.transformRetryResult(data.result) }),
      ...(data.error && { error: this.transformErrorInfo(data.error) }),
      ...(data.duration && { duration: data.duration }),
      ...(data.initiated_by && { initiatedBy: data.initiated_by }),
      ...(data.configuration && { configuration: this.transformRetryConfiguration(data.configuration) }),
    };
  }

  /**
   * Transform retry result from API
   */
  private transformRetryResult(data: any): RetryResult {
    return {
      success: data.success,
      message: data.message,
      progress: data.progress,
      newStage: data.new_stage,
      data: data.data,
    };
  }

  /**
   * Transform retry configuration from API
   */
  private transformRetryConfiguration(data: any): RetryConfiguration {
    return {
      scope: data.scope,
      stage: data.stage,
      frameIndex: data.frame_index,
      options: data.options,
    };
  }

  /**
   * Transform error info from API
   */
  private transformErrorInfo(data: any): ErrorInfo {
    return {
      id: data.id,
      type: data.type,
      severity: data.severity,
      code: data.code,
      message: data.message,
      description: data.description,
      stage: data.stage,
      timestamp: new Date(data.timestamp),
      recoverable: data.recoverable,
      context: data.context,
      stackTrace: data.stack_trace,
      metadata: data.metadata,
    };
  }

  /**
   * Transform error log entry from API
   */
  private transformErrorLogEntry(data: any): ErrorLogEntry {
    return {
      id: data.id,
      level: data.level,
      message: data.message,
      timestamp: new Date(data.timestamp),
      source: data.source,
      data: data.data,
      stackTrace: data.stack_trace,
      errorId: data.error_id,
    };
  }
}

/**
 * Create error recovery service instance
 */
export const createErrorRecoveryService = (config?: Partial<ErrorRecoveryServiceConfig>): ErrorRecoveryService => {
  return new ErrorRecoveryService(config);
};

/**
 * Default error recovery service instance
 */
export const errorRecoveryService = createErrorRecoveryService();

export default ErrorRecoveryService;
