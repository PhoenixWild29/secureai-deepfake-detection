/**
 * WebSocket Types and Validation
 * Type definitions and validation utilities for WebSocket message handling
 */

/**
 * Analysis processing stages
 * @typedef {('initializing'|'uploading'|'frame_extraction'|'feature_extraction'|'model_inference'|'post_processing'|'blockchain_submission'|'completed'|'failed')} AnalysisStage
 */
export const ANALYSIS_STAGES = {
  INITIALIZING: 'initializing',
  UPLOADING: 'uploading',
  FRAME_EXTRACTION: 'frame_extraction',
  FEATURE_EXTRACTION: 'feature_extraction',
  MODEL_INFERENCE: 'model_inference',
  POST_PROCESSING: 'post_processing',
  BLOCKCHAIN_SUBMISSION: 'blockchain_submission',
  COMPLETED: 'completed',
  FAILED: 'failed'
};

/**
 * WebSocket event types
 * @typedef {('status_update'|'result_update'|'error'|'heartbeat'|'connection_established'|'stage_transition'|'status_streaming')} EventType
 */
export const EVENT_TYPES = {
  STATUS_UPDATE: 'status_update',
  RESULT_UPDATE: 'result_update',
  ERROR: 'error',
  HEARTBEAT: 'heartbeat',
  CONNECTION_ESTABLISHED: 'connection_established',
  STAGE_TRANSITION: 'stage_transition',
  STATUS_STREAMING: 'status_streaming'
};

/**
 * WebSocket connection states
 * @typedef {('connecting'|'connected'|'disconnected'|'reconnecting'|'error')} ConnectionState
 */
export const CONNECTION_STATES = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  RECONNECTING: 'reconnecting',
  ERROR: 'error'
};

/**
 * Suspicious region detected in video analysis
 * @typedef {Object} SuspiciousRegion
 * @property {number} frame_number - Frame number where region was detected
 * @property {number} x - Normalized x coordinate (0.0-1.0)
 * @property {number} y - Normalized y coordinate (0.0-1.0)
 * @property {number} width - Normalized width (0.0-1.0)
 * @property {number} height - Normalized height (0.0-1.0)
 * @property {number} confidence - Detection confidence (0.0-1.0)
 * @property {string} region_type - Type of suspicious region
 */
export class SuspiciousRegion {
  constructor(data) {
    this.frame_number = data.frame_number;
    this.x = data.x;
    this.y = data.y;
    this.width = data.width;
    this.height = data.height;
    this.confidence = data.confidence;
    this.region_type = data.region_type;
  }

  /**
   * Validate suspicious region data
   * @param {Object} data - Region data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      typeof data.frame_number === 'number' && data.frame_number >= 0 &&
      typeof data.x === 'number' && data.x >= 0 && data.x <= 1 &&
      typeof data.y === 'number' && data.y >= 0 && data.y <= 1 &&
      typeof data.width === 'number' && data.width >= 0 && data.width <= 1 &&
      typeof data.height === 'number' && data.height >= 0 && data.height <= 1 &&
      typeof data.confidence === 'number' && data.confidence >= 0 && data.confidence <= 1 &&
      typeof data.region_type === 'string' && data.region_type.length > 0
    );
  }
}

/**
 * Status update event for real-time analysis progress
 * @typedef {Object} StatusUpdate
 * @property {string} event_type - Event type ('status_update')
 * @property {string} task_id - Celery task ID
 * @property {string} analysis_id - Analysis ID
 * @property {number} progress - Progress percentage (0.0-1.0)
 * @property {AnalysisStage} current_stage - Current processing stage
 * @property {string} message - Status message
 * @property {string|null} estimated_completion - Estimated completion time (ISO string)
 * @property {string|null} error - Error message if any
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class StatusUpdate {
  constructor(data) {
    this.event_type = data.event_type;
    this.task_id = data.task_id;
    this.analysis_id = data.analysis_id;
    this.progress = data.progress;
    this.current_stage = data.current_stage;
    this.message = data.message;
    this.estimated_completion = data.estimated_completion;
    this.error = data.error;
    this.timestamp = data.timestamp;
  }

  /**
   * Validate status update data
   * @param {Object} data - Status update data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.STATUS_UPDATE &&
      typeof data.task_id === 'string' && data.task_id.length > 0 &&
      typeof data.analysis_id === 'string' && data.analysis_id.length > 0 &&
      typeof data.progress === 'number' && data.progress >= 0 && data.progress <= 1 &&
      Object.values(ANALYSIS_STAGES).includes(data.current_stage) &&
      typeof data.message === 'string' && data.message.length > 0 &&
      (data.estimated_completion === null || typeof data.estimated_completion === 'string') &&
      (data.error === null || typeof data.error === 'string') &&
      typeof data.timestamp === 'string'
    );
  }

  /**
   * Get progress percentage for display
   * @returns {number} - Progress percentage (0-100)
   */
  getProgressPercentage() {
    return Math.round(this.progress * 100);
  }

