/**
 * S3 Upload Service
 * Handles secure file uploads to AWS S3 with progress tracking and authentication
 */

import { S3Client, PutObjectCommand, HeadObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

/**
 * S3 Upload Service Class
 */
export class S3UploadService {
  constructor(config = {}) {
    this.config = {
      region: config.region || 'us-east-1',
      bucket: config.bucket || 'secureai-deepfake-videos',
      usePresignedUrls: config.usePresignedUrls !== false, // Default to true
      chunkSize: config.chunkSize || 5 * 1024 * 1024, // 5MB chunks
      maxRetries: config.maxRetries || 3,
      ...config
    };

    this.s3Client = null;
    this.initializeClient();
  }

  /**
   * Initialize S3 client with credentials
   */
  initializeClient() {
    try {
      this.s3Client = new S3Client({
        region: this.config.region,
        credentials: this.getCredentials(),
        maxAttempts: this.config.maxRetries
      });
    } catch (error) {
      console.error('Failed to initialize S3 client:', error);
      throw new Error('S3 client initialization failed');
    }
  }

  /**
   * Get AWS credentials from various sources
   * @returns {Object} AWS credentials
   */
  getCredentials() {
    // Try to get credentials from environment, IAM role, or Cognito
    if (this.config.accessKeyId && this.config.secretAccessKey) {
      return {
        accessKeyId: this.config.accessKeyId,
        secretAccessKey: this.config.secretAccessKey
      };
    }

    // For production, credentials should come from IAM roles or Cognito
    // This is handled automatically by the AWS SDK
    return undefined;
  }

  /**
   * Generate presigned URL for direct upload
   * @param {string} key - S3 object key
   * @param {string} contentType - File content type
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<string>} Presigned URL
   */
  async generatePresignedUrl(key, contentType, metadata = {}) {
    try {
      const command = new PutObjectCommand({
        Bucket: this.config.bucket,
        Key: key,
        ContentType: contentType,
        Metadata: metadata,
        ServerSideEncryption: 'AES256'
      });

      const presignedUrl = await getSignedUrl(this.s3Client, command, {
        expiresIn: 3600 // 1 hour
      });

      return presignedUrl;
    } catch (error) {
      console.error('Failed to generate presigned URL:', error);
      throw new Error('Failed to generate presigned URL');
    }
  }

  /**
   * Upload file using presigned URL
   * @param {File} file - File to upload
   * @param {string} presignedUrl - Presigned URL for upload
   * @param {Function} onProgress - Progress callback function
   * @returns {Promise<Object>} Upload result
   */
  async uploadWithPresignedUrl(file, presignedUrl, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const startTime = Date.now();

      // Track upload progress
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = {
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100),
            speed: this.calculateSpeed(event.loaded, startTime),
            estimatedTime: this.estimateRemainingTime(event.loaded, event.total, startTime)
          };
          onProgress(progress);
        }
      });

      // Handle upload completion
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve({
            success: true,
            status: xhr.status,
            uploadTime: Date.now() - startTime
          });
        } else {
          reject(new Error(`Upload failed with status: ${xhr.status}`));
        }
      });

      // Handle upload errors
      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed due to network error'));
      });

      // Handle upload abort
      xhr.addEventListener('abort', () => {
        reject(new Error('Upload was aborted'));
      });

      // Start upload
      xhr.open('PUT', presignedUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  }

  /**
   * Upload file directly to S3 using SDK
   * @param {File} file - File to upload
   * @param {string} key - S3 object key
   * @param {Function} onProgress - Progress callback function
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<Object>} Upload result
   */
  async uploadDirect(file, key, onProgress, metadata = {}) {
    try {
      const command = new PutObjectCommand({
        Bucket: this.config.bucket,
        Key: key,
        Body: file,
        ContentType: file.type,
        Metadata: metadata,
        ServerSideEncryption: 'AES256'
      });

      // For direct upload, we can't track progress with the SDK
      // We'll use a simple progress simulation
      if (onProgress) {
        this.simulateProgress(file.size, onProgress);
      }

      const result = await this.s3Client.send(command);
      
      return {
        success: true,
        etag: result.ETag,
        location: `https://${this.config.bucket}.s3.${this.config.region}.amazonaws.com/${key}`
      };
    } catch (error) {
      console.error('Direct upload failed:', error);
      throw new Error('Direct upload failed');
    }
  }

  /**
   * Upload file with chunked upload for large files
   * @param {File} file - File to upload
   * @param {string} key - S3 object key
   * @param {Function} onProgress - Progress callback function
   * @param {Object} metadata - Additional metadata
   * @returns {Promise<Object>} Upload result
   */
  async uploadChunked(file, key, onProgress, metadata = {}) {
    // For now, we'll use the presigned URL approach
    // In a production environment, you might want to implement multipart upload
    const presignedUrl = await this.generatePresignedUrl(key, file.type, metadata);
    return this.uploadWithPresignedUrl(file, presignedUrl, onProgress);
  }

  /**
   * Main upload method that chooses the best upload strategy
   * @param {File} file - File to upload
   * @param {string} key - S3 object key
   * @param {Function} onProgress - Progress callback function
   * @param {Object} options - Upload options
   * @returns {Promise<Object>} Upload result
   */
  async upload(file, key, onProgress, options = {}) {
    try {
      // Validate inputs
      if (!file || !key) {
        throw new Error('File and key are required');
      }

      const metadata = {
        originalName: file.name,
        uploadDate: new Date().toISOString(),
        fileSize: file.size.toString(),
        ...options.metadata
      };

      // Choose upload strategy based on file size and configuration
      if (this.config.usePresignedUrls && file.size > this.config.chunkSize) {
        return this.uploadChunked(file, key, onProgress, metadata);
      } else if (this.config.usePresignedUrls) {
        const presignedUrl = await this.generatePresignedUrl(key, file.type, metadata);
        return this.uploadWithPresignedUrl(file, presignedUrl, onProgress);
      } else {
        return this.uploadDirect(file, key, onProgress, metadata);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  }

  /**
   * Check if file exists in S3
   * @param {string} key - S3 object key
   * @returns {Promise<boolean>} True if file exists
   */
  async fileExists(key) {
    try {
      const command = new HeadObjectCommand({
        Bucket: this.config.bucket,
        Key: key
      });
      
      await this.s3Client.send(command);
      return true;
    } catch (error) {
      if (error.name === 'NotFound') {
        return false;
      }
      throw error;
    }
  }

  /**
   * Get file metadata from S3
   * @param {string} key - S3 object key
   * @returns {Promise<Object>} File metadata
   */
  async getFileMetadata(key) {
    try {
      const command = new HeadObjectCommand({
        Bucket: this.config.bucket,
        Key: key
      });
      
      const result = await this.s3Client.send(command);
      return {
        size: result.ContentLength,
        lastModified: result.LastModified,
        etag: result.ETag,
        contentType: result.ContentType,
        metadata: result.Metadata
      };
    } catch (error) {
      console.error('Failed to get file metadata:', error);
      throw error;
    }
  }

  /**
   * Generate unique S3 key for file
   * @param {File} file - File to generate key for
   * @param {string} prefix - Key prefix (default: 'uploads/')
   * @returns {string} Unique S3 key
   */
  generateUniqueKey(file, prefix = 'uploads/') {
    const timestamp = Date.now();
    const randomId = Math.random().toString(36).substring(2, 15);
    const extension = file.name.split('.').pop();
    return `${prefix}${timestamp}-${randomId}.${extension}`;
  }

  /**
   * Calculate upload speed
   * @param {number} loaded - Bytes loaded
   * @param {number} startTime - Upload start time
   * @returns {number} Speed in bytes per second
   */
  calculateSpeed(loaded, startTime) {
    const elapsed = Date.now() - startTime;
    return elapsed > 0 ? loaded / (elapsed / 1000) : 0;
  }

  /**
   * Estimate remaining upload time
   * @param {number} loaded - Bytes loaded
   * @param {number} total - Total bytes
   * @param {number} startTime - Upload start time
   * @returns {number} Estimated remaining time in seconds
   */
  estimateRemainingTime(loaded, total, startTime) {
    if (loaded === 0 || total === 0) return 0;
    
    const elapsed = Date.now() - startTime;
    const rate = loaded / elapsed; // bytes per millisecond
    const remaining = total - loaded;
    
    return Math.round(remaining / rate / 1000); // convert to seconds
  }

  /**
   * Simulate progress for direct uploads
   * @param {number} fileSize - File size in bytes
   * @param {Function} onProgress - Progress callback
   */
  simulateProgress(fileSize, onProgress) {
    let loaded = 0;
    const interval = setInterval(() => {
      loaded += fileSize * 0.1; // Simulate 10% increments
      if (loaded >= fileSize) {
        loaded = fileSize;
        clearInterval(interval);
      }
      
      onProgress({
        loaded,
        total: fileSize,
        percentage: Math.round((loaded / fileSize) * 100),
        speed: fileSize * 0.1 / 100, // Simulated speed
        estimatedTime: Math.round((fileSize - loaded) / (fileSize * 0.1 / 100))
      });
    }, 100);
  }

  /**
   * Format upload speed for display
   * @param {number} bytesPerSecond - Speed in bytes per second
   * @returns {string} Formatted speed string
   */
  formatSpeed(bytesPerSecond) {
    if (bytesPerSecond === 0) return '0 B/s';
    
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k));
    
    return parseFloat((bytesPerSecond / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Format time remaining for display
   * @param {number} seconds - Time in seconds
   * @returns {string} Formatted time string
   */
  formatTimeRemaining(seconds) {
    if (seconds === 0 || isNaN(seconds)) return 'Calculating...';
    
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${minutes}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  }
}

/**
 * Default S3 upload service instance
 */
export const s3UploadService = new S3UploadService();

/**
 * Upload file to S3 with progress tracking
 * @param {File} file - File to upload
 * @param {Function} onProgress - Progress callback function
 * @param {Object} options - Upload options
 * @returns {Promise<Object>} Upload result
 */
export const uploadToS3 = async (file, onProgress, options = {}) => {
  const key = options.key || s3UploadService.generateUniqueKey(file, options.prefix);
  
  try {
    const result = await s3UploadService.upload(file, key, onProgress, options);
    return {
      success: true,
      key,
      url: `https://${s3UploadService.config.bucket}.s3.${s3UploadService.config.region}.amazonaws.com/${key}`,
      ...result
    };
  } catch (error) {
    console.error('S3 upload failed:', error);
    return {
      success: false,
      error: error.message
    };
  }
};

/**
 * Upload file using existing Flask API endpoint
 * @param {File} file - File to upload
 * @param {Function} onProgress - Progress callback function
 * @param {Object} options - Upload options
 * @returns {Promise<Object>} Upload result
 */
export const uploadViaAPI = async (file, onProgress, options = {}) => {
  const formData = new FormData();
  formData.append('video', file);
  
  if (options.userId) {
    formData.append('user_id', options.userId);
  }
  
  if (options.metadata) {
    formData.append('metadata', JSON.stringify(options.metadata));
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const startTime = Date.now();

    // Track upload progress
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = {
          loaded: event.loaded,
          total: event.total,
          percentage: Math.round((event.loaded / event.total) * 100),
          speed: s3UploadService.calculateSpeed(event.loaded, startTime),
          estimatedTime: s3UploadService.estimateRemainingTime(event.loaded, event.total, startTime)
        };
        onProgress(progress);
      }
    });

    // Handle upload completion
    xhr.addEventListener('load', () => {
      try {
        const response = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve({
            success: true,
            ...response,
            uploadTime: Date.now() - startTime
          });
        } else {
          reject(new Error(response.error || `Upload failed with status: ${xhr.status}`));
        }
      } catch (error) {
        reject(new Error('Failed to parse response'));
      }
    });

    // Handle upload errors
    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed due to network error'));
    });

    // Handle upload abort
    xhr.addEventListener('abort', () => {
      reject(new Error('Upload was aborted'));
    });

    // Start upload
    xhr.open('POST', '/api/upload');
    xhr.send(formData);
  });
};
