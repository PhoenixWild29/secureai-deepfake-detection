/**
 * Export API Routes
 * Work Order #39 - Multi-Format Export Capabilities
 * 
 * API endpoints for handling export requests, status checking,
 * and download functionality for multi-format detection result exports.
 */

import { Router } from 'express';
import { exportController } from '../server/controllers/exportController.js';
import { authMiddleware } from '../server/middleware/authMiddleware.js';
import { permissionMiddleware } from '../server/middleware/permissionMiddleware.js';
import { rateLimitMiddleware } from '../server/middleware/rateLimitMiddleware.js';

const router = Router();

// ============================================================================
// Middleware Configuration
// ============================================================================

// Apply authentication to all export routes
router.use(authMiddleware);

// Apply rate limiting for export operations
router.use('/initiate', rateLimitMiddleware({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10, // Limit to 10 export requests per window per IP
  message: 'Too many export requests, please try again later.'
}));

// ============================================================================
// Export Management Routes
// ============================================================================

/**
 * POST /api/exports/initiate
 * Initiate new export job
 * 
 * Body:
 * {
 *   "format": "pdf|json|csv",
 *   "analysisIds": ["analysis-id-1", "analysis-id-2"],
 *   "options": {
 *     "includeFrameAnalysis": true,
 *     "includeBlockchainVerification": true,
 *     "includeProcessingMetrics": false,
 *     "includeSuspiciousRegions": false
 *   }
 * }
 */
router.post('/initiate', 
  permissionMiddleware.checkExportPermission,
  exportController.initiateExport
);

/**
 * GET /api/exports/:exportId/status
 * Get export job status
 */
router.get('/:exportId/status',
  permissionMiddleware.checkExportAccess,
  exportController.getExportStatus
);

/**
 * GET /api/exports/:exportId/download
 * Download completed export file
 */
router.get('/:exportId/download',
  permissionMiddleware.checkExportAccess,
  exportController.downloadExport
);

/**
 * POST /api/exports/:exportId/cancel
 * Cancel active export job
 */
router.post('/:exportId/cancel',
  permissionMiddleware.checkExportAccess,
  exportController.cancelExport
);

/**
 * POST /api/exports/:exportId/retry
 * Retry failed export job
 */
router.post('/:exportId/retry',
  permissionMiddleware.checkExportAccess,
  exportController.retryExport
);

/**
 * GET /api/exports/:exportId/progress
 * Get real-time export progress (WebSocket alternative)
 */
router.get('/:exportId/progress',
  permissionMiddleware.checkExportAccess,
  exportController.getExportProgress
);

// ============================================================================
// Batch Export Routes
// ============================================================================

/**
 * POST /api/exports/batch
 * Initiate batch export for multiple analyses
 * 
 * Body:
 * {
 *   "format": "pdf|json|csv",
 *   "analysisIds": ["analysis-id-1", "analysis-id-2", "..."],
 *   "options": {
 *     "includeFrameAnalysis": true,
 *     "includeBlockchainVerification": true,
 *     "splitByAnalysis": false, // Create separate files per analysis
 *     "combineIntoOne": true    // Combine all analyses into single file
 *   }
 * }
 */
router.post('/batch',
  permissionMiddleware.checkBatchExportPermission,
  exportController.initiateBatchExport
);

/**
 * GET /api/exports/batch/:batchId/status
 * Get batch export status
 */
router.get('/batch/:batchId/status',
  permissionMiddleware.checkBatchExportAccess,
  exportController.getBatchExportStatus
);

// ============================================================================
// Preview Routes
// ============================================================================

/**
 * POST /api/exports/preview
 * Generate export format preview
 * 
 * Body:
 * {
 *   "format": "pdf|json|csv",
 *   "analysisId": "analysis-id",
 *   "options": {
 *     "includeFrameAnalysis": true,
 *     "includeBlockchainVerification": true
 *   }
 * }
 */
router.post('/preview',
  permissionMiddleware.checkPreviewPermission,
  exportController.generatePreview
);