  /**
   * Get estimated completion time as Date
   * @returns {Date|null} - Estimated completion date or null
   */
  getEstimatedCompletionDate() {
    return this.estimated_completion ? new Date(this.estimated_completion) : null;
  }

  /**
   * Check if analysis is completed
   * @returns {boolean} - True if completed
   */
  isCompleted() {
    return this.current_stage === ANALYSIS_STAGES.COMPLETED;
  }

  /**
   * Check if analysis failed
   * @returns {boolean} - True if failed
   */
  isFailed() {
    return this.current_stage === ANALYSIS_STAGES.FAILED || this.error !== null;
  }
}

/**
 * Result update event for completed analysis
 * @typedef {Object} ResultUpdate
 * @property {string} event_type - Event type ('result_update')
 * @property {string} analysis_id - Analysis ID
 * @property {number} confidence_score - Overall confidence score (0.0-1.0)
 * @property {number} frames_processed - Number of frames processed
 * @property {number} total_frames - Total frames in video
 * @property {SuspiciousRegion[]} suspicious_regions - Detected suspicious regions
 * @property {string|null} blockchain_hash - Blockchain verification hash
 * @property {number} processing_time_ms - Total processing time in milliseconds
 * @property {boolean} is_fake - Whether video is detected as fake
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class ResultUpdate {
  constructor(data) {
    this.event_type = data.event_type;
    this.analysis_id = data.analysis_id;
    this.confidence_score = data.confidence_score;
    this.frames_processed = data.frames_processed;
    this.total_frames = data.total_frames;
    this.suspicious_regions = data.suspicious_regions || [];
    this.blockchain_hash = data.blockchain_hash;
    this.processing_time_ms = data.processing_time_ms;
    this.is_fake = data.is_fake;
    this.timestamp = data.timestamp;
  }

  /**
   * Validate result update data
   * @param {Object} data - Result update data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.RESULT_UPDATE &&
      typeof data.analysis_id === 'string' && data.analysis_id.length > 0 &&
      typeof data.confidence_score === 'number' && data.confidence_score >= 0 && data.confidence_score <= 1 &&
      typeof data.frames_processed === 'number' && data.frames_processed >= 0 &&
      typeof data.total_frames === 'number' && data.total_frames >= 0 &&
      data.frames_processed <= data.total_frames &&
      Array.isArray(data.suspicious_regions) &&
      data.suspicious_regions.every(region => SuspiciousRegion.validate(region)) &&
      (data.blockchain_hash === null || typeof data.blockchain_hash === 'string') &&
      typeof data.processing_time_ms === 'number' && data.processing_time_ms >= 0 &&
      typeof data.is_fake === 'boolean' &&
      typeof data.timestamp === 'string'
    );
  }

  /**
   * Get confidence percentage for display
   * @returns {number} - Confidence percentage (0-100)
   */
  getConfidencePercentage() {
    return Math.round(this.confidence_score * 100);
  }

  /**
   * Get processing time in seconds
   * @returns {number} - Processing time in seconds
   */
  getProcessingTimeSeconds() {
    return Math.round(this.processing_time_ms / 1000);
  }

  /**
   * Get processing time formatted string
   * @returns {string} - Formatted processing time
   */
  getProcessingTimeFormatted() {
    const seconds = this.getProcessingTimeSeconds();
    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  }
}

