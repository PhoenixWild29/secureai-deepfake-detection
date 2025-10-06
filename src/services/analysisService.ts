/**
 * Analysis Service
 * API service for fetching analysis processing status and resource monitoring data
 */

import { AnalysisStatus, ProcessingStageInfo, WorkerInfo, GPUInfo, QueueInfo, ResourceMetrics } from '@/types/processingStage';

export interface AnalysisServiceConfig {
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

export interface PollingConfig {
  /** Polling interval in milliseconds */
  interval: number;
  /** Whether to start polling immediately */
  autoStart: boolean;
  /** Maximum polling duration in milliseconds */
  maxDuration?: number;
  /** Whether to stop polling on error */
  stopOnError: boolean;
}

export class AnalysisService {
  private config: Required<AnalysisServiceConfig>;
  private pollingTimers: Map<string, NodeJS.Timeout> = new Map();
  private pollingCallbacks: Map<string, (status: AnalysisStatus) => void> = new Map();

  constructor(config: Partial<AnalysisServiceConfig> = {}) {
    this.config = {
      baseUrl: config.baseUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      timeout: config.timeout || 10000,
      retry: {
        attempts: config.retry?.attempts || 3,
        delay: config.retry?.delay || 1000,
      },
    };
  }

  /**
   * Fetch analysis status for a specific analysis ID
   */
  public async getAnalysisStatus(analysisId: string): Promise<AnalysisStatus> {
    const url = `${this.config.baseUrl}/api/v1/analysis/${analysisId}/status`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch analysis status: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformAnalysisStatus(data);
    } catch (error) {
      console.error('Error fetching analysis status:', error);
      throw error;
    }
  }

  /**
   * Start polling for analysis status updates
   */
  public startPolling(
    analysisId: string,
    callback: (status: AnalysisStatus) => void,
    config: Partial<PollingConfig> = {}
  ): () => void {
    const pollingConfig: Required<PollingConfig> = {
      interval: config.interval || 2000,
      autoStart: config.autoStart !== false,
      maxDuration: config.maxDuration,
      stopOnError: config.stopOnError !== false,
    };

    // Store callback
    this.pollingCallbacks.set(analysisId, callback);

    // Start polling if autoStart is enabled
    if (pollingConfig.autoStart) {
      this.startPollingTimer(analysisId, pollingConfig);
    }

    // Return stop function
    return () => this.stopPolling(analysisId);
  }

  /**
   * Stop polling for a specific analysis
   */
  public stopPolling(analysisId: string): void {
    const timer = this.pollingTimers.get(analysisId);
    if (timer) {
      clearInterval(timer);
      this.pollingTimers.delete(analysisId);
    }
    this.pollingCallbacks.delete(analysisId);
  }

  /**
   * Stop all polling
   */
  public stopAllPolling(): void {
    this.pollingTimers.forEach((timer) => clearInterval(timer));
    this.pollingTimers.clear();
    this.pollingCallbacks.clear();
  }

