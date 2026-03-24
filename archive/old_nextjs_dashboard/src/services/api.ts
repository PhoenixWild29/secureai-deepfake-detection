/**
 * Intelligent API Caching Service
 * Advanced caching strategies with configurable invalidation policies and offline support
 */

import { measureApiCall } from './performanceMonitor';

// Cache configuration types
export interface CacheConfig {
  ttl: number; // Time to live in milliseconds
  maxSize: number; // Maximum number of items
  strategy: CacheStrategy;
  invalidationPolicy: InvalidationPolicy;
  enableOfflineSupport: boolean;
  enableBackgroundRefresh: boolean;
  enableCompression: boolean;
}

export type CacheStrategy = 'lru' | 'lfu' | 'fifo' | 'ttl';
export type InvalidationPolicy = 'immediate' | 'lazy' | 'time-based' | 'manual';

// Cache entry types
export interface CacheEntry<T = any> {
  key: string;
  data: T;
  timestamp: number;
  lastAccessed: number;
  accessCount: number;
  size: number;
  compressed: boolean;
  metadata: Record<string, any>;
}

export interface CacheStats {
  hits: number;
  misses: number;
  size: number;
  maxSize: number;
  hitRate: number;
  memoryUsage: number;
  oldestEntry: number;
  newestEntry: number;
}

// API request types
export interface ApiRequest {
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: any;
  params?: Record<string, any>;
  cacheKey?: string;
  cacheConfig?: Partial<CacheConfig>;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  headers: Record<string, string>;
  timestamp: number;
  fromCache: boolean;
  cacheKey: string;
}

// Cache invalidation patterns
export interface InvalidationPattern {
  pattern: string;
  type: 'exact' | 'prefix' | 'suffix' | 'regex';
  priority: number;
}

// Intelligent API caching service class
export class IntelligentApiCache {
  private cache: Map<string, CacheEntry> = new Map();
  private config: CacheConfig;
  private stats: CacheStats;
  private invalidationPatterns: InvalidationPattern[] = [];
  private backgroundRefreshQueue: Set<string> = new Set();
  private compressionEnabled: boolean = false;

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = {
      ttl: 5 * 60 * 1000, // 5 minutes
      maxSize: 1000,
      strategy: 'lru',
      invalidationPolicy: 'lazy',
      enableOfflineSupport: true,
      enableBackgroundRefresh: true,
      enableCompression: false,
      ...config,
    };

    this.stats = {
      hits: 0,
      misses: 0,
      size: 0,
      maxSize: this.config.maxSize,
      hitRate: 0,
      memoryUsage: 0,
      oldestEntry: 0,
      newestEntry: 0,
    };

    this.compressionEnabled = this.config.enableCompression && this.isCompressionSupported();

    // Start background refresh if enabled
    if (this.config.enableBackgroundRefresh) {
      this.startBackgroundRefresh();
    }

