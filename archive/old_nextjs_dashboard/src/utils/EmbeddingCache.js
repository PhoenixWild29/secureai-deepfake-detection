/**
 * EmbeddingCache Utility
 * Client-side utility for checking duplicate video hashes and caching results
 */

import { createHash } from 'crypto';

/**
 * EmbeddingCache class for managing video hash caching and duplicate detection
 */
class EmbeddingCache {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || '/api/v1/embedding-cache';
    this.cacheTimeout = options.cacheTimeout || 24 * 60 * 60 * 1000; // 24 hours
    this.localCache = new Map();
    this.requestCache = new Map(); // Prevent duplicate requests
  }

  /**
   * Generate hash for a file
   * @param {File} file - File object
   * @returns {Promise<string>} - File hash
   */
  async generateFileHash(file) {
    try {
      // Use Web Crypto API for better performance
      const buffer = await file.arrayBuffer();
      const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      return hashHex;
    } catch (error) {
      console.warn('Web Crypto API not available, falling back to alternative method:', error);
      return this.generateFileHashFallback(file);
    }
  }

  /**
   * Fallback method for generating file hash
   * @param {File} file - File object
   * @returns {Promise<string>} - File hash
   */
  async generateFileHashFallback(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = () => {
        try {
          // Simple hash implementation for browsers without Web Crypto API
          const buffer = reader.result;
          let hash = 0;
          
          for (let i = 0; i < buffer.byteLength; i++) {
            const byte = buffer[i];
            hash = ((hash << 5) - hash + byte) & 0xffffffff;
          }
          
          // Convert to hex string
          const hashHex = Math.abs(hash).toString(16);
          resolve(hashHex);
        } catch (error) {
          reject(error);
        }
      };
      
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(file);
    });
  }

  /**
   * Check if a hash exists in the cache (local check first)
   * @param {string} hash - File hash
   * @returns {Promise<Object>} - Duplicate check result
   */
  async checkDuplicate(hash) {
    try {
      // Check local cache first
      const localResult = this.checkLocalCache(hash);
      if (localResult.found) {
        return localResult;
      }

      // Check if request is already in progress
      if (this.requestCache.has(hash)) {
        return await this.requestCache.get(hash);
      }

      // Make API request
      const requestPromise = this.checkRemoteCache(hash);
      this.requestCache.set(hash, requestPromise);

      try {
        const result = await requestPromise;
        
        // Cache the result locally
        if (result.found) {
          this.setLocalCache(hash, result);
        }
        
        return result;
      } finally {
        // Clean up request cache
        this.requestCache.delete(hash);
      }

    } catch (error) {
      console.error('Duplicate check failed:', error);
      return {
        found: false,
        error: error.message,
        hash: hash
      };
    }
  }

  /**
   * Check local cache for hash
   * @param {string} hash - File hash
   * @returns {Object} - Local cache result
   */
  checkLocalCache(hash) {
    const cached = this.localCache.get(hash);
    
    if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
      return {
        found: true,
        result: cached.result,
        analysisId: cached.analysisId,
        timestamp: cached.timestamp,
        source: 'local'
      };
    }
    
    // Remove expired entry
    if (cached) {
      this.localCache.delete(hash);
    }
    
    return { found: false };
  }

  /**
   * Set local cache entry
   * @param {string} hash - File hash
   * @param {Object} result - Cache result
   */
  setLocalCache(hash, result) {
    this.localCache.set(hash, {
      result: result.result,
      analysisId: result.analysisId,
      timestamp: Date.now()
    });
  }

  /**
   * Check remote cache via API
   * @param {string} hash - File hash
   * @returns {Promise<Object>} - Remote cache result
   */
  async checkRemoteCache(hash) {
    try {
      const response = await fetch(`${this.baseUrl}/check/${hash}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      return {
        found: data.found || false,
        result: data.result || null,
        analysisId: data.analysisId || null,
        timestamp: Date.now(),
        source: 'remote'
      };

    } catch (error) {
      console.error('Remote cache check failed:', error);
      throw error;
    }
  }

  /**
   * Add a result to the cache
   * @param {string} hash - File hash
   * @param {Object} result - Analysis result
   * @param {string} analysisId - Analysis ID
   * @returns {Promise<boolean>} - Success status
   */
  async addToCache(hash, result, analysisId) {
    try {
      // Add to local cache immediately
      this.setLocalCache(hash, { result, analysisId });

      // Add to remote cache
      const response = await fetch(`${this.baseUrl}/add`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          hash,
          result,
          analysisId,
          timestamp: Date.now()
        })
      });

      if (!response.ok) {
        console.warn('Failed to add to remote cache:', response.statusText);
        return false;
      }

      return true;

    } catch (error) {
      console.error('Failed to add to cache:', error);
      return false;
    }
  }

  /**
   * Clear local cache
   */
  clearLocalCache() {
    this.localCache.clear();
    this.requestCache.clear();
  }

  /**
   * Get cache statistics
   * @returns {Object} - Cache statistics
   */
  getCacheStats() {
    const now = Date.now();
    let validEntries = 0;
    let expiredEntries = 0;

    for (const [hash, entry] of this.localCache.entries()) {
      if ((now - entry.timestamp) < this.cacheTimeout) {
        validEntries++;
      } else {
        expiredEntries++;
      }
    }

    return {
      totalEntries: this.localCache.size,
      validEntries,
      expiredEntries,
      pendingRequests: this.requestCache.size
    };
  }

  /**
   * Clean up expired entries
   */
  cleanupExpiredEntries() {
    const now = Date.now();
    const expiredHashes = [];

    for (const [hash, entry] of this.localCache.entries()) {
      if ((now - entry.timestamp) >= this.cacheTimeout) {
        expiredHashes.push(hash);
      }
    }

    expiredHashes.forEach(hash => this.localCache.delete(hash));
    
    return expiredHashes.length;
  }

  /**
   * Batch check multiple hashes
   * @param {string[]} hashes - Array of file hashes
   * @returns {Promise<Object[]>} - Array of duplicate check results
   */
  async batchCheckDuplicates(hashes) {
    try {
      const response = await fetch(`${this.baseUrl}/batch-check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ hashes })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Update local cache with results
      data.results.forEach(result => {
        if (result.found) {
          this.setLocalCache(result.hash, result);
        }
      });

      return data.results;

    } catch (error) {
      console.error('Batch duplicate check failed:', error);
      // Fallback to individual checks
      return Promise.all(hashes.map(hash => this.checkDuplicate(hash)));
    }
  }

  /**
   * Get cached result by analysis ID
   * @param {string} analysisId - Analysis ID
   * @returns {Promise<Object|null>} - Cached result or null
   */
  async getResultByAnalysisId(analysisId) {
    try {
      const response = await fetch(`${this.baseUrl}/result/${analysisId}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data.result;

    } catch (error) {
      console.error('Failed to get result by analysis ID:', error);
      return null;
    }
  }

  /**
   * Configure cache settings
   * @param {Object} options - Configuration options
   */
  configure(options) {
    if (options.baseUrl !== undefined) {
      this.baseUrl = options.baseUrl;
    }
    if (options.cacheTimeout !== undefined) {
      this.cacheTimeout = options.cacheTimeout;
    }
  }
}

// Export singleton instance
export { EmbeddingCache };

// Default export for convenience
export default EmbeddingCache;
