/**
 * Basic Tests for Custom React Hooks
 * Tests the integration and basic functionality of the custom hooks
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock dependencies
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: null,
    refetch: vi.fn(),
    isRefetching: false,
    lastFetchTime: null
  })),
  useMutation: vi.fn(() => ({
    mutateAsync: vi.fn(),
    onSuccess: vi.fn(),
    onError: vi.fn()
  })),
  useQueryClient: vi.fn(() => ({
    removeQueries: vi.fn()
  }))
}));

vi.mock('../services/s3UploadService', () => ({
  S3UploadService: vi.fn(() => ({
    upload: vi.fn(),
    generateUniqueKey: vi.fn(),
    formatTimeRemaining: vi.fn()
  }))
}));

// Import hooks after mocking
import { useDetectionAnalysis } from '../useDetectionAnalysis';
import { useVideoUpload } from '../useVideoUpload';
import { useWebSocketEvents } from '../useWebSocketEvents';

describe('Custom React Hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useDetectionAnalysis', () => {
    it('should initialize with correct default state', () => {
      const { result } = renderHook(() => useDetectionAnalysis());
      
      expect(result.current.state).toBe('idle');
      expect(result.current.progress).toBeNull();
      expect(result.current.result).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.isRetrying).toBe(false);
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useDetectionAnalysis());
      
      expect(typeof result.current.startAnalysis).toBe('function');
      expect(typeof result.current.retryAnalysis).toBe('function');
      expect(typeof result.current.clearError).toBe('function');
      expect(typeof result.current.resetAnalysis).toBe('function');
      expect(typeof result.current.refetch).toBe('function');
    });
  });

  describe('useVideoUpload', () => {
    it('should initialize with correct default state', () => {
      const { result } = renderHook(() => useVideoUpload());
      
      expect(result.current.state).toBe('idle');
      expect(result.current.progress).toBeNull();
      expect(result.current.result).toBeNull();
      expect(result.current.error).toBeNull();
      expect(result.current.validation).toBeNull();
      expect(result.current.preview).toBeNull();
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useVideoUpload());
      
      expect(typeof result.current.selectFile).toBe('function');
      expect(typeof result.current.uploadFile).toBe('function');
      expect(typeof result.current.cancelUpload).toBe('function');
      expect(typeof result.current.clearError).toBe('function');
      expect(typeof result.current.resetUpload).toBe('function');
      expect(typeof result.current.generatePreview).toBe('function');
      expect(typeof result.current.validateFile).toBe('function');
      expect(typeof result.current.formatFileSize).toBe('function');
      expect(typeof result.current.formatUploadSpeed).toBe('function');
    });
  });

  describe('useWebSocketEvents', () => {
    it('should initialize with correct default state', () => {
      const { result } = renderHook(() => useWebSocketEvents());
      
      expect(result.current.state).toBe('disconnected');
      expect(result.current.isConnected).toBe(false);
      expect(result.current.isReconnecting).toBe(false);
      expect(result.current.lastError).toBeNull();
      expect(result.current.reconnectionInfo).toBeNull();
      expect(result.current.lastHeartbeat).toBeNull();
    });

    it('should provide all required methods', () => {
      const { result } = renderHook(() => useWebSocketEvents());
      
      expect(typeof result.current.connect).toBe('function');
      expect(typeof result.current.disconnect).toBe('function');
      expect(typeof result.current.reconnect).toBe('function');
      expect(typeof result.current.sendMessage).toBe('function');
      expect(typeof result.current.clearError).toBe('function');
      expect(typeof result.current.onStatusUpdate).toBe('function');
      expect(typeof result.current.onResultUpdate).toBe('function');
      expect(typeof result.current.onHeartbeat).toBe('function');
      expect(typeof result.current.onError).toBe('function');
      expect(typeof result.current.onConnect).toBe('function');
      expect(typeof result.current.onDisconnect).toBe('function');
      expect(typeof result.current.removeEventListener).toBe('function');
      expect(typeof result.current.removeAllEventListeners).toBe('function');
    });
  });

  describe('Hook Integration', () => {
    it('should work together without conflicts', () => {
      const { result: analysisResult } = renderHook(() => useDetectionAnalysis());
      const { result: uploadResult } = renderHook(() => useVideoUpload());
      const { result: wsResult } = renderHook(() => useWebSocketEvents());

      // All hooks should initialize properly
      expect(analysisResult.current.state).toBe('idle');
      expect(uploadResult.current.state).toBe('idle');
      expect(wsResult.current.state).toBe('disconnected');

      // Methods should be available
      expect(typeof analysisResult.current.startAnalysis).toBe('function');
      expect(typeof uploadResult.current.selectFile).toBe('function');
      expect(typeof wsResult.current.connect).toBe('function');
    });
  });
});

describe('Error Handling Integration', () => {
  it('should handle errors consistently across hooks', () => {
    const { result } = renderHook(() => useDetectionAnalysis());
    
    act(() => {
      result.current.clearError();
    });
    
    expect(result.current.error).toBeNull();
  });
});

describe('Utility Functions', () => {
  it('should format file sizes correctly', () => {
    const { result } = renderHook(() => useVideoUpload());
    
    // Test file size formatting
    const formattedSize = result.current.formatFileSize(1024);
    expect(formattedSize).toBe('1 KB');
    
    const formattedSizeMB = result.current.formatFileSize(1024 * 1024);
    expect(formattedSizeMB).toBe('1 MB');
  });

  it('should format upload speeds correctly', () => {
    const { result } = renderHook(() => useVideoUpload());
    
    // Test upload speed formatting
    const formattedSpeed = result.current.formatUploadSpeed(1024);
    expect(formattedSpeed).toBe('1 KB/s');
    
    const formattedSpeedMB = result.current.formatUploadSpeed(1024 * 1024);
    expect(formattedSpeedMB).toBe('1 MB/s');
  });
});
