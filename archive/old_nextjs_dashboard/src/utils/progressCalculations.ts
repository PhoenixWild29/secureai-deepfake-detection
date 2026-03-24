/**
 * Progress Calculation Utilities
 * Handles time calculations, debouncing, and progress estimation
 */

import { 
  ProgressState, 
  StatusUpdate, 
  ProcessingStage, 
  FrameProgressData,
  STAGE_CONFIGS 
} from '@/types/progress';

export interface TimeEstimate {
  /** Elapsed time in milliseconds */
  elapsed: number;
  /** Estimated remaining time in milliseconds */
  remaining: number;
  /** Estimated completion time */
  completionTime: Date | null;
  /** Confidence in the estimate (0-1) */
  confidence: number;
}

export interface DebouncedUpdate {
  /** Debounced progress state */
  state: ProgressState;
  /** Whether this is a debounced update */
  isDebounced: boolean;
  /** Original update timestamp */
  originalTimestamp: Date;
}

/**
 * Debounce utility for high-frequency updates
 */
export class Debouncer<T> {
  private timeoutId: NodeJS.Timeout | null = null;
  private lastValue: T | null = null;
  private delay: number;

  constructor(delay: number) {
    this.delay = delay;
  }

  /**
   * Debounce a function call
   */
  public debounce(callback: (value: T) => void, value: T): void {
    this.lastValue = value;
    
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }

    this.timeoutId = setTimeout(() => {
      if (this.lastValue !== null) {
        callback(this.lastValue);
        this.lastValue = null;
      }
      this.timeoutId = null;
    }, this.delay);
  }

  /**
   * Cancel pending debounced call
   */
  public cancel(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    this.lastValue = null;
  }

  /**
   * Flush pending debounced call immediately
   */
  public flush(callback: (value: T) => void): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    
    if (this.lastValue !== null) {
      callback(this.lastValue);
      this.lastValue = null;
    }
  }
}

/**
 * Progress calculation utilities
 */
export class ProgressCalculator {
  private stageStartTimes: Map<ProcessingStage, Date> = new Map();
  private stageProgressHistory: Map<ProcessingStage, number[]> = new Map();

  /**
   * Calculate time estimates based on current progress
   */
  public calculateTimeEstimate(
    state: ProgressState,
    currentUpdate: StatusUpdate
  ): TimeEstimate {
    const now = new Date();
    const elapsed = state.startTime ? now.getTime() - state.startTime.getTime() : 0;
    
    if (!state.startTime || state.overallProgress === 0) {
      return {
        elapsed,
        remaining: 0,
        completionTime: null,
        confidence: 0,
      };
    }

    // Calculate remaining time based on current progress rate
    const progressRate = state.overallProgress / elapsed; // progress per millisecond
    const remainingProgress = 100 - state.overallProgress;
    const estimatedRemaining = progressRate > 0 ? remainingProgress / progressRate : 0;

    // Apply confidence based on progress consistency
    const confidence = this.calculateEstimateConfidence(state, currentUpdate);

    // Adjust estimate based on stage-specific data
    const stageAdjustedRemaining = this.adjustEstimateForStage(
      state.currentStage,
      estimatedRemaining,
      state.stageProgress
    );

    const completionTime = new Date(now.getTime() + stageAdjustedRemaining);

    return {
      elapsed,
      remaining: stageAdjustedRemaining,
      completionTime,
      confidence,
    };
  }

  /**
   * Calculate confidence in time estimate
   */
  private calculateEstimateConfidence(
    state: ProgressState,
    currentUpdate: StatusUpdate
  ): number {
    let confidence = 0.5; // Base confidence

    // Increase confidence if we have enough progress history
    const history = this.stageProgressHistory.get(state.currentStage) || [];
    if (history.length > 5) {
      confidence += 0.2;
    }

    // Increase confidence if progress is consistent
    if (history.length > 2) {
      const recentProgress = history.slice(-3);
      const isConsistent = recentProgress.every((progress, index) => {
        if (index === 0) return true;
        return progress >= recentProgress[index - 1];
      });
      
      if (isConsistent) {
        confidence += 0.2;
      }
    }

    // Decrease confidence if progress is stalled
    if (state.lastUpdate && Date.now() - state.lastUpdate.getTime() > 30000) {
      confidence -= 0.3;
    }

    return Math.max(0, Math.min(1, confidence));
  }

  /**
   * Adjust time estimate based on current stage
   */
  private adjustEstimateForStage(
    stage: ProcessingStage,
    baseEstimate: number,
    stageProgress: number
  ): number {
    const stageConfig = STAGE_CONFIGS[stage];
    if (!stageConfig) {
      return baseEstimate;
    }

    // Use stage-specific estimated duration as a fallback
    const stageRemaining = (100 - stageProgress) / 100 * stageConfig.estimatedDuration;
    
    // Blend base estimate with stage-specific estimate
    const weight = Math.min(stageProgress / 50, 1); // More weight to base estimate as stage progresses
    return baseEstimate * weight + stageRemaining * (1 - weight);
  }

