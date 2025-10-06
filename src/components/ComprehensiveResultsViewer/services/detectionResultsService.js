/**
 * Detection Results Service
 * Enhanced service for caching, real-time updates, and comprehensive data integration
 */

import { detectionResultsApi } from '../../../api/detectionResultsApi';

// ============================================================================
// Service Configuration
// ============================================================================

const DEFAULT_CONFIG = {
  cacheTimeout: 300000, // 5 minutes
  websocketTimeout: 30000, // 30 seconds
  retryAttempts: 3,
  retryDelay: 1000,
  refreshInterval: 5000,
  enableCaching: true,
  enableRealTimeUpdates: true
};

// ============================================================================
// Cache Implementation
// ============================================================================

class DetectionResultsCache {
  constructor() {
    this.cache = new Map();
    this.timeouts = new Map();
    
    // Periodic cleanup
    setInterval(() => {
      this.cleanup();
    }, 60000); // Clean every minute
  }

  set(key, data, timeout = DEFAULT_CONFIG.cacheTimeout) {
    // Clear existing timeout
    if (this.timeouts.has(key)) {
      clearTimeout(this.timeouts.get(key));
    }

    // Store data with timestamp
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });

    // Set cleanup timeout
    const timeoutId = setTimeout(() => {
      this.cache.delete(key);
      this.timeouts.delete(key);
    }, timeout);

    this.timeouts.set(key, timeoutId);
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    return item.data;
  }

  has(key) {
    return this.cache.has(key);
  }

  delete(key) {
    if (this.timeouts.has(key)) {
      clearTimeout(this.timeouts.get(key));
      this.timeouts.delete(key);
    }
    return this.cache.delete(key);
  }

  cleanup() {
    const now = Date.now();
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > DEFAULT_CONFIG.cacheTimeout) {
        this.delete(key);
      }
    }
  }

  getCacheStats() {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
      timeoutCount: this.timeouts.size
    };
  }
}

// ============================================================================
// Main Service Class
// ============================================================================

class DetectionResultsService {
  constructor(config = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.cache = new DetectionResultsCache();
    this.activeWebSockets = new Map();
    this.subscribers = new Map();
  }

  // ============================================================================
  // Detection Results with Caching
  // ============================================================================

  async getDetectionResultsWithCache(analysisId, options = {}) {
    const cacheKey = `detection_results_${analysisId}`;
    
    // Check cache first
    if (options.enableCache !== false && this.cache.has(cacheKey)) {
      console.log('📦 Cache hit for detection results:', analysisId);
      return this.cache.get(cacheKey);
    }

    try {
      console.log('🌐 Fetching detection results:', analysisId);
      const results = await detectionResultsApi.getDetectionResult(analysisId);
      
      // Cache the results
      if (options.enableCache !== false) {
        this.cache.set(cacheKey, results, this.config.cacheTimeout);
      }

      // Notify subscribers
      this.notifySubscribers('detection_results_loaded', { analysisId, results });

      return results;
    } catch (error) {
      console.error('❌ Error fetching detection results:', error);
      throw new Error(`Failed to fetch detection results: ${error.message}`);
    }
  }

  async getFrameAnalysisData(analysisId, options = {}) {
    const cacheKey = `frame_analysis_${analysisId}`;
    
    // Check cache first
    if (options.enableCache !== false && this.cache.has(cacheKey)) {
      console.log('📦 Cache hit for frame analysis:', analysisId);
      return this.cache.get(cacheKey);
    }

    try {
      console.log('🌐 Fetching frame analysis data:', analysisId);
      
      // Simulate frame analysis data based on detection results
      const detectionData = await this.getDetectionResultsWithCache(analysisId, options);
      
      // Generate frame data (in real implementation, this would come from API)
      const frameData = this.generateFrameAnalysisData(detectionData);
      
      // Cache the results
      if (options.enableCache !== false) {
        this.cache.set(cacheKey, frameData, this.config.cacheTimeout);
      }

      // Notify subscribers
      this.notifySubscribers('frame_analysis_loaded', { analysisId, frameData });

      return frameData;
    } catch (error) {
      console.error('❌ Error fetching frame analysis:', error);
      throw new Error(`Failed to fetch frame analysis data: ${error.message}`);
    }
  }