  /**
   * Get worker information
   */
  public async getWorkerInfo(): Promise<WorkerInfo[]> {
    const url = `${this.config.baseUrl}/api/v1/workers/status`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch worker info: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformWorkerInfo(data);
    } catch (error) {
      console.error('Error fetching worker info:', error);
      throw error;
    }
  }

  /**
   * Get GPU information
   */
  public async getGPUInfo(): Promise<GPUInfo[]> {
    const url = `${this.config.baseUrl}/api/v1/gpu/status`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch GPU info: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformGPUInfo(data);
    } catch (error) {
      console.error('Error fetching GPU info:', error);
      throw error;
    }
  }

  /**
   * Get queue information
   */
  public async getQueueInfo(queueId?: string): Promise<QueueInfo> {
    const url = queueId 
      ? `${this.config.baseUrl}/api/v1/queue/${queueId}/status`
      : `${this.config.baseUrl}/api/v1/queue/status`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch queue info: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformQueueInfo(data);
    } catch (error) {
      console.error('Error fetching queue info:', error);
      throw error;
    }
  }

  /**
   * Get system resource metrics
   */
  public async getResourceMetrics(): Promise<ResourceMetrics> {
    const url = `${this.config.baseUrl}/api/v1/system/metrics`;
    
    try {
      const response = await this.fetchWithRetry(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch resource metrics: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return this.transformResourceMetrics(data);
    } catch (error) {
      console.error('Error fetching resource metrics:', error);
      throw error;
    }
  }

  /**
   * Start polling timer for analysis status
   */
  private startPollingTimer(analysisId: string, config: Required<PollingConfig>): void {
    const timer = setInterval(async () => {
      try {
        const status = await this.getAnalysisStatus(analysisId);
        const callback = this.pollingCallbacks.get(analysisId);
        
        if (callback) {
          callback(status);
        }

        // Stop polling if analysis is completed or failed
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          this.stopPolling(analysisId);
        }
      } catch (error) {
        console.error('Error during polling:', error);
        
        if (config.stopOnError) {
          this.stopPolling(analysisId);
        }
      }
    }, config.interval);

    this.pollingTimers.set(analysisId, timer);

    // Set max duration timer if specified
    if (config.maxDuration) {
      setTimeout(() => {
        this.stopPolling(analysisId);
      }, config.maxDuration);
    }
  }

  /**
   * Fetch with retry logic
   */
  private async fetchWithRetry(url: string): Promise<Response> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= this.config.retry.attempts; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
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
   * Transform analysis status data from API response
   */
  private transformAnalysisStatus(data: any): AnalysisStatus {
    return {
      analysisId: data.analysis_id,
      currentStage: data.current_stage,
      overallProgress: data.overall_progress || 0,
      startTime: new Date(data.start_time),
      lastUpdate: new Date(data.last_update),
      estimatedCompletion: data.estimated_completion ? new Date(data.estimated_completion) : undefined,
      stages: this.transformStages(data.stages || []),
      workers: this.transformWorkerInfo(data.workers || []),
      gpus: this.transformGPUInfo(data.gpus || []),
      queue: this.transformQueueInfo(data.queue || {}),
      resourceMetrics: this.transformResourceMetrics(data.resource_metrics || {}),
      status: data.status || 'pending',
      error: data.error ? this.transformStageError(data.error) : undefined,
      metadata: data.metadata || {},
    };
  }

  /**
   * Transform stages data
   */
  private transformStages(data: any[]): ProcessingStageInfo[] {
    return data.map(stage => ({
      id: stage.id,
      name: stage.name,
      description: stage.description,
      progress: stage.progress || 0,
      isActive: stage.is_active || false,
      isCompleted: stage.is_completed || false,
      hasError: stage.has_error || false,
      isSkipped: stage.is_skipped || false,
      startTime: stage.start_time ? new Date(stage.start_time) : undefined,
      endTime: stage.end_time ? new Date(stage.end_time) : undefined,
      estimatedDuration: stage.estimated_duration,
      actualDuration: stage.actual_duration,
      error: stage.error ? this.transformStageError(stage.error) : undefined,
      metadata: stage.metadata || {},
    }));
  }

  /**
   * Transform worker info data
   */
  private transformWorkerInfo(data: any[]): WorkerInfo[] {
    return data.map(worker => ({
      id: worker.id,
      name: worker.name,
      status: worker.status,
      currentTask: worker.current_task,
      taskStartTime: worker.task_start_time ? new Date(worker.task_start_time) : undefined,
      cpuUsage: worker.cpu_usage || 0,
      memoryUsage: worker.memory_usage || 0,
      uptime: worker.uptime || 0,
      tasksCompleted: worker.tasks_completed || 0,
      metadata: worker.metadata || {},
    }));
  }

  /**
   * Transform GPU info data
   */
  private transformGPUInfo(data: any[]): GPUInfo[] {
    return data.map(gpu => ({
      id: gpu.id,
      name: gpu.name,
      status: gpu.status,
      utilization: gpu.utilization || 0,
      memoryUsed: gpu.memory_used || 0,
      memoryTotal: gpu.memory_total || 0,
      memoryUsagePercentage: gpu.memory_usage_percentage || 0,
      temperature: gpu.temperature || 0,
      powerUsage: gpu.power_usage || 0,
      currentTask: gpu.current_task,
      taskStartTime: gpu.task_start_time ? new Date(gpu.task_start_time) : undefined,
      metadata: gpu.metadata || {},
    }));
  }

  /**
   * Transform queue info data
   */
  private transformQueueInfo(data: any): QueueInfo {
    return {
      id: data.id || 'default',
      name: data.name || 'Processing Queue',
      position: data.position || 0,
      totalItems: data.total_items || 0,
      estimatedWaitTime: data.estimated_wait_time || 0,
      priority: data.priority || 'normal',
      status: data.status || 'active',
      processingRate: data.processing_rate || 0,
      averageProcessingTime: data.average_processing_time || 0,
      metadata: data.metadata || {},
    };
  }

  /**
   * Transform resource metrics data
   */
  private transformResourceMetrics(data: any): ResourceMetrics {
    return {
      systemCpuUsage: data.system_cpu_usage || 0,
      systemMemoryUsed: data.system_memory_used || 0,
      systemMemoryTotal: data.system_memory_total || 0,
      systemMemoryUsagePercentage: data.system_memory_usage_percentage || 0,
      diskUsagePercentage: data.disk_usage_percentage || 0,
      networkIO: data.network_io || 0,
      timestamp: new Date(data.timestamp || Date.now()),
    };
  }

  /**
   * Transform stage error data
   */
  private transformStageError(data: any): any {
    return {
      code: data.code,
      message: data.message,
      severity: data.severity || 'medium',
      recoverable: data.recoverable || false,
      timestamp: new Date(data.timestamp || Date.now()),
      recoveryActions: data.recovery_actions || [],
    };
  }
}

/**
 * Create analysis service instance
 */
export const createAnalysisService = (config?: Partial<AnalysisServiceConfig>): AnalysisService => {
  return new AnalysisService(config);
};

/**
 * Default analysis service instance
 */
export const analysisService = createAnalysisService();

export default AnalysisService;