/**
 * Error event for analysis failures
 * @typedef {Object} ErrorEvent
 * @property {string} event_type - Event type ('error')
 * @property {string} analysis_id - Analysis ID
 * @property {string} error_code - Error code
 * @property {string} error_message - Error message
 * @property {Object|null} error_details - Additional error details
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class ErrorEvent {
  constructor(data) {
    this.event_type = data.event_type;
    this.analysis_id = data.analysis_id;
    this.error_code = data.error_code;
    this.error_message = data.error_message;
    this.error_details = data.error_details;
    this.timestamp = data.timestamp;
  }

  /**
   * Validate error event data
   * @param {Object} data - Error event data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.ERROR &&
      typeof data.analysis_id === 'string' && data.analysis_id.length > 0 &&
      typeof data.error_code === 'string' && data.error_code.length > 0 &&
      typeof data.error_message === 'string' && data.error_message.length > 0 &&
      (data.error_details === null || typeof data.error_details === 'object') &&
      typeof data.timestamp === 'string'
    );
  }
}

/**
 * Heartbeat event for connection health monitoring
 * @typedef {Object} HeartbeatEvent
 * @property {string} event_type - Event type ('heartbeat')
 * @property {string} message - Heartbeat message ('ping' or 'pong')
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class HeartbeatEvent {
  constructor(data) {
    this.event_type = data.event_type;
    this.message = data.message;
    this.timestamp = data.timestamp;
  }

  /**
   * Validate heartbeat event data
   * @param {Object} data - Heartbeat event data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.HEARTBEAT &&
      typeof data.message === 'string' && (data.message === 'ping' || data.message === 'pong') &&
      typeof data.timestamp === 'string'
    );
  }
}

/**
 * Connection established event
 * @typedef {Object} ConnectionEstablishedEvent
 * @property {string} event_type - Event type ('connection_established')
 * @property {string} analysis_id - Analysis ID
 * @property {string} message - Welcome message
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class ConnectionEstablishedEvent {
  constructor(data) {
    this.event_type = data.event_type;
    this.analysis_id = data.analysis_id;
    this.message = data.message;
    this.timestamp = data.timestamp;
  }

  /**
   * Validate connection established event data
   * @param {Object} data - Connection established event data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.CONNECTION_ESTABLISHED &&
      typeof data.analysis_id === 'string' && data.analysis_id.length > 0 &&
      typeof data.message === 'string' && data.message.length > 0 &&
      typeof data.timestamp === 'string'
    );
  }
}

/**
 * WebSocket message parser and validator
 */
export class WebSocketMessageParser {
  /**
   * Parse and validate WebSocket message
   * @param {string} message - Raw WebSocket message
   * @returns {Object|null} - Parsed message object or null if invalid
   */
  static parseMessage(message) {
    try {
      const data = JSON.parse(message);
      
      // Validate based on event type
      switch (data.event_type) {
        case EVENT_TYPES.STATUS_UPDATE:
          if (StatusUpdate.validate(data)) {
            return new StatusUpdate(data);
          }
          break;
          
        case EVENT_TYPES.RESULT_UPDATE:
          if (ResultUpdate.validate(data)) {
            return new ResultUpdate(data);
          }
          break;
          
        case EVENT_TYPES.ERROR:
          if (ErrorEvent.validate(data)) {
            return new ErrorEvent(data);
          }
          break;
          
        case EVENT_TYPES.HEARTBEAT:
          if (HeartbeatEvent.validate(data)) {
            return new HeartbeatEvent(data);
          }
          break;
          
        case EVENT_TYPES.CONNECTION_ESTABLISHED:
          if (ConnectionEstablishedEvent.validate(data)) {
            return new ConnectionEstablishedEvent(data);
          }
          break;
          
        case EVENT_TYPES.STAGE_TRANSITION:
          if (StageTransitionEvent.validate(data)) {
            return new StageTransitionEvent(data);
          }
          break;
          
        case EVENT_TYPES.STATUS_STREAMING:
          if (StatusStreamingEvent.validate(data)) {
            return new StatusStreamingEvent(data);
          }
          break;
          
        default:
          console.warn('Unknown event type:', data.event_type);
          return null;
      }
      
      console.warn('Invalid message data:', data);
      return null;
      
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      return null;
    }
  }

  /**
   * Create heartbeat message
   * @param {string} message - Heartbeat message ('ping' or 'pong')
   * @returns {string} - JSON string message
   */
  static createHeartbeatMessage(message = 'ping') {
    const heartbeat = new HeartbeatEvent({
      event_type: EVENT_TYPES.HEARTBEAT,
      message: message,
      timestamp: new Date().toISOString()
    });
    
    return JSON.stringify({
      type: message,
      timestamp: new Date().toISOString()
    });
  }
}

/**
 * Stage transition event for real-time analysis stage changes
 * @typedef {Object} StageTransitionEvent
 * @property {string} event_type - Event type ('stage_transition')
 * @property {string} analysis_id - Analysis ID
 * @property {AnalysisStage} from_stage - Previous stage
 * @property {AnalysisStage} to_stage - Current stage
 * @property {string} transition_reason - Reason for transition
 * @property {number} stage_progress - Progress in current stage (0.0-1.0)
 * @property {string|null} estimated_stage_completion - Estimated stage completion time (ISO string)
 * @property {number|null} stage_frames_processed - Frames processed in previous stage
 * @property {number|null} stage_total_frames - Total frames in current stage
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class StageTransitionEvent {
  constructor(data) {
    this.event_type = data.event_type;
    this.analysis_id = data.analysis_id;
    this.from_stage = data.from_stage;
    this.to_stage = data.to_stage;
    this.transition_reason = data.transition_reason;
    this.stage_progress = data.stage_progress;
    this.estimated_stage_completion = data.estimated_stage_completion;
    this.stage_frames_processed = data.stage_frames_processed;
    this.stage_total_frames = data.stage_total_frames;
    this.timestamp = data.timestamp;
  }

  /**
   * Validate stage transition event data
   * @param {Object} data - Stage transition data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.STAGE_TRANSITION &&
      typeof data.analysis_id === 'string' && data.analysis_id.length > 0 &&
      Object.values(ANALYSIS_STAGES).includes(data.from_stage) &&
      Object.values(ANALYSIS_STAGES).includes(data.to_stage) &&
      typeof data.transition_reason === 'string' && data.transition_reason.length > 0 &&
      typeof data.stage_progress === 'number' && data.stage_progress >= 0 && data.stage_progress <= 1 &&
      (data.estimated_stage_completion === null || typeof data.estimated_stage_completion === 'string') &&
      (data.stage_frames_processed === null || (typeof data.stage_frames_processed === 'number' && data.stage_frames_processed >= 0)) &&
      (data.stage_total_frames === null || (typeof data.stage_total_frames === 'number' && data.stage_total_frames >= 0)) &&
      typeof data.timestamp === 'string'
    );
  }

  /**
   * Get stage progress percentage for display
   * @returns {number} - Stage progress percentage (0-100)
   */
  getStageProgressPercentage() {
    return Math.round(this.stage_progress * 100);
  }

  /**
   * Check if transition represents progress advancement
   * @returns {boolean} - True if progressing forward
   */
  isProgressTransition() {
    const stageOrder = Object.values(ANALYSIS_STAGES);
    const fromIndex = stageOrder.indexOf(this.from_stage);
    const toIndex = stageOrder.indexOf(this.to_stage);
    return toIndex > fromIndex;
  }

  /**
   * Get estimated stage completion date
   * @returns {Date|null} - Estimated completion date or null
   */
  getEstimatedStageCompletionDate() {
    return this.estimated_stage_completion ? new Date(this.estimated_stage_completion) : null;
  }
}

/**
 * Comprehensive status streaming event
 * @typedef {Object} StatusStreamingEvent
 * @property {string} event_type - Event type ('status_streaming')
 * @property {string} analysis_id - Analysis ID
 * @property {AnalysisStage} current_stage - Current processing stage
 * @property {number} overall_progress - Overall progress percentage (0.0-1.0)
 * @property {number} stage_progress - Current stage progress (0.0-1.0)
 * @property {string} message - Status message
 * @property {string|null} estimated_completion - Estimated completion time (ISO string)
 * @property {number} frames_processed - Total frames processed
 * @property {number} total_frames - Total frames in video
 * @property {number|null} processing_rate_fps - Processing rate in FPS
 * @property {number|null} cpu_usage_percent - CPU usage percentage
 * @property {number|null} memory_usage_mb - Memory usage in MB
 * @property {number|null} processing_efficiency - Processing efficiency score (0.0-1.0)
 * @property {ErrorRecoveryStatus|null} error_recovery_status - Error recovery information
 * @property {Object[]} progress_history - Recent progress history
 * @property {string} timestamp - Event timestamp (ISO string)
 */
export class StatusStreamingEvent {
  constructor(data) {
    this.event_type = data.event_type;
    this.analysis_id = data.analysis_id;
    this.current_stage = data.current_stage;
    this.overall_progress = data.overall_progress;
    this.stage_progress = data.stage_progress;
    this.message = data.message;
    this.estimated_completion = data.estimated_completion;
    this.frames_processed = data.frames_processed;
    this.total_frames = data.total_frames;
    this.processing_rate_fps = data.processing_rate_fps;
    this.cpu_usage_percent = data.cpu_usage_percent;
    this.memory_usage_mb = data.memory_usage_mb;
    this.processing_efficiency = data.processing_efficiency;
    this.error_recovery_status = data.error_recovery_status;
    this.progress_history = data.progress_history || [];
    this.timestamp = data.timestamp;
  }

