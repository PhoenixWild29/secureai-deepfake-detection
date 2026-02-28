/**
 * useResultVisualization Hook Test Suite
 * Work Order #48 - Extended State Management for Result Visualization
 * 
 * Comprehensive test suite for the useResultVisualization hook covering
 * all functionality including state management, WebSocket integration,
 * performance optimization, and error handling.
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useResultVisualization } from './useResultVisualization';
import { useDetectionAnalysis } from './useDetectionAnalysis';
import { useWebSocket } from './useWebSocket';
import { useAuth } from './useAuth';
import { exportService } from '../services/exportService';

// Mock dependencies
jest.mock('./useDetectionAnalysis');
jest.mock('./useWebSocket');
jest.mock('./useAuth');
jest.mock('../services/exportService');

// ============================================================================
// Test Configuration
// ============================================================================

const MOCK_ANALYSIS_ID = 'test-analysis-12345';
const MOCK_USER_ID = 'test-user-67890';

const MOCK_DETECTION_ANALYSIS = {
  analysisState: 'completed',
  analysisProgress: 100,
  confidenceScore: 0.85,
  isFake: false,
  blockchainVerification: {
    verified: true,
    transactionHash: '0x1234567890abcdef',
    verifiedAt: new Date().toISOString()
  },
  frameAnalysis: [
    {
      frameNumber: 0,
      confidence: 0.82,
      suspiciousRegions: []
    },
    {
      frameNumber: 1,
      confidence: 0.87,
      suspiciousRegions: [{ x: 100, y: 100, width: 50, height: 50 }]
    }
  ]
};

const MOCK_USER = {
  id: MOCK_USER_ID,
  name: 'Test User',
  email: 'test@example.com',
  permissions: {
    allowedFormats: ['pdf', 'json', 'csv'],
    maxBatchSize: 10,
    dataAccessLevel: 'standard'
  }
};

const MOCK_WEBSOCKET = {
  isConnected: true,
  subscribe: jest.fn(),
  unsubscribe: jest.fn()
};

const MOCK_AUTH = {
  user: MOCK_USER,
  hasPermission: jest.fn(() => true),
  isAuthenticated: true
};

// ============================================================================
// Test Setup
// ============================================================================

describe('useResultVisualization Hook', () => {
  
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mock implementations
    useDetectionAnalysis.mockReturnValue(MOCK_DETECTION_ANALYSIS);
    useWebSocket.mockReturnValue(MOCK_WEBSOCKET);
    useAuth.mockReturnValue(MOCK_AUTH);
    exportService.initiateExport = jest.fn();
    exportService.cancelExport = jest.fn();
    exportService.retryExport = jest.fn();
  });
  
  afterEach(() => {
    jest.restoreAllMocks();
  });
  
  // ============================================================================
  // Basic Hook Functionality Tests
  // ============================================================================
  
  describe('Basic Hook Functionality', () => {
    
    test('should initialize with default state', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      expect(result.current.visualizationState.currentMode).toBe('summary');
      expect(result.current.visualizationState.isInitialized).toBe(false);
      expect(result.current.isLoading).toBe(true);
      expect(result.current.error).toBe(null);
    });
    
    test('should initialize with custom options', () => {
      const customOptions = {
        enableConfidenceCaching: false,
        enableHeatmapProcessing: false,
        cacheSize: 500,
        debounceDelay: 500
      };
      
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, customOptions));
      
      expect(result.current.visualizationState).toBeDefined();
      expect(result.current.actions).toBeDefined();
      expect(result.current.detectionAnalysis).toBe(MOCK_DETECTION_ANALYSIS);
    });
    
    test('should return all required properties', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      expect(result.current).toHaveProperty('visualizationState');
      expect(result.current).toHaveProperty('actions');
      expect(result.current).toHaveProperty('detectionAnalysis');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('performanceMetrics');
      expect(result.current).toHaveProperty('canExport');
      expect(result.current).toHaveProperty('hasUnseenModifications');
      expect(result.current).toHaveProperty('refresh');
      expect(result.current).toHaveProperty('cleanup');
    });
    
    test('should provide all required actions', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      const { actions } = result.current;
      
      expect(actions).toHaveProperty('setVisualizationMode');
      expect(actions).toHaveProperty('updateConfidenceCache');
      expect(actions).toHaveProperty('processHeatmapData');
      expect(actions).toHaveProperty('initiateExport');
      expect(actions).toHaveProperty('cancelExport');
      expect(actions).toHaveProperty('retryExport');
      expect(actions).toHaveProperty('clearExportHistory');
      expect(actions).toHaveProperty('refreshBlockchainStatus');
      expect(actions).toHaveProperty('markModificationsSeen');
      expect(actions).toHaveProperty('clearModificationHistory');
      expect(actions).toHaveProperty('resetVisualizationState');
      expect(actions).toHaveProperty('optimizePerformance');
    });
  });
  
  // ============================================================================
  // Visualization Mode Management Tests
  // ============================================================================
  
  describe('Visualization Mode Management', () => {
    
    test('should change visualization mode', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      act(() => {
        result.current.actions.setVisualizationMode('detailed');
      });
      
      expect(result.current.visualizationState.currentMode).toBe('detailed');
    });
    
    test('should handle invalid visualization mode', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      act(() => {
        result.current.actions.setVisualizationMode('invalid_mode');
      });
      
      // Should not change mode and should log error
      expect(result.current.visualizationState.currentMode).toBe('summary');
      expect(result.current.error).toBeDefined();
    });
    
    test('should support all valid visualization modes', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      const validModes = ['summary', 'detailed', 'export_preview'];
      
      validModes.forEach(mode => {
        act(() => {
          result.current.actions.setVisualizationMode(mode);
        });
        
        expect(result.current.visualizationState.currentMode).toBe(mode);
      });
    });
  });
  
  // ============================================================================
  // Confidence Score Caching Tests
  // ============================================================================
  
  describe('Confidence Score Caching', () => {
    
    test('should update confidence cache', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      const frameNumber = 5;
      const confidenceData = {
        confidenceScore: 0.92,
        isProcessed: true,
        suspiciousRegions: []
      };
      
      act(() => {
        result.current.actions.updateConfidenceCache(frameNumber, confidenceData);
      });
      
      expect(result.current.visualizationState.confidenceCache.size).toBe(1);
      expect(result.current.visualizationState.confidenceCache.has(frameNumber)).toBe(true);
    });
    
    test('should respect cache size limit', () => {
      const options = { cacheSize: 2 };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      // Add more items than cache size
      act(() => {
        result.current.actions.updateConfidenceCache(1, { confidenceScore: 0.8 });
        result.current.actions.updateConfidenceCache(2, { confidenceScore: 0.9 });
        result.current.actions.updateConfidenceCache(3, { confidenceScore: 0.95 });
      });
      
      expect(result.current.visualizationState.confidenceCache.size).toBe(2);
      expect(result.current.visualizationState.confidenceCache.has(1)).toBe(false); // Should be evicted
      expect(result.current.visualizationState.confidenceCache.has(3)).toBe(true); // Should be present
    });
    
    test('should disable caching when option is false', () => {
      const options = { enableConfidenceCaching: false };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      act(() => {
        result.current.actions.updateConfidenceCache(1, { confidenceScore: 0.8 });
      });
      
      expect(result.current.visualizationState.confidenceCache.size).toBe(0);
    });
  });
  
  // ============================================================================
  // Heatmap Data Processing Tests
  // ============================================================================
  
  describe('Heatmap Data Processing', () => {
    
    test('should process heatmap data successfully', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      const heatmapData = {
        dataPoints: [
          { x: 0.1, y: 0.1, intensity: 0.8, confidence: 0.8, frameNumber: 0, regionType: 'detection' },
          { x: 0.2, y: 0.2, intensity: 0.9, confidence: 0.9, frameNumber: 1, regionType: 'detection' }
        ],
        frameCount: 2,
        maxIntensity: 0.9,
        minIntensity: 0.8,
        metadata: {},
        processingTime: 0
      };
      
      await act(async () => {
        await result.current.actions.processHeatmapData(heatmapData);
      });
      
      expect(result.current.visualizationState.heatmapState.status).toBe('completed');
      expect(result.current.visualizationState.heatmapState.data).toBeDefined();
      expect(result.current.visualizationState.heatmapState.progress).toBe(100);
    });
    
    test('should handle heatmap processing errors', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // Mock console.error to avoid test output
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      await act(async () => {
        // Pass invalid data to trigger error
        await result.current.actions.processHeatmapData(null);
      });
      
      expect(result.current.visualizationState.heatmapState.status).toBe('failed');
      expect(result.current.error).toBeDefined();
      
      consoleSpy.mockRestore();
    });
    
    test('should optimize large heatmap datasets', async () => {
      const options = { heatmapOptimizationThreshold: 5 };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      const largeHeatmapData = {
        dataPoints: Array.from({ length: 10 }, (_, i) => ({
          x: Math.random(),
          y: Math.random(),
          intensity: Math.random(),
          confidence: Math.random(),
          frameNumber: i,
          regionType: 'detection'
        })),
        frameCount: 10,
        maxIntensity: 1.0,
        minIntensity: 0.0,
        metadata: {},
        processingTime: 0
      };
      
      await act(async () => {
        await result.current.actions.processHeatmapData(largeHeatmapData);
      });
      
      expect(result.current.visualizationState.heatmapState.isOptimized).toBe(true);
      expect(result.current.visualizationState.heatmapState.data.dataPoints.length).toBeLessThanOrEqual(5);
    });
    
    test('should disable heatmap processing when option is false', async () => {
      const options = { enableHeatmapProcessing: false };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      const heatmapData = {
        dataPoints: [],
        frameCount: 0,
        maxIntensity: 0,
        minIntensity: 0,
        metadata: {},
        processingTime: 0
      };
      
      await act(async () => {
        await result.current.actions.processHeatmapData(heatmapData);
      });
      
      expect(result.current.visualizationState.heatmapState.status).toBe('idle');
    });
  });
  
  // ============================================================================
  // Export State Management Tests
  // ============================================================================
  
  describe('Export State Management', () => {
    
    test('should initiate export successfully', async () => {
      const mockExportJob = {
        exportId: 'export-123',
        status: 'initiating',
        format: 'pdf',
        analysisCount: 1
      };
      
      exportService.initiateExport.mockResolvedValue(mockExportJob);
      
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      await act(async () => {
        await result.current.actions.initiateExport('pdf', {});
      });
      
      expect(result.current.visualizationState.exportState.isExporting).toBe(true);
      expect(result.current.visualizationState.exportState.currentExport).toBeDefined();
      expect(exportService.initiateExport).toHaveBeenCalledWith({
        format: 'pdf',
        analysisIds: [MOCK_ANALYSIS_ID],
        options: {},
        userId: MOCK_USER_ID,
        permissions: MOCK_USER.permissions
      });
    });
    
    test('should handle export initiation errors', async () => {
      const exportError = new Error('Export failed');
      exportService.initiateExport.mockRejectedValue(exportError);
      
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      await act(async () => {
        await result.current.actions.initiateExport('pdf', {});
      });
      
      expect(result.current.visualizationState.exportState.isExporting).toBe(false);
      expect(result.current.visualizationState.exportState.currentExport.status).toBe('failed');
      expect(result.current.error).toBeDefined();
    });
    
    test('should cancel export', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // First initiate an export
      exportService.initiateExport.mockResolvedValue({ exportId: 'export-123' });
      
      await act(async () => {
        await result.current.actions.initiateExport('pdf', {});
      });
      
      // Then cancel it
      exportService.cancelExport.mockResolvedValue({});
      
      await act(async () => {
        await result.current.actions.cancelExport();
      });
      
      expect(result.current.visualizationState.exportState.isExporting).toBe(false);
      expect(result.current.visualizationState.exportState.currentExport.status).toBe('cancelled');
      expect(exportService.cancelExport).toHaveBeenCalledWith('export-123');
    });
    
    test('should retry failed export', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // First initiate an export
      exportService.initiateExport.mockResolvedValue({ exportId: 'export-123' });
      
      await act(async () => {
        await result.current.actions.initiateExport('pdf', {});
      });
      
      // Then retry it
      exportService.retryExport.mockResolvedValue({});
      
      await act(async () => {
        await result.current.actions.retryExport();
      });
      
      expect(result.current.visualizationState.exportState.currentExport.status).toBe('initiating');
      expect(exportService.retryExport).toHaveBeenCalledWith('export-123');
    });
    
    test('should respect export permissions', () => {
      const mockAuthWithoutPermission = {
        ...MOCK_AUTH,
        hasPermission: jest.fn(() => false)
      };
      
      useAuth.mockReturnValue(mockAuthWithoutPermission);
      
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      expect(result.current.canExport).toBe(false);
    });
    
    test('should clear export history', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // Add some export history
      act(() => {
        result.current.actions.updateConfidenceCache(1, { confidenceScore: 0.8 });
      });
      
      act(() => {
        result.current.actions.clearExportHistory();
      });
      
      expect(result.current.visualizationState.exportState.exportHistory).toEqual([]);
    });
  });
  
  // ============================================================================
  // Blockchain Verification Tests
  // ============================================================================
  
  describe('Blockchain Verification', () => {
    
    test('should refresh blockchain status', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      await act(async () => {
        await result.current.actions.refreshBlockchainStatus();
      });
      
      expect(result.current.visualizationState.blockchainState.verification.status).toBe('verified');
      expect(result.current.visualizationState.blockchainState.verification.transactionHash).toBe('0x1234567890abcdef');
    });
    
    test('should handle blockchain monitoring when disabled', async () => {
      const options = { enableBlockchainMonitoring: false };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      await act(async () => {
        await result.current.actions.refreshBlockchainStatus();
      });
      
      // Should not update blockchain state when disabled
      expect(result.current.visualizationState.blockchainState.verification.status).toBe('pending');
    });
  });
  
  // ============================================================================
  // Result Modification Tracking Tests
  // ============================================================================
  
  describe('Result Modification Tracking', () => {
    
    test('should track modifications', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      act(() => {
        // Simulate tracking a modification
        result.current.actions.updateConfidenceCache(1, { confidenceScore: 0.8 });
      });
      
      // Check if modification tracking is working
      expect(result.current.visualizationState.modificationState.modificationHistory).toBeDefined();
    });
    
    test('should mark modifications as seen', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      act(() => {
        result.current.actions.markModificationsSeen();
      });
      
      expect(result.current.visualizationState.modificationState.hasUnseenModifications).toBe(false);
    });
    
    test('should clear modification history', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      act(() => {
        result.current.actions.clearModificationHistory();
      });
      
      expect(result.current.visualizationState.modificationState.modificationHistory).toEqual([]);
      expect(result.current.visualizationState.modificationState.hasUnseenModifications).toBe(false);
    });
    
    test('should respect modification tracking when disabled', () => {
      const options = { enableModificationTracking: false };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      act(() => {
        result.current.actions.updateConfidenceCache(1, { confidenceScore: 0.8 });
      });
      
      expect(result.current.visualizationState.modificationState.modificationHistory).toEqual([]);
    });
  });
  
  // ============================================================================
  // Performance Optimization Tests
  // ============================================================================
  
  describe('Performance Optimization', () => {
    
    test('should optimize performance', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      act(() => {
        result.current.actions.optimizePerformance();
      });
      
      expect(result.current.visualizationState.performanceMetrics.lastOptimization).toBeDefined();
    });
    
    test('should disable performance optimization when option is false', () => {
      const options = { enablePerformanceOptimization: false };
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, options));
      
      const initialOptimization = result.current.visualizationState.performanceMetrics.lastOptimization;
      
      act(() => {
        result.current.actions.optimizePerformance();
      });
      
      expect(result.current.visualizationState.performanceMetrics.lastOptimization).toBe(initialOptimization);
    });
    
    test('should track performance metrics', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      expect(result.current.performanceMetrics).toHaveProperty('renderCount');
      expect(result.current.performanceMetrics).toHaveProperty('stateUpdateCount');
      expect(result.current.performanceMetrics).toHaveProperty('cacheHitRate');
      expect(result.current.performanceMetrics).toHaveProperty('averageRenderTime');
      expect(result.current.performanceMetrics).toHaveProperty('memoryUsage');
    });
  });
  
  // ============================================================================
  // WebSocket Integration Tests
  // ============================================================================
  
  describe('WebSocket Integration', () => {
    
    test('should subscribe to WebSocket events', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      expect(MOCK_WEBSOCKET.subscribe).toHaveBeenCalledWith('analysis_progress', expect.any(Function));
      expect(MOCK_WEBSOCKET.subscribe).toHaveBeenCalledWith('blockchain_update', expect.any(Function));
      expect(MOCK_WEBSOCKET.subscribe).toHaveBeenCalledWith('export_progress', expect.any(Function));
      expect(MOCK_WEBSOCKET.subscribe).toHaveBeenCalledWith('result_modification', expect.any(Function));
    });
    
    test('should unsubscribe from WebSocket events on cleanup', () => {
      const { unmount } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      unmount();
      
      expect(MOCK_WEBSOCKET.unsubscribe).toHaveBeenCalledWith('analysis_progress', expect.any(Function));
      expect(MOCK_WEBSOCKET.unsubscribe).toHaveBeenCalledWith('blockchain_update', expect.any(Function));
      expect(MOCK_WEBSOCKET.unsubscribe).toHaveBeenCalledWith('export_progress', expect.any(Function));
      expect(MOCK_WEBSOCKET.unsubscribe).toHaveBeenCalledWith('result_modification', expect.any(Function));
    });
    
    test('should handle WebSocket disconnection', () => {
      const disconnectedWebSocket = {
        ...MOCK_WEBSOCKET,
        isConnected: false
      };
      
      useWebSocket.mockReturnValue(disconnectedWebSocket);
      
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      expect(result.current.visualizationState).toBeDefined();
      expect(MOCK_WEBSOCKET.subscribe).not.toHaveBeenCalled();
    });
  });
  
  // ============================================================================
  // Error Handling Tests
  // ============================================================================
  
  describe('Error Handling', () => {
    
    test('should handle errors gracefully', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // Mock console.error to avoid test output
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      await act(async () => {
        await result.current.actions.processHeatmapData(null);
      });
      
      expect(result.current.error).toBeDefined();
      expect(result.current.visualizationState.errorHistory).toHaveLength(1);
      
      consoleSpy.mockRestore();
    });
    
    test('should maintain error history', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // Trigger multiple errors
      act(() => {
        result.current.actions.setVisualizationMode('invalid_mode');
      });
      
      act(() => {
        result.current.actions.setVisualizationMode('another_invalid_mode');
      });
      
      expect(result.current.visualizationState.errorHistory.length).toBeGreaterThan(0);
    });
    
    test('should reset visualization state', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // Change some state
      act(() => {
        result.current.actions.setVisualizationMode('detailed');
      });
      
      // Reset state
      act(() => {
        result.current.actions.resetVisualizationState();
      });
      
      expect(result.current.visualizationState.currentMode).toBe('summary');
      expect(result.current.error).toBe(null);
    });
  });
  
  // ============================================================================
  // Integration Tests
  // ============================================================================
  
  describe('Integration Tests', () => {
    
    test('should initialize with detection analysis data', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      await waitFor(() => {
        expect(result.current.visualizationState.isInitialized).toBe(true);
      });
      
      expect(result.current.isLoading).toBe(false);
    });
    
    test('should refresh all data', async () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      await act(async () => {
        await result.current.refresh();
      });
      
      expect(result.current.isLoading).toBe(false);
    });
    
    test('should cleanup on unmount', () => {
      const { result, unmount } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      const cleanup = result.current.cleanup;
      
      expect(() => cleanup()).not.toThrow();
      
      unmount();
    });
  });
  
  // ============================================================================
  // Edge Cases and Boundary Tests
  // ============================================================================
  
  describe('Edge Cases and Boundary Tests', () => {
    
    test('should handle missing analysis ID', () => {
      const { result } = renderHook(() => useResultVisualization(null));
      
      expect(result.current.visualizationState.isInitialized).toBe(false);
    });
    
    test('should handle empty options', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, {}));
      
      expect(result.current.visualizationState).toBeDefined();
    });
    
    test('should handle invalid option values', () => {
      const invalidOptions = {
        cacheSize: -1,
        debounceDelay: -100,
        heatmapOptimizationThreshold: 0
      };
      
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID, invalidOptions));
      
      // Should use default values for invalid options
      expect(result.current.visualizationState).toBeDefined();
    });
    
    test('should handle rapid state updates', () => {
      const { result } = renderHook(() => useResultVisualization(MOCK_ANALYSIS_ID));
      
      // Rapidly update visualization mode
      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.actions.setVisualizationMode('detailed');
          result.current.actions.setVisualizationMode('summary');
        }
      });
      
      expect(result.current.visualizationState.currentMode).toBeDefined();
    });
  });
});

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Helper function to wait for async operations
 */
const waitForStateChange = async (result, condition, timeout = 1000) => {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    if (condition(result.current)) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  throw new Error('Timeout waiting for state change');
};

/**
 * Helper function to create mock heatmap data
 */
const createMockHeatmapData = (pointCount = 10) => ({
  dataPoints: Array.from({ length: pointCount }, (_, i) => ({
    x: Math.random(),
    y: Math.random(),
    intensity: Math.random(),
    confidence: Math.random(),
    frameNumber: i,
    regionType: 'detection'
  })),
  frameCount: pointCount,
  maxIntensity: 1.0,
  minIntensity: 0.0,
  metadata: { source: 'test' },
  processingTime: 0
});

export { waitForStateChange, createMockHeatmapData };