    // Start cleanup interval
    this.startCleanupInterval();
  }

  /**
   * Make API request with intelligent caching
   */
  public async request<T>(request: ApiRequest): Promise<ApiResponse<T>> {
    const cacheKey = this.generateCacheKey(request);
    const cachedResponse = this.get<T>(cacheKey);

    // Return cached response if available and valid
    if (cachedResponse && this.isValid(cachedResponse)) {
      this.stats.hits++;
      this.updateStats();
      
      // Background refresh if enabled
      if (this.config.enableBackgroundRefresh && this.shouldBackgroundRefresh(cachedResponse)) {
        this.backgroundRefreshQueue.add(cacheKey);
      }

      return {
        data: cachedResponse.data,
        status: 200,
        headers: {},
        timestamp: cachedResponse.timestamp,
        fromCache: true,
        cacheKey,
      };
    }

    // Make actual API request
    this.stats.misses++;
    this.updateStats();

    try {
      const response = await measureApiCall(async () => {
        const url = this.buildUrl(request.url, request.params);
        const fetchOptions: RequestInit = {
          method: request.method,
          headers: {
            'Content-Type': 'application/json',
            ...request.headers,
          },
        };

        if (request.body) {
          fetchOptions.body = JSON.stringify(request.body);
        }

        return fetch(url, fetchOptions);
      }, request.url);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const responseHeaders: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });

      const apiResponse: ApiResponse<T> = {
        data,
        status: response.status,
        headers: responseHeaders,
        timestamp: Date.now(),
        fromCache: false,
        cacheKey,
      };

      // Cache the response
      this.set(cacheKey, data, request.cacheConfig);

      return apiResponse;
    } catch (error) {
      // Return cached response if available (offline support)
      if (cachedResponse && this.config.enableOfflineSupport) {
        console.warn('API request failed, returning cached data:', error);
        return {
          data: cachedResponse.data,
          status: 200,
          headers: {},
          timestamp: cachedResponse.timestamp,
          fromCache: true,
          cacheKey,
        };
      }

      throw error;
    }
  }

  /**
   * Get cached data
   */
  public get<T>(key: string): CacheEntry<T> | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }

    // Update access statistics
    entry.lastAccessed = Date.now();
    entry.accessCount++;

    return entry as CacheEntry<T>;
  }

  /**
   * Set cached data
   */
  public set<T>(key: string, data: T, config?: Partial<CacheConfig>): void {
    const entryConfig = { ...this.config, ...config };
    const size = this.calculateSize(data);
    
    // Compress data if enabled
    let processedData = data;
    let compressed = false;
    
    if (this.compressionEnabled && size > 1024) { // Compress if > 1KB
      try {
        processedData = this.compress(data) as T;
        compressed = true;
      } catch (error) {
        console.warn('Compression failed:', error);
      }
    }

    const entry: CacheEntry<T> = {
      key,
      data: processedData,
      timestamp: Date.now(),
      lastAccessed: Date.now(),
      accessCount: 1,
      size: this.calculateSize(processedData),
      compressed,
      metadata: {
        originalSize: size,
        compressionRatio: compressed ? size / this.calculateSize(processedData) : 1,
      },
    };

    // Evict entries if cache is full
    if (this.cache.size >= entryConfig.maxSize) {
      this.evictEntries(entryConfig.strategy);
    }

    this.cache.set(key, entry);
    this.updateStats();
  }

  /**
   * Delete cached data
   */
  public delete(key: string): boolean {
    const deleted = this.cache.delete(key);
    if (deleted) {
      this.updateStats();
    }
    return deleted;
  }

  /**
   * Clear all cached data
   */
  public clear(): void {
    this.cache.clear();
    this.updateStats();
  }

  /**
   * Invalidate cache entries based on patterns
   */
  public invalidate(pattern: string, type: 'exact' | 'prefix' | 'suffix' | 'regex' = 'exact'): number {
    let invalidatedCount = 0;
    const keysToDelete: string[] = [];

    for (const key of this.cache.keys()) {
      if (this.matchesPattern(key, pattern, type)) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach(key => {
      this.cache.delete(key);
      invalidatedCount++;
    });

    this.updateStats();
    return invalidatedCount;
  }

  /**
   * Add invalidation pattern
   */
  public addInvalidationPattern(pattern: InvalidationPattern): void {
    this.invalidationPatterns.push(pattern);
    this.invalidationPatterns.sort((a, b) => b.priority - a.priority);
  }

  /**
   * Remove invalidation pattern
   */
  public removeInvalidationPattern(pattern: string): void {
    this.invalidationPatterns = this.invalidationPatterns.filter(p => p.pattern !== pattern);
  }

  /**
   * Get cache statistics
   */
  public getStats(): CacheStats {
    return { ...this.stats };
  }

  /**
   * Get cache configuration
   */
  public getConfig(): CacheConfig {
    return { ...this.config };
  }

  /**
   * Update cache configuration
   */
  public updateConfig(config: Partial<CacheConfig>): void {
    this.config = { ...this.config, ...config };
    
    // Update compression setting
    this.compressionEnabled = this.config.enableCompression && this.isCompressionSupported();
    
    // Restart background refresh if setting changed
    if (config.enableBackgroundRefresh !== undefined) {
      if (config.enableBackgroundRefresh) {
        this.startBackgroundRefresh();
      } else {
        this.stopBackgroundRefresh();
      }
    }
  }

  /**
   * Preload data for specific keys
   */
  public async preload<T>(requests: ApiRequest[]): Promise<void> {
    const promises = requests.map(request => this.request<T>(request));
    await Promise.allSettled(promises);
  }

  /**
   * Warm up cache with frequently accessed data
   */
  public async warmup<T>(requests: ApiRequest[]): Promise<void> {
    // Sort requests by priority (if available in metadata)
    const sortedRequests = requests.sort((a, b) => {
      const aPriority = a.metadata?.priority || 0;
      const bPriority = b.metadata?.priority || 0;
      return bPriority - aPriority;
    });

    // Load data in batches to avoid overwhelming the system
    const batchSize = 5;
    for (let i = 0; i < sortedRequests.length; i += batchSize) {
      const batch = sortedRequests.slice(i, i + batchSize);
      await this.preload<T>(batch);
      
      // Small delay between batches
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  // Private methods

  /**
   * Generate cache key from request
   */
  private generateCacheKey(request: ApiRequest): string {
    if (request.cacheKey) {
      return request.cacheKey;
    }

    const keyData = {
      url: request.url,
      method: request.method,
      params: request.params,
      body: request.body,
    };

    return this.hashObject(keyData);
  }

  /**
   * Build URL with parameters
   */
  private buildUrl(url: string, params?: Record<string, any>): string {
    if (!params) return url;

    const urlObj = new URL(url, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      urlObj.searchParams.append(key, String(value));
    });

    return urlObj.toString();
  }

  /**
   * Check if cache entry is valid
   */
  private isValid(entry: CacheEntry): boolean {
    const now = Date.now();
    const age = now - entry.timestamp;
    
    return age < this.config.ttl;
  }

  /**
   * Check if entry should be background refreshed
   */
  private shouldBackgroundRefresh(entry: CacheEntry): boolean {
    const now = Date.now();
    const age = now - entry.timestamp;
    const refreshThreshold = this.config.ttl * 0.8; // Refresh when 80% of TTL has passed
    
    return age > refreshThreshold;
  }

  /**
   * Evict entries based on strategy
   */
  private evictEntries(strategy: CacheStrategy): void {
    const entries = Array.from(this.cache.entries());
    
    switch (strategy) {
      case 'lru':
        entries.sort((a, b) => a[1].lastAccessed - b[1].lastAccessed);
        break;
      case 'lfu':
        entries.sort((a, b) => a[1].accessCount - b[1].accessCount);
        break;
      case 'fifo':
        entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
        break;
      case 'ttl':
        entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
        break;
    }

    // Remove oldest/lowest priority entries
    const entriesToRemove = Math.floor(this.config.maxSize * 0.1); // Remove 10%
    for (let i = 0; i < entriesToRemove && i < entries.length; i++) {
      this.cache.delete(entries[i][0]);
    }
  }

  /**
   * Calculate data size
   */
  private calculateSize(data: any): number {
    try {
      return JSON.stringify(data).length * 2; // Rough estimate (UTF-16)
    } catch {
      return 0;
    }
  }

  /**
   * Compress data
   */
  private compress(data: any): any {
    // Simple compression using JSON stringify/parse
    // In a real implementation, you might use a compression library
    const jsonString = JSON.stringify(data);
    return jsonString; // Placeholder - implement actual compression
  }

  /**
   * Decompress data
   */
  private decompress(data: any): any {
    // Simple decompression
    return data; // Placeholder - implement actual decompression
  }

  /**
   * Check if compression is supported
   */
  private isCompressionSupported(): boolean {
    // Check if compression libraries are available
    return typeof window !== 'undefined' && 'CompressionStream' in window;
  }

  /**
   * Hash object to string
   */
  private hashObject(obj: any): string {
    const str = JSON.stringify(obj);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36);
  }

  /**
   * Match key against pattern
   */
  private matchesPattern(key: string, pattern: string, type: string): boolean {
    switch (type) {
      case 'exact':
        return key === pattern;
      case 'prefix':
        return key.startsWith(pattern);
      case 'suffix':
        return key.endsWith(pattern);
      case 'regex':
        return new RegExp(pattern).test(key);
      default:
        return false;
    }
  }

  /**
   * Update cache statistics
   */
  private updateStats(): void {
    this.stats.size = this.cache.size;
    this.stats.hitRate = this.stats.hits / (this.stats.hits + this.stats.misses) || 0;
    
    // Calculate memory usage
    let memoryUsage = 0;
    let oldestEntry = Date.now();
    let newestEntry = 0;
    
    for (const entry of this.cache.values()) {
      memoryUsage += entry.size;
      oldestEntry = Math.min(oldestEntry, entry.timestamp);
      newestEntry = Math.max(newestEntry, entry.timestamp);
    }
    
    this.stats.memoryUsage = memoryUsage;
    this.stats.oldestEntry = oldestEntry;
    this.stats.newestEntry = newestEntry;
  }

  /**
   * Start background refresh
   */
  private startBackgroundRefresh(): void {
    setInterval(() => {
      if (this.backgroundRefreshQueue.size > 0) {
        // Process background refresh queue
        const keys = Array.from(this.backgroundRefreshQueue);
        this.backgroundRefreshQueue.clear();
        
        // Refresh entries in background
        keys.forEach(key => {
          // This would trigger a background refresh
          // Implementation depends on specific requirements
        });
      }
    }, 30000); // Every 30 seconds
  }

  /**
   * Stop background refresh
   */
  private stopBackgroundRefresh(): void {
    this.backgroundRefreshQueue.clear();
  }

  /**
   * Start cleanup interval
   */
  private startCleanupInterval(): void {
    setInterval(() => {
      this.cleanup();
    }, 60000); // Every minute
  }

  /**
   * Cleanup expired entries
   */
  private cleanup(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.config.ttl) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach(key => {
      this.cache.delete(key);
    });

    if (keysToDelete.length > 0) {
      this.updateStats();
    }
  }
}

// Singleton instance
let apiCacheInstance: IntelligentApiCache | null = null;

/**
 * Get API cache singleton instance
 */
export const getApiCache = (config?: Partial<CacheConfig>): IntelligentApiCache => {
  if (!apiCacheInstance) {
    apiCacheInstance = new IntelligentApiCache(config);
  }
  return apiCacheInstance;
};

/**
 * Create new API cache instance
 */
export const createApiCache = (config?: Partial<CacheConfig>): IntelligentApiCache => {
  return new IntelligentApiCache(config);
};

/**
 * Utility function for cached API requests
 */
export const cachedRequest = async <T>(request: ApiRequest): Promise<ApiResponse<T>> => {
  const cache = getApiCache();
  return cache.request<T>(request);
};

/**
 * Utility function for batch cached requests
 */
export const cachedBatchRequest = async <T>(requests: ApiRequest[]): Promise<ApiResponse<T>[]> => {
  const cache = getApiCache();
  const promises = requests.map(request => cache.request<T>(request));
  return Promise.all(promises);
};

export default IntelligentApiCache;