  /**
   * Validate status streaming event data
   * @param {Object} data - Status streaming data to validate
   * @returns {boolean} - True if valid
   */
  static validate(data) {
    return (
      data.event_type === EVENT_TYPES.STATUS_STREAMING &&
      typeof data.analysis_id === 'string' && data.analysis_id.length > 0 &&
      Object.values(ANALYSIS_STAGES).includes(data.current_stage) &&
      typeof data.overall_progress === 'number' && data.overall_progress >= 0 && data.overall_progress <= 1 &&
      typeof data.stage_progress === 'number' && data.stage_progress >= 0 && data.stage_progress <= 1 &&
      typeof data.message === 'string' && data.message.length > 0 &&
      (data.estimated_completion === null || typeof data.estimated_completion === 'string') &&
      typeof data.frames_processed === 'number' && data.frames_processed >= 0 &&
      typeof data.total_frames === 'number' && data.total_frames >= 0 &&
      (data.processing_rate_fps === null || (typeof data.processing_rate_fps === 'number' && data.processing_rate_fps >= 0)) &&
      (data.cpu_usage_percent === null || (typeof data.cpu_usage_percent === 'number' && data.cpu_usage_percent >= 0 && data.cpu_usage_percent <= 100)) &&
      (data.memory_usage_mb === null || (typeof data.memory_usage_mb === 'number' && data.memory_usage_mb >= 0)) &&
      (data.processing_efficiency === null || (typeof data.processing_efficiency === 'number' && data.processing_efficiency >= 0 && data.processing_efficiency <= 1)) &&
      (data.error_recovery_status === null || typeof data.error_recovery_status === 'object') &&
      Array.isArray(data.progress_history) &&
      typeof data.timestamp === 'string'
    );
  }

  /**
   * Get overall progress percentage for display
   * @returns {number} - Overall progress percentage (0-100)
   */
  getOverallProgressPercentage() {
    return Math.round(this.overall_progress * 100);
  }

  /**
   * Get stage progress percentage for display
   * @returns {number} - Stage progress percentage (0-100)
   */
  getStageProgressPercentage() {
    return Math.round(this.stage_progress * 100);
  }

  /**
   * Check if analysis is completed
   * @returns {boolean} - True if completed
   */
  isCompleted() {
    return this.current_stage === ANALYSIS_STAGES.COMPLETED;
  }

  /**
   * Check if analysis failed
   * @returns {boolean} - True if failed
   */
  isFailed() {
    return this.current_stage === ANALYSIS_STAGES.FAILED || 
           (this.error_recovery_status && this.error_recovery_status.has_errors);
  }

  /**
   * Get processing rate formatted string
   * @returns {string} - Formatted processing rate
   */
  getProcessingRateFormatted() {
    return this.processing_rate_fps ? `${this.processing_rate_fps.toFixed(1)} fps` : 'Calculating...';
  }

  /**
   * Get system resource status
   * @returns {Object} - System resource information
   */
  getSystemResourceStatus() {
    return {
      cpu: this.cpu_usage_percent ? `${this.cpu_usage_percent.toFixed(1)}%` : 'Unknown',
      memory: this.memory_usage_mb ? `${this.memory_usage_mb.toFixed(1)} MB` : 'Unknown',
      efficiency: this.processing_efficiency ? `${(this.processing_efficiency * 100).toFixed(1)}%` : 'Unknown'
    };
  }

  /**
   * Get error recovery status text
   * @returns {string} - Error recovery status text
   */
  getErrorRecoveryStatusText() {
    if (!this.error_recovery_status) return 'No errors';
    
    const { has_errors, error_count, retry_attempts, max_retries, is_recovering } = this.error_recovery_status;
    
    if (!has_errors) return 'No errors';
    if (is_recovering) return `Recovering (${retry_attempts}/${max_retries} attempts)`;
    if (retry_attempts >= max_retries) return `Failed after ${max_retries} attempts`;
    return `${error_count} error(s), ${retry_attempts}/${max_retries} retries`;
  }
}

