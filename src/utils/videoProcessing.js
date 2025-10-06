/**
 * Video Processing Utilities
 * Functions for video thumbnail generation, metadata extraction, and validation
 */

// Supported video formats
export const SUPPORTED_FORMATS = {
  'video/mp4': ['.mp4'],
  'video/x-msvideo': ['.avi'],
  'video/quicktime': ['.mov']
};

// Maximum file size (500MB)
export const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB in bytes

// Minimum file size (1KB)
export const MIN_FILE_SIZE = 1024; // 1KB in bytes

/**
 * Validate video file for size and format
 * @param {File} file - The file to validate
 * @returns {Object} Validation result with isValid, error, and fileInfo
 */
export const validateVideoFile = (file) => {
  const result = {
    isValid: true,
    error: null,
    fileInfo: {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified
    }
  };

  // Check if file exists
  if (!file) {
    result.isValid = false;
    result.error = 'No file provided';
    return result;
  }

  // Check file size
  if (file.size < MIN_FILE_SIZE) {
    result.isValid = false;
    result.error = 'File is too small. Minimum size is 1KB.';
    return result;
  }

  if (file.size > MAX_FILE_SIZE) {
    result.isValid = false;
    result.error = `File is too large. Maximum size is ${formatFileSize(MAX_FILE_SIZE)}.`;
    return result;
  }

  // Check file type
  const isValidFormat = Object.keys(SUPPORTED_FORMATS).includes(file.type) ||
    SUPPORTED_FORMATS['video/mp4'].some(ext => file.name.toLowerCase().endsWith(ext)) ||
    SUPPORTED_FORMATS['video/x-msvideo'].some(ext => file.name.toLowerCase().endsWith(ext)) ||
    SUPPORTED_FORMATS['video/quicktime'].some(ext => file.name.toLowerCase().endsWith(ext));

  if (!isValidFormat) {
    result.isValid = false;
    result.error = 'Unsupported file format. Please upload MP4, AVI, or MOV files.';
    return result;
  }

  return result;
};

/**
 * Generate video thumbnail from file at specified timestamp
 * @param {File} file - The video file
 * @param {number} timestamp - Timestamp in seconds (default: 1)
 * @returns {Promise<string>} Base64 data URL of the thumbnail
 */
export const generateVideoThumbnail = async (file, timestamp = 1) => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    video.addEventListener('loadedmetadata', () => {
      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Seek to the specified timestamp
      video.currentTime = Math.min(timestamp, video.duration - 0.1);
    });

    video.addEventListener('seeked', () => {
      try {
        // Draw the video frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        // Convert canvas to base64 data URL
        const thumbnail = canvas.toDataURL('image/jpeg', 0.8);
        resolve(thumbnail);
      } catch (error) {
        reject(new Error('Failed to generate thumbnail: ' + error.message));
      }
    });

    video.addEventListener('error', (e) => {
      reject(new Error('Video loading error: ' + e.message));
    });

    // Set video source
    video.src = URL.createObjectURL(file);
    video.load();
  });
};

/**
 * Extract video metadata including duration, dimensions, and format
 * @param {File} file - The video file
 * @returns {Promise<Object>} Video metadata object
 */
export const extractVideoMetadata = async (file) => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const metadata = {
      duration: 0,
      width: 0,
      height: 0,
      format: file.type || 'unknown',
      size: file.size,
      name: file.name
    };

    video.addEventListener('loadedmetadata', () => {
      metadata.duration = video.duration;
      metadata.width = video.videoWidth;
      metadata.height = video.videoHeight;
      
      // Clean up object URL
      URL.revokeObjectURL(video.src);
      resolve(metadata);
    });

    video.addEventListener('error', (e) => {
      URL.revokeObjectURL(video.src);
      reject(new Error('Failed to extract metadata: ' + e.message));
    });

    // Set video source
    video.src = URL.createObjectURL(file);
    video.load();
  });
};

/**
 * Format file size in human readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size string
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Format duration in human readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string (HH:MM:SS)
 */
export const formatDuration = (seconds) => {
  if (!seconds || isNaN(seconds)) return '00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  } else {
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
};

/**
 * Calculate upload progress percentage
 * @param {number} loaded - Bytes loaded
 * @param {number} total - Total bytes
 * @returns {number} Progress percentage (0-100)
 */
export const calculateProgress = (loaded, total) => {
  if (total === 0) return 0;
  return Math.min(100, Math.round((loaded / total) * 100));
};

/**
 * Estimate remaining upload time
 * @param {number} loaded - Bytes loaded
 * @param {number} total - Total bytes
 * @param {number} startTime - Upload start time in milliseconds
 * @returns {number} Estimated remaining time in seconds
 */
export const estimateRemainingTime = (loaded, total, startTime) => {
  if (loaded === 0 || total === 0) return 0;
  
  const elapsed = Date.now() - startTime;
  const rate = loaded / elapsed; // bytes per millisecond
  const remaining = total - loaded;
  
  return Math.round(remaining / rate / 1000); // convert to seconds
};

/**
 * Format time remaining in human readable format
 * @param {number} seconds - Time in seconds
 * @returns {string} Formatted time string
 */
export const formatTimeRemaining = (seconds) => {
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
};

/**
 * Get file extension from filename
 * @param {string} filename - The filename
 * @returns {string} File extension (including dot)
 */
export const getFileExtension = (filename) => {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2);
};

/**
 * Check if file is a supported video format
 * @param {File} file - The file to check
 * @returns {boolean} True if file is a supported video format
 */
export const isSupportedVideoFormat = (file) => {
  if (!file) return false;
  
  // Check MIME type
  if (Object.keys(SUPPORTED_FORMATS).includes(file.type)) {
    return true;
  }
  
  // Check file extension as fallback
  const extension = getFileExtension(file.name).toLowerCase();
  return Object.values(SUPPORTED_FORMATS).flat().includes(`.${extension}`);
};

/**
 * Create a file hash for duplicate detection
 * @param {File} file - The file to hash
 * @returns {Promise<string>} SHA-256 hash of the file
 */
export const createFileHash = async (file) => {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
};

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle function to limit function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
export const throttle = (func, limit) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

/**
 * Format upload speed in human-readable format
 * @param {number} bytesPerSecond - Upload speed in bytes per second
 * @returns {string} Formatted speed string
 */
export const formatUploadSpeed = (bytesPerSecond) => {
  if (bytesPerSecond === 0) return '0 B/s';
  
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
  let size = bytesPerSecond;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

/**
 * Extract file metadata from File object
 * @param {File} file - File object
 * @returns {Object} File metadata
 */
export const extractFileMetadata = async (file) => {
  return {
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified,
    sizeFormatted: formatFileSize(file.size),
    extension: file.name.split('.').pop()?.toLowerCase() || '',
    mimeType: file.type
  };
};