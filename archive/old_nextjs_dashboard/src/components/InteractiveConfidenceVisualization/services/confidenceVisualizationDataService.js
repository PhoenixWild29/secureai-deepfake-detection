/**
 * Confidence Visualization Data Service
 * Service for data fetching, processing, and client-side caching for confidence visualization
 */

// ============================================================================
// Service Configuration
// ============================================================================

const DEFAULT_CONFIG = {
  cacheTimeout: 300000, // 5 minutes
  maxCacheSize: 50, // Maximum number of cached analyses
  enableCompression: true,
  enableVirtualization: true,
  maxDataPoints: 1000,
  frameRate: 30
};

// ============================================================================
// Cache Implementation
// ============================================================================

class ConfidenceDataCache {
  constructor() {
    this.cache = new Map();
    this.accessTimes = new Map();
    this.maxSize = DEFAULT_CONFIG.maxCacheSize;
  }

  set(key, data, timeout = DEFAULT_CONFIG.cacheTimeout) {
    // Remove oldest entries if cache is full
    if (this.cache.size >= this.maxSize) {
      this.evictOldest();
    }

    this.cache.set(key, {
      data: this.compressData(data),
      timestamp: Date.now(),
      timeout
    });
    this.accessTimes.set(key, Date.now());
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    // Check if expired
    if (Date.now() - item.timestamp > item.timeout) {
      this.cache.delete(key);
      this.accessTimes.delete(key);
      return null;
    }

    // Update access time
    this.accessTimes.set(key, Date.now());
    
    return this.decompressData(item.data);
  }

  has(key) {
    return this.cache.has(key) && !this.isExpired(key);
  }

  delete(key) {
    this.cache.delete(key);
    this.accessTimes.delete(key);
  }

  clear() {
    this.cache.clear();
    this.accessTimes.clear();
  }

  isExpired(key) {
    const item = this.cache.get(key);
    if (!item) return true;
    return Date.now() - item.timestamp > item.timeout;
  }

  evictOldest() {
    let oldestKey = null;
    let oldestTime = Infinity;

    for (const [key, time] of this.accessTimes.entries()) {
      if (time < oldestTime) {
        oldestTime = time;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.delete(oldestKey);
    }
  }

  compressData(data) {
    if (!DEFAULT_CONFIG.enableCompression) return data;
    
    // Simple compression by removing unnecessary precision
    return JSON.parse(JSON.stringify(data, (key, value) => {
      if (typeof value === 'number') {
        return Math.round(value * 1000) / 1000; // 3 decimal places
      }
      return value;
    }));
  }

  decompressData(data) {
    return data; // No decompression needed for simple precision reduction
  }

  getStats() {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      keys: Array.from(this.cache.keys())
    };
  }
}

// ============================================================================
// Data Processing Utilities
// ============================================================================

/**
 * Process raw frame data into confidence visualization format
 */
const processFrameData = (frameData, options = {}) => {
  if (!frameData || frameData.length === 0) {
    return {
      rawData: [],
      processedData: [],
      statistics: null,
      metadata: {
        totalFrames: 0,
        timeRange: { start: 0, end: 0 },
        confidenceRange: { min: 0, max: 1 }
      }
    };
  }

  const {
    frameRate = DEFAULT_CONFIG.frameRate,
    confidenceThresholds = { low: 0.0, medium: 0.4, high: 0.7, critical: 0.9 },
    enableVirtualization = DEFAULT_CONFIG.enableVirtualization,
    maxDataPoints = DEFAULT_CONFIG.maxDataPoints
  } = options;

  // Convert frame data to confidence points
  let rawData = frameData.map((frame, index) => ({
    frameNumber: frame.frame_number || index,
    confidence: frame.confidence_score || 0,
    timestamp: (frame.frame_number || index) / frameRate,
    algorithm: frame.algorithm || 'default',
    suspiciousRegions: frame.suspicious_regions || [],
    artifacts: frame.artifacts || {},
    processingTime: frame.processing_time_ms || 0
  }));

  // Apply virtualization if needed
  let processedData = rawData;
  if (enableVirtualization && rawData.length > maxDataPoints) {
    processedData = virtualizeData(rawData, maxDataPoints);
  }

  // Calculate statistics
  const statistics = calculateStatistics(processedData, confidenceThresholds);

  // Calculate metadata
  const metadata = {
    totalFrames: frameData.length,
    processedFrames: processedData.length,
    timeRange: {
      start: Math.min(...processedData.map(p => p.timestamp)),
      end: Math.max(...processedData.map(p => p.timestamp))
    },
    confidenceRange: {
      min: Math.min(...processedData.map(p => p.confidence)),
      max: Math.max(...processedData.map(p => p.confidence))
    },
    frameRate,
    processingOptions: options
  };

  return {
    rawData,
    processedData,
    statistics,
    metadata
  };
};

/**
 * Virtualize data for performance with large datasets
 */
const virtualizeData = (data, maxPoints) => {
  if (data.length <= maxPoints) return data;

  const step = Math.ceil(data.length / maxPoints);
  const virtualized = [];

  for (let i = 0; i < data.length; i += step) {
    const chunk = data.slice(i, i + step);
    
    // Take the most representative point from each chunk
    const representative = chunk.reduce((best, current) => {
      // Prefer points with higher confidence or more interesting data
      const currentScore = current.confidence + (current.suspiciousRegions.length * 0.1);
      const bestScore = best.confidence + (best.suspiciousRegions.length * 0.1);
      
      return currentScore > bestScore ? current : best;
    });

    virtualized.push(representative);
  }

  return virtualized;
};

/**
 * Calculate comprehensive statistics
 */
const calculateStatistics = (data, thresholds) => {
  if (data.length === 0) {
    return {
      mean: 0,
      median: 0,
      standardDeviation: 0,
      distribution: { low: 0, medium: 0, high: 0, critical: 0 },
      trends: { increasing: 0, decreasing: 0, stable: 0 },
      peaks: [],
      valleys: []
    };
  }

  const confidences = data.map(p => p.confidence);
  const sortedConfidences = [...confidences].sort((a, b) => a - b);

  // Basic statistics
  const mean = confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length;
  const median = sortedConfidences[Math.floor(sortedConfidences.length / 2)];
  
  const variance = confidences.reduce((sum, conf) => sum + Math.pow(conf - mean, 2), 0) / confidences.length;
  const standardDeviation = Math.sqrt(variance);

  // Distribution by thresholds
  const distribution = confidences.reduce((acc, conf) => {
    if (conf >= thresholds.critical) acc.critical++;
    else if (conf >= thresholds.high) acc.high++;
    else if (conf >= thresholds.medium) acc.medium++;
    else acc.low++;
    return acc;
  }, { low: 0, medium: 0, high: 0, critical: 0 });

  // Trend analysis
  const trends = analyzeTrends(data);

  // Peak and valley detection
  const { peaks, valleys } = detectPeaksAndValleys(data);

  return {
    mean,
    median,
    standardDeviation,
    distribution,
    trends,
    peaks,
    valleys,
    min: Math.min(...confidences),
    max: Math.max(...confidences),
    range: Math.max(...confidences) - Math.min(...confidences)
  };
};

/**
 * Analyze confidence trends
 */
const analyzeTrends = (data) => {
  if (data.length < 2) {
    return { increasing: 0, decreasing: 0, stable: 0 };
  }

  let increasing = 0;
  let decreasing = 0;
  let stable = 0;

  for (let i = 1; i < data.length; i++) {
    const diff = data[i].confidence - data[i - 1].confidence;
    const threshold = 0.01; // 1% threshold for trend detection

    if (diff > threshold) increasing++;
    else if (diff < -threshold) decreasing++;
    else stable++;
  }

  const total = data.length - 1;
  return {
    increasing: increasing / total,
    decreasing: decreasing / total,
    stable: stable / total
  };
};

/**
 * Detect peaks and valleys in confidence data
 */
const detectPeaksAndValleys = (data, threshold = 0.05) => {
  const peaks = [];
  const valleys = [];

  for (let i = 1; i < data.length - 1; i++) {
    const prev = data[i - 1].confidence;
    const curr = data[i].confidence;
    const next = data[i + 1].confidence;

    // Peak detection
    if (curr > prev && curr > next && (curr - Math.max(prev, next)) > threshold) {
      peaks.push({
        ...data[i],
        type: 'peak',
        prominence: curr - Math.max(prev, next)
      });
    }

    // Valley detection
    if (curr < prev && curr < next && (Math.min(prev, next) - curr) > threshold) {
      valleys.push({
        ...data[i],
        type: 'valley',
        prominence: Math.min(prev, next) - curr
      });
    }
  }

  return { peaks, valleys };
};

/**
 * Generate comparative data for different algorithms or time periods
 */
const generateComparativeData = (data, comparisonType = 'algorithm') => {
  const groups = {};

  data.forEach(point => {
    const key = comparisonType === 'algorithm' ? point.algorithm : 
                comparisonType === 'time_period' ? Math.floor(point.timestamp / 60) : // Group by minute
                'default';

    if (!groups[key]) {
      groups[key] = [];
    }
    groups[key].push(point);
  });

  const comparativeData = {};
  Object.entries(groups).forEach(([key, points]) => {
    const stats = calculateStatistics(points);
    comparativeData[key] = {
      points,
      statistics: stats,
      metadata: {
        count: points.length,
        timeRange: {
          start: Math.min(...points.map(p => p.timestamp)),
          end: Math.max(...points.map(p => p.timestamp))
        }
      }
    };
  });

  return comparativeData;
};

// ============================================================================
// Main Service Class
// ============================================================================

class ConfidenceVisualizationDataService {
  constructor() {
    this.cache = new ConfidenceDataCache();
    this.processingQueue = new Map();
  }

  /**
   * Get cached confidence data
   */
  async getCachedConfidenceData(analysisId) {
    const cacheKey = `confidence_${analysisId}`;
    return this.cache.get(cacheKey);
  }

  /**
   * Cache confidence data
   */
  async cacheConfidenceData(analysisId, data, timeout = DEFAULT_CONFIG.cacheTimeout) {
    const cacheKey = `confidence_${analysisId}`;
    this.cache.set(cacheKey, data, timeout);
  }

  /**
   * Process frame data for visualization
   */
  async processFrameData(frameData, options = {}) {
    const processingId = `processing_${Date.now()}_${Math.random()}`;
    
    try {
      this.processingQueue.set(processingId, { status: 'processing', startTime: Date.now() });
      
      const result = processFrameData(frameData, options);
      
      this.processingQueue.delete(processingId);
      return result;
    } catch (error) {
      this.processingQueue.delete(processingId);
      throw new Error(`Failed to process frame data: ${error.message}`);
    }
  }

  /**
   * Generate trend analysis data
   */
  async generateTrendAnalysis(data, trendType = 'moving_average', parameters = {}) {
    const {
      period = 10,
      threshold = 0.1,
      algorithm = 'simple'
    } = parameters;

    switch (trendType) {
      case 'moving_average':
        return this.calculateMovingAverage(data, period);
      
      case 'exponential_smoothing':
        return this.calculateExponentialSmoothing(data, parameters.alpha || 0.3);
      
      case 'linear_regression':
        return this.calculateLinearRegression(data);
      
      case 'peak_valley':
        return detectPeaksAndValleys(data, threshold);
      
      default:
        return this.calculateMovingAverage(data, period);
    }
  }

  /**
   * Calculate moving average
   */
  calculateMovingAverage(data, period) {
    if (data.length < period) return data;

    const result = [];
    for (let i = 0; i < data.length; i++) {
      const start = Math.max(0, i - period + 1);
      const slice = data.slice(start, i + 1);
      const average = slice.reduce((sum, point) => sum + point.confidence, 0) / slice.length;
      
      result.push({
        ...data[i],
        confidence: average,
        isMovingAverage: true,
        period
      });
    }

    return result;
  }