/**
 * GET /api/exports/formats
 * Get available export formats and their configurations
 */
router.get('/formats',
  exportController.getAvailableFormats
);

// ============================================================================
// User Export Management Routes
// ============================================================================

/**
 * GET /api/users/:userId/exports
 * Get user's export history
 */
router.get('/users/:userId/exports',
  permissionMiddleware.checkUserAccess,
  exportController.getUserExportHistory
);

/**
 * GET /api/users/:userId/exports/stats
 * Get user's export statistics
 */
router.get('/users/:userId/exports/stats',
  permissionMiddleware.checkUserAccess,
  exportController.getUserExportStats
);

/**
 * DELETE /api/users/:userId/exports/:exportId
 * Delete user's export record
 */
router.delete('/users/:userId/exports/:exportId',
  permissionMiddleware.checkUserAccess,
  exportController.deleteUserExport
);

// ============================================================================
// Admin Routes
// ============================================================================

/**
 * GET /api/admin/exports
 * Get all export jobs (admin only)
 */
router.get('/admin/exports',
  permissionMiddleware.requireAdmin,
  exportController.getAllExports
);

/**
 * GET /api/admin/exports/stats
 * Get system-wide export statistics (admin only)
 */
router.get('/admin/exports/stats',
  permissionMiddleware.requireAdmin,
  exportController.getSystemExportStats
);

/**
 * POST /api/admin/exports/cleanup
 * Cleanup old export files (admin only)
 */
router.post('/admin/exports/cleanup',
  permissionMiddleware.requireAdmin,
  exportController.cleanupOldExports
);

// ============================================================================
// File Upload Route (for export file storage)
// ============================================================================

/**
 * POST /api/exports/upload
 * Upload export file to storage
 */
router.post('/upload',
  permissionMiddleware.checkUploadPermission,
  exportController.uploadExportFile
);

// ============================================================================
// WebSocket Routes (if using Socket.IO)
// ============================================================================

/**
 * WebSocket connection for real-time export progress updates
 * ws://localhost:8000/api/exports/ws/:exportId
 */
router.ws('/ws/:exportId', (ws, req) => {
  const { exportId } = req.params;
  const userId = req.user?.id;

  if (!userId) {
    ws.close(1008, 'Authentication required');
    return;
  }

  // Subscribe to export progress updates
  exportController.subscribeToExportProgress(exportId, userId, ws);
});

// ============================================================================
// Error Handling
// ============================================================================

// Handle 404 for export routes
router.use('*', (req, res) => {
  res.status(404).json({
    error: 'Export endpoint not found',
    message: `The requested export endpoint ${req.originalUrl} does not exist.`,
    availableEndpoints: [
      'POST /api/exports/initiate',
      'GET /api/exports/:exportId/status',
      'GET /api/exports/:exportId/download',
      'POST /api/exports/:exportId/cancel',
      'POST /api/exports/:exportId/retry',
      'POST /api/exports/batch',
      'POST /api/exports/preview',
      'GET /api/exports/formats',
      'GET /api/users/:userId/exports'
    ]
  });
});

// Global error handler for export routes
router.use((error, req, res, next) => {
  console.error('Export route error:', error);

  // Handle specific error types
  if (error.name === 'ValidationError') {
    return res.status(400).json({
      error: 'Validation Error',
      message: error.message,
      details: error.details
    });
  }

  if (error.name === 'PermissionError') {
    return res.status(403).json({
      error: 'Permission Denied',
      message: error.message
    });
  }

  if (error.name === 'ExportError') {
    return res.status(500).json({
      error: 'Export Error',
      message: error.message,
      exportId: error.exportId
    });
  }

  // Generic error response
  res.status(500).json({
    error: 'Internal Server Error',
    message: 'An unexpected error occurred during export processing.',
    requestId: req.id
  });
});

// ============================================================================
// Export Router
// ============================================================================

export { router as exportRoutes };
export default router;