  async getBlockchainVerificationStatus(analysisId, options = {}) {
    const cacheKey = `blockchain_status_${analysisId}`;
    
    // Check cache first
    if (options.enableCache !== false && this.cache.has(cacheKey)) {
      console.log('📦 Cache hit for blockchain status:', analysisId);
      return this.cache.get(cacheKey);
    }

    try {
      console.log('🌐 Fetching blockchain verification status:', analysisId);
      
      // Simulate blockchain status (in real implementation, this would come from API)
      const blockchainData = this.generateBlockchainStatus(analysisId);
      
      // Cache the results with shorter timeout for real-time data
      if (options.enableCache !== false) {
        this.cache.set(cacheKey, blockchainData, 60000); // 1 minute cache for blockchain
      }

      // Notify subscribers
      this.notifySubscribers('blockchain_status_updated', { analysisId, blockchainData });

      return blockchainData;
    } catch (error) {
      console.error('❌ Error fetching blockchain status:', error);
      throw new Error(`Failed to fetch blockchain verification status: ${error.message}`);
    }
  }

  // ============================================================================
  // Real-time Updates
  // ============================================================================

  subscribeToUpdates(analysisId, callback) {
    const subscriptionId = `${analysisId}_${Date.now()}`;
    
    if (!this.subscribers.has(analysisId)) {
      this.subscribers.set(analysisId, new Map());
    }
    
    this.subscribers.get(analysisId).set(subscriptionId, callback);
    
    console.log('📡 Subscribed to updates for analysis:', analysisId);
    
    // Start real-time updates if not already active
    this.startRealTimeUpdates(analysisId);
    
    return subscriptionId;
  }

  unsubscribeFromUpdates(analysisId, subscriptionId) {
    if (this.subscribers.has(analysisId)) {
      this.subscribers.get(analysisId).delete(subscriptionId);
      
      // Clean up if no more subscribers
      if (this.subscribers.get(analysisId).size === 0) {
        this.subscribers.delete(analysisId);
        this.stopRealTimeUpdates(analysisId);
      }
    }
    
    console.log('📡 Unsubscribed from updates for analysis:', analysisId);
  }

  startRealTimeUpdates(analysisId) {
    // Skip if already active
    if (this.activeWebSockets.has(analysisId)) {
      return;
  }

    console.log('🔄 Starting real-time updates for analysis:', analysisId);
    
    // Start periodic refresh
    const refreshInterval = setInterval(async () => {
      try {
        await this.refreshDetectionResults(analysisId);
      } catch (error) {
        console.warn('Real-time refresh failed:', error.message);
      }
    }, this.config.refreshInterval);

    this.activeWebSockets.set(analysisId, {
      refreshInterval,
      startTime: Date.now()
    });
  }

  stopRealTimeUpdates(analysisId) {
    const websocketData = this.activeWebSockets.get(analysisId);
    if (websocketData) {
      clearInterval(websocketData.refreshInterval);
      this.activeWebSockets.delete(analysisId);
      console.log('🛑 Stopped real-time updates for analysis:', analysisId);
    }
  }

  async refreshDetectionResults(analysisId) {
    try {
      // Refresh without cache
      const refreshedResults = await this.getDetectionResultsWithCache(analysisId, { enableCache: false });
      
      // Update cache with fresh data
      const cacheKey = `detection_results_${analysisId}`;
      this.cache.set(cacheKey, refreshedResults);
      
      // Notify subscribers
      this.notifySubscribers('detection_results_updated', { analysisId, results: refreshedResults });
      
      return refreshedResults;
    } catch (error) {
      console.warn('Refresh failed:', error.message);
      throw error;
    }
  }

  // ============================================================================
  // Data Generation Helpers (Simulated)
  // ============================================================================

  generateFrameAnalysisData(detectionResults) {
    const totalFrames = Math.floor(Math.random() * 500) + 100; // 100-600 frames
    const frames = [];

    for (let i = 0; i < totalFrames; i++) {
      const baseConfidence = detectionResults.confidence_height || 0.5;
      const variation = (Math.random() - 0.5) * 0.3; // ±15% variation
      const confidence = Math.max(0, Math.min(1, baseConfidence + variation));

      frames.push({
        frame_number: i,
        confidence_score: confidence,
        suspicious_regions: this.generateSuspiciousRegions(confidence),
        artifacts: this.generateArtifacts(confidence),
        processing_time_ms: Math.floor(Math.random() * 50) + 10
      });
    }

    return frames;
  }