  /**
   * Update progress state with new status update
   */
  public updateProgressState(
    currentState: ProgressState,
    update: StatusUpdate
  ): ProgressState {
    const now = new Date();
    const newState = { ...currentState };

    // Update basic progress data
    newState.sessionId = update.sessionId;
    newState.currentStage = update.stage;
    newState.overallProgress = update.progress;
    newState.stageProgress = update.stageProgress;
    newState.lastUpdate = now;
    newState.error = update.error || null;

    // Initialize start time if this is the first update
    if (!newState.startTime && update.stage !== 'completed' && update.stage !== 'error') {
      newState.startTime = now;
    }

    // Track stage transitions
    if (currentState.currentStage !== update.stage) {
      this.stageStartTimes.set(update.stage, now);
      this.stageProgressHistory.set(update.stage, []);
    }

    // Update stage progress history
    const history = this.stageProgressHistory.get(update.stage) || [];
    history.push(update.stageProgress);
    if (history.length > 10) {
      history.shift(); // Keep only last 10 updates
    }
    this.stageProgressHistory.set(update.stage, history);

    // Update frame progress if provided
    if (update.metadata?.frameProgress) {
      newState.frameProgress = this.updateFrameProgress(
        newState.frameProgress,
        update.metadata.frameProgress
      );
    }

    // Calculate time estimates
    const timeEstimate = this.calculateTimeEstimate(newState, update);
    newState.estimatedCompletion = timeEstimate.completionTime;

    // Update processing status
    newState.isActive = update.stage !== 'completed' && update.stage !== 'error';

    return newState;
  }

  /**
   * Update frame-level progress data
   */
  private updateFrameProgress(
    currentFrameProgress: FrameProgressData[],
    frameUpdates: any[]
  ): FrameProgressData[] {
    const frameMap = new Map(currentFrameProgress.map(fp => [fp.frameIndex, fp]));
    
    frameUpdates.forEach((frameUpdate: any) => {
      const existing = frameMap.get(frameUpdate.frameIndex);
      frameMap.set(frameUpdate.frameIndex, {
        frameIndex: frameUpdate.frameIndex,
        status: frameUpdate.status || 'processing',
        progress: frameUpdate.progress || 0,
        startTime: frameUpdate.startTime ? new Date(frameUpdate.startTime) : existing?.startTime,
        endTime: frameUpdate.endTime ? new Date(frameUpdate.endTime) : existing?.endTime,
        error: frameUpdate.error || existing?.error,
      });
    });

    return Array.from(frameMap.values()).sort((a, b) => a.frameIndex - b.frameIndex);
  }

  /**
   * Format time duration for display
   */
  public formatDuration(milliseconds: number): string {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }

  /**
   * Format progress percentage
   */
  public formatProgress(progress: number): string {
    return `${Math.round(progress)}%`;
  }

  /**
   * Get stage display information
   */
  public getStageInfo(stage: ProcessingStage) {
    return STAGE_CONFIGS[stage] || {
      id: stage,
      name: stage.replace(/_/g, ' ').toUpperCase(),
      description: 'Processing stage',
      icon: 'cog',
      estimatedDuration: 0,
      skippable: false,
      dependencies: [],
    };
  }

  /**
   * Check if stage transition is valid
   */
  public isValidStageTransition(from: ProcessingStage, to: ProcessingStage): boolean {
    const toConfig = STAGE_CONFIGS[to];
    if (!toConfig) return false;

    return toConfig.dependencies.includes(from) || toConfig.dependencies.length === 0;
  }

  /**
   * Reset calculator state
   */
  public reset(): void {
    this.stageStartTimes.clear();
    this.stageProgressHistory.clear();
  }
}

/**
 * Create debounced progress updater
 */
export const createDebouncedProgressUpdater = (
  delay: number,
  onUpdate: (state: ProgressState) => void
) => {
  const debouncer = new Debouncer<ProgressState>(delay);
  const calculator = new ProgressCalculator();

  return {
    /**
     * Update progress with debouncing
     */
    update: (currentState: ProgressState, update: StatusUpdate) => {
      const newState = calculator.updateProgressState(currentState, update);
      
      debouncer.debounce((state) => {
        onUpdate({
          ...state,
          // Mark as debounced for UI purposes
        } as ProgressState & { isDebounced: boolean });
      }, newState);
    },

    /**
     * Flush pending updates immediately
     */
    flush: () => {
      debouncer.flush((state) => {
        onUpdate({
          ...state,
          // Mark as debounced for UI purposes
        } as ProgressState & { isDebounced: boolean });
      });
    },

    /**
     * Cancel pending updates
     */
    cancel: () => {
      debouncer.cancel();
    },

    /**
     * Get calculator instance
     */
    getCalculator: () => calculator,
  };
};

export default ProgressCalculator;