/**
 * Utility functions for WebSocket message handling
 */
export const WebSocketUtils = {
  /**
   * Get stage display name
   * @param {AnalysisStage} stage - Analysis stage
   * @returns {string} - Display name
   */
  getStageDisplayName(stage) {
    const stageNames = {
      [ANALYSIS_STAGES.INITIALIZING]: 'Initializing',
      [ANALYSIS_STAGES.UPLOADING]: 'Uploading',
      [ANALYSIS_STAGES.FRAME_EXTRACTION]: 'Extracting Frames',
      [ANALYSIS_STAGES.FEATURE_EXTRACTION]: 'Extracting Features',
      [ANALYSIS_STAGES.MODEL_INFERENCE]: 'Running Analysis',
      [ANALYSIS_STAGES.POST_PROCESSING]: 'Post Processing',
      [ANALYSIS_STAGES.BLOCKCHAIN_SUBMISSION]: 'Submitting to Blockchain',
      [ANALYSIS_STAGES.COMPLETED]: 'Completed',
      [ANALYSIS_STAGES.FAILED]: 'Failed'
    };
    
    return stageNames[stage] || stage;
  },

  /**
   * Get stage description
   * @param {AnalysisStage} stage - Analysis stage
   * @returns {string} - Stage description
   */
  getStageDescription(stage) {
    const stageDescriptions = {
      [ANALYSIS_STAGES.INITIALIZING]: 'Preparing analysis environment',
      [ANALYSIS_STAGES.UPLOADING]: 'Uploading video file to server',
      [ANALYSIS_STAGES.FRAME_EXTRACTION]: 'Extracting frames from video',
      [ANALYSIS_STAGES.FEATURE_EXTRACTION]: 'Extracting features from frames',
      [ANALYSIS_STAGES.MODEL_INFERENCE]: 'Running deepfake detection models',
      [ANALYSIS_STAGES.POST_PROCESSING]: 'Processing analysis results',
      [ANALYSIS_STAGES.BLOCKCHAIN_SUBMISSION]: 'Submitting results to blockchain',
      [ANALYSIS_STAGES.COMPLETED]: 'Analysis completed successfully',
      [ANALYSIS_STAGES.FAILED]: 'Analysis failed'
    };
    
    return stageDescriptions[stage] || 'Processing...';
  },

  /**
   * Format time remaining
   * @param {string|null} estimatedCompletion - Estimated completion time
   * @returns {string} - Formatted time remaining
   */
  formatTimeRemaining(estimatedCompletion) {
    if (!estimatedCompletion) {
      return 'Calculating...';
    }
    
    try {
      const now = new Date();
      const completion = new Date(estimatedCompletion);
      const diffMs = completion.getTime() - now.getTime();
      
      if (diffMs <= 0) {
        return 'Almost done';
      }
      
      const diffSeconds = Math.floor(diffMs / 1000);
      const diffMinutes = Math.floor(diffSeconds / 60);
      const diffHours = Math.floor(diffMinutes / 60);
      
      if (diffHours > 0) {
        return `${diffHours}h ${diffMinutes % 60}m remaining`;
      } else if (diffMinutes > 0) {
        return `${diffMinutes}m ${diffSeconds % 60}s remaining`;
      } else {
        return `${diffSeconds}s remaining`;
      }
    } catch (error) {
      return 'Calculating...';
    }
  },

  /**
   * Get connection status display text
   * @param {ConnectionState} state - Connection state
   * @returns {string} - Display text
   */
  getConnectionStatusText(state) {
    const statusTexts = {
      [CONNECTION_STATES.CONNECTING]: 'Connecting...',
      [CONNECTION_STATES.CONNECTED]: 'Connected',
      [CONNECTION_STATES.DISCONNECTED]: 'Disconnected',
      [CONNECTION_STATES.RECONNECTING]: 'Reconnecting...',
      [CONNECTION_STATES.ERROR]: 'Connection Error'
    };
    
    return statusTexts[state] || 'Unknown';
  }
};

// Export all types and utilities
export default {
  ANALYSIS_STAGES,
  EVENT_TYPES,
  CONNECTION_STATES,
  SuspiciousRegion,
  StatusUpdate,
  ResultUpdate,
  ErrorEvent,
  HeartbeatEvent,
  ConnectionEstablishedEvent,
  StageTransitionEvent,
  StatusStreamingEvent,
  WebSocketMessageParser,
  WebSocketUtils
};