  generateSuspiciousRegions(confidence) {
    if (confidence < 0.6) return [];

    const regionCount = confidence > 0.8 ? Math.floor(Math.random() * 3) + 1 : 1;
    const regions = [];

    for (let i = 0; i < regionCount; i++) {
      regions.push({
        x: Math.floor(Math.random() * 800) + 50,
        y: Math.floor(Math.random() * 600) + 50,
        width: Math.floor(Math.random() * 100) + 30,
        height: Math.floor(Math.random() * 80) + 20,
        confidence: confidence * 100,
        description: `Face manipulation artifacts ${i + 1}`,
        artifact_type: 'deepfake_face_synthesis'
      });
    }

    return regions;
  }

  generateArtifacts(confidence) {
    const artifactTypes = ['face_swap', 'lip_sync', 'gesture_modification', 'background_change'];
    
    return {
      detection_type: artifactTypes[Math.floor(Math.random() * artifactTypes.length)],
      confidence_level: confidence > 0.8 ? 'high' : confidence > 0.5 ? 'medium' : 'low',
      processing_info: {
        model_version: '2.1.3',
        timestamp: new Date().toISOString()
      }
    };
  }

  generateBlockchainStatus(analysisId) {
    const statuses = ['verified', 'pending', 'failed'];
    const status = Math.random() > 0.2 ? 'verified' : statuses[Math.floor(Math.random() * statuses.length)];

    return {
      analysis_id: analysisId,
      status,
      progress: status === 'verified' ? 100 : Math.floor(Math.random() * 90) + 10,
      hash_value: this.generateHash(),
      verification_time_ms: status === 'verified' ? Math.floor(Math.random() * 5000) + 1000 : null,
      network: 'ethereum',
      gas_used: Math.floor(Math.random() * 50000) + 20000,
      token_cost: Math.random() * 0.01 + 0.005,
      node_agreement_percentage: Math.floor(Math.random() * 20) + 80
    };
  }

  generateHash() {
    const chars = '0123456789abcdef';
    let hash = '0x';
    for (let i = 0; i < 64; i++) {
      hash += chars[Math.floor(Math.random() * chars.length)];
    }
    return hash;
  }

  // ============================================================================
  // Notification System
  // ============================================================================

  notifySubscribers(eventType, data) {
    const { analysisId } = data;
    
    if (this.subscribers.has(analysisId)) {
      const subscribers = this.subscribers.get(analysisId);
      
      subscribers.forEach((callback) => {
        try {
          callback(eventType, data);
        } catch (error) {
          console.error('Error in subscriber callback:', error);
        }
      });
    }
  }

  // ============================================================================
  // Cache Management
  // ============================================================================

  clearCache(analysisId = null) {
    if (analysisId) {
      this.cache.delete(`detection_results_${analysisId}`);
      this.cache.delete(`frame_analysis_${analysisId}`);
      this.cache.delete(`blockchain_status_${analysisId}`);
      console.log('🗑️ Cleared cache for analysis:', analysisId);
    } else {
      this.cache = new DetectionResultsCache();
      console.log('🗑️ Cleared entire cache');
    }
  }

  getCacheStats() {
    return {
      ...this.cache.getCacheStats(),
      activeSubscribers: Array.from(this.subscribers.keys()).length,
      activeWebSockets: this.activeWebSockets.size
    };
  }

  // ============================================================================
  // Export and Utilities
  // ============================================================================

  async exportDetectionResults(analysisId, format = 'json') {
    try {
      const results = await this.getDetectionResultsWithCache(analysisId, { enableCache: false });
      const frameData = await this.getFrameAnalysisData(analysisId, { enableCache: false });
      const blockchainData = await this.getBlockchainVerificationStatus(analysisId, { enableCache: false });

      const exportData = {
        analysis: results,
        frames: frameData,
        blockchain: blockchainData,
        exported_at: new Date().toISOString(),
        format
      };

      return exportData;
    } catch (error) {
      throw new Error(`Failed to export detection results: ${error.message}`);
    }
  }

  destroy() {
    // Clear all intervals
    this.activeWebSockets.forEach((data) => {
      clearInterval(data.refreshInterval);
    });
    this.activeWebSockets.clear();
    
    // Clear cache
    this.cache = new DetectionResultsCache();
    
    console.log('💥 DetectionResultsService destroyed');
  }
}

// ============================================================================
// Export Singleton Instance
// ============================================================================

const detectionResultsService = new DetectionResultsService();

export { DetectionResultsService, detectionResultsService };
export default detectionResultsService;