  /**
   * Calculate exponential smoothing
   */
  calculateExponentialSmoothing(data, alpha = 0.3) {
    if (data.length === 0) return [];

    const result = [{ ...data[0], confidence: data[0].confidence, isExponentialSmoothing: true }];
    
    for (let i = 1; i < data.length; i++) {
      const smoothed = alpha * data[i].confidence + (1 - alpha) * result[i - 1].confidence;
      result.push({
        ...data[i],
        confidence: smoothed,
        isExponentialSmoothing: true,
        alpha
      });
    }

    return result;
  }

  /**
   * Calculate linear regression
   */
  calculateLinearRegression(data) {
    if (data.length < 2) return data;

    const n = data.length;
    const xValues = data.map((_, index) => index);
    const yValues = data.map(point => point.confidence);

    // Calculate means
    const xMean = xValues.reduce((sum, x) => sum + x, 0) / n;
    const yMean = yValues.reduce((sum, y) => sum + y, 0) / n;

    // Calculate slope and intercept
    let numerator = 0;
    let denominator = 0;

    for (let i = 0; i < n; i++) {
      const xDiff = xValues[i] - xMean;
      numerator += xDiff * (yValues[i] - yMean);
      denominator += xDiff * xDiff;
    }

    const slope = denominator === 0 ? 0 : numerator / denominator;
    const intercept = yMean - slope * xMean;

    // Generate regression line
    return data.map((point, index) => ({
      ...point,
      confidence: slope * index + intercept,
      isLinearRegression: true,
      slope,
      intercept
    }));
  }

  /**
   * Generate comparative analysis
   */
  async generateComparativeAnalysis(data, comparisonType = 'algorithm') {
    return generateComparativeData(data, comparisonType);
  }

  /**
   * Export chart data for report generation
   */
  async exportChartData(data, format = 'json', options = {}) {
    const {
      includeStatistics = true,
      includeMetadata = true,
      includeRawData = false,
      resolution = { width: 1920, height: 1080 }
    } = options;

    const exportData = {
      chartData: data.processedData || data,
      metadata: includeMetadata ? data.metadata : undefined,
      statistics: includeStatistics ? data.statistics : undefined,
      rawData: includeRawData ? data.rawData : undefined,
      exportInfo: {
        format,
        resolution,
        exportedAt: new Date().toISOString(),
        version: '1.0'
      }
    };

    switch (format) {
      case 'json':
        return JSON.stringify(exportData, null, 2);
      
      case 'csv':
        return this.convertToCSV(data.processedData || data);
      
      case 'png':
        return this.generateChartImage(data, resolution);
      
      default:
        return exportData;
    }
  }

  /**
   * Convert data to CSV format
   */
  convertToCSV(data) {
    if (!data || data.length === 0) return '';

    const headers = ['frameNumber', 'confidence', 'timestamp', 'algorithm'];
    const rows = data.map(point => [
      point.frameNumber,
      point.confidence,
      point.timestamp,
      point.algorithm || 'default'
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
  }

  /**
   * Generate chart image (placeholder - would integrate with chart library)
   */
  generateChartImage(data, resolution) {
    // This would integrate with a chart library to generate PNG
    // For now, return a placeholder
    return {
      type: 'image/png',
      data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
      resolution
    };
  }

  /**
   * Clear cache
   */
  clearCache(analysisId = null) {
    if (analysisId) {
      this.cache.delete(`confidence_${analysisId}`);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    return this.cache.getStats();
  }

  /**
   * Get processing queue status
   */
  getProcessingStatus() {
    return Array.from(this.processingQueue.entries()).map(([id, status]) => ({
      id,
      ...status,
      duration: Date.now() - status.startTime
    }));
  }
}

// ============================================================================
// Export Singleton Instance
// ============================================================================

const confidenceVisualizationDataService = new ConfidenceVisualizationDataService();

export { ConfidenceVisualizationDataService, confidenceVisualizationDataService };
export default confidenceVisualizationDataService;
