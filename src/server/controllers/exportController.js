/**
 * Export Controller
 * Work Order #39 - Multi-Format Export Capabilities
 * 
 * Controller functions for handling export requests, orchestrating data retrieval
 * from Core Detection Engine, permission validation, and format-specific generation.
 */

import { ExportJob } from '../models/ExportJob.js';
import { ExportProgressTracker } from '../utils/ExportProgressTracker.js';
import { coreDetectionEngineClient } from '../utils/coreDetectionEngineClient.js';
import { pdfGenerator } from '../utils/pdfGenerator.js';
import { jsonGenerator } from '../utils/jsonGenerator.js';
import { csvGenerator } from '../utils/csvGenerator.js';
import { exportAuditLogger } from '../utils/exportAuditLogger.js';

// ============================================================================
// Export Controller Class
// ============================================================================

export class ExportController {
  constructor() {
    this.activeExports = new Map();
    this.progressTracker = new ExportProgressTracker();
    this.auditLogger = exportAuditLogger;
  }

  // ============================================================================
  // Export Initiation
  // ============================================================================

  /**
   * Initiate new export job
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async initiateExport(req, res) {
    try {
      const { format, analysisIds, options = {} } = req.body;
      const userId = req.user.id;
      const userPermissions = req.user.permissions;

      // Validate request
      this.validateExportRequest(req.body);

      // Check permissions
      await this.checkExportPermissions(userId, format, analysisIds, userPermissions);

      // Create export job
      const exportJob = await this.createExportJob({
        format,
        analysisIds,
        options,
        userId,
        status: 'initiating',
        createdAt: new Date()
      });

      // Start processing asynchronously
      this.processExportJob(exportJob).catch(error => {
        console.error(`Export job ${exportJob.id} failed:`, error);
        this.failExportJob(exportJob.id, error);
      });

      // Log audit event
      await this.auditLogger.logExportInitiated(userId, exportJob.id, format, analysisIds.length);

      // Return job information
      res.status(201).json({
        success: true,
        exportId: exportJob.id,
        status: 'initiating',
        format,
        analysisCount: analysisIds.length,
        estimatedCompletion: this.calculateEstimatedCompletion(format, analysisIds.length),
        createdAt: exportJob.createdAt
      });

    } catch (error) {
      console.error('Export initiation failed:', error);
      res.status(400).json({
        success: false,
        error: error.message,
        code: error.code || 'EXPORT_INITIATION_FAILED'
      });
    }
  }

  /**
   * Initiate batch export for multiple analyses
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async initiateBatchExport(req, res) {
    try {
      const { format, analysisIds, options = {} } = req.body;
      const userId = req.user.id;
      const userPermissions = req.user.permissions;

      // Validate batch request
      this.validateBatchExportRequest(req.body);

      // Check batch permissions
      await this.checkBatchExportPermissions(userId, format, analysisIds, userPermissions);

      // Create batch export job
      const batchExportJob = await this.createBatchExportJob({
        format,
        analysisIds,
        options,
        userId,
        status: 'initiating',
        createdAt: new Date()
      });

      // Start batch processing asynchronously
      this.processBatchExportJob(batchExportJob).catch(error => {
        console.error(`Batch export job ${batchExportJob.id} failed:`, error);
        this.failExportJob(batchExportJob.id, error);
      });

      // Log audit event
      await this.auditLogger.logBatchExportInitiated(userId, batchExportJob.id, format, analysisIds.length);

      // Return batch job information
      res.status(201).json({
        success: true,
        batchId: batchExportJob.id,
        status: 'initiating',
        format,
        analysisCount: analysisIds.length,
        estimatedCompletion: this.calculateBatchEstimatedCompletion(format, analysisIds.length),
        createdAt: batchExportJob.createdAt
      });

    } catch (error) {
      console.error('Batch export initiation failed:', error);
      res.status(400).json({
        success: false,
        error: error.message,
        code: error.code || 'BATCH_EXPORT_INITIATION_FAILED'
      });
    }
  }

  // ============================================================================
  // Export Status and Management
  // ============================================================================

  /**
   * Get export job status
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async getExportStatus(req, res) {
    try {
      const { exportId } = req.params;
      const userId = req.user.id;

      // Get export job
      const exportJob = await ExportJob.findById(exportId);
      
      if (!exportJob) {
        return res.status(404).json({
          success: false,
          error: 'Export job not found'
        });
      }

      // Check access permissions
      if (exportJob.userId !== userId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to this export job'
        });
      }

      // Get current progress
      const progress = await this.progressTracker.getProgress(exportId);

      res.json({
        success: true,
        exportId: exportJob.id,
        status: exportJob.status,
        format: exportJob.format,
        progress: progress.progress || 0,
        message: progress.message || 'Processing...',
        createdAt: exportJob.createdAt,
        completedAt: exportJob.completedAt,
        downloadUrl: exportJob.status === 'completed' ? this.generateDownloadUrl(exportId) : null,
        errorMessage: exportJob.errorMessage,
        estimatedCompletion: exportJob.estimatedCompletion
      });

    } catch (error) {
      console.error('Export status check failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get export status'
      });
    }
  }

  /**
   * Download completed export file
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async downloadExport(req, res) {
    try {
      const { exportId } = req.params;
      const userId = req.user.id;

      // Get export job
      const exportJob = await ExportJob.findById(exportId);
      
      if (!exportJob) {
        return res.status(404).json({
          success: false,
          error: 'Export job not found'
        });
      }

      // Check access permissions
      if (exportJob.userId !== userId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to this export'
        });
      }

      // Check if export is completed
      if (exportJob.status !== 'completed') {
        return res.status(400).json({
          success: false,
          error: 'Export not completed yet'
        });
      }

      // Get file path
      const filePath = exportJob.filePath;
      if (!filePath) {
        return res.status(404).json({
          success: false,
          error: 'Export file not found'
        });
      }

      // Set download headers
      res.setHeader('Content-Type', exportJob.mimeType);
      res.setHeader('Content-Disposition', `attachment; filename="${exportJob.fileName}"`);
      res.setHeader('Content-Length', exportJob.fileSize);

      // Stream file
      const fs = require('fs');
      const fileStream = fs.createReadStream(filePath);
      
      fileStream.pipe(res);
      
      fileStream.on('error', (error) => {
        console.error('File stream error:', error);
        if (!res.headersSent) {
          res.status(500).json({
            success: false,
            error: 'Failed to download export file'
          });
        }
      });

      // Log download event
      await this.auditLogger.logExportDownloaded(userId, exportId);

    } catch (error) {
      console.error('Export download failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to download export'
      });
    }
  }

  /**
   * Cancel active export job
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async cancelExport(req, res) {
    try {
      const { exportId } = req.params;
      const userId = req.user.id;

      // Get export job
      const exportJob = await ExportJob.findById(exportId);
      
      if (!exportJob) {
        return res.status(404).json({
          success: false,
          error: 'Export job not found'
        });
      }

      // Check access permissions
      if (exportJob.userId !== userId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to this export job'
        });
      }

      // Check if export can be cancelled
      if (!['initiating', 'processing', 'generating'].includes(exportJob.status)) {
        return res.status(400).json({
          success: false,
          error: 'Export cannot be cancelled in current status'
        });
      }

      // Cancel export job
      await this.cancelExportJob(exportId);

      // Log cancellation event
      await this.auditLogger.logExportCancelled(userId, exportId);

      res.json({
        success: true,
        message: 'Export cancelled successfully'
      });

    } catch (error) {
      console.error('Export cancellation failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to cancel export'
      });
    }
  }

  /**
   * Retry failed export job
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async retryExport(req, res) {
    try {
      const { exportId } = req.params;
      const userId = req.user.id;

      // Get export job
      const exportJob = await ExportJob.findById(exportId);
      
      if (!exportJob) {
        return res.status(404).json({
          success: false,
          error: 'Export job not found'
        });
      }

      // Check access permissions
      if (exportJob.userId !== userId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to this export job'
        });
      }

      // Check if export can be retried
      if (exportJob.status !== 'failed') {
        return res.status(400).json({
          success: false,
          error: 'Only failed exports can be retried'
        });
      }

      // Reset export job for retry
      await this.resetExportJobForRetry(exportId);

      // Restart processing
      this.processExportJob(exportJob).catch(error => {
        console.error(`Retry export job ${exportId} failed:`, error);
        this.failExportJob(exportId, error);
      });

      // Log retry event
      await this.auditLogger.logExportRetried(userId, exportId);

      res.json({
        success: true,
        message: 'Export retry initiated successfully'
      });

    } catch (error) {
      console.error('Export retry failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to retry export'
      });
    }
  }

  // ============================================================================
  // Preview Generation
  // ============================================================================

  /**
   * Generate export format preview
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async generatePreview(req, res) {
    try {
      const { format, analysisId, options = {} } = req.body;
      const userId = req.user.id;

      // Validate preview request
      this.validatePreviewRequest(req.body);

      // Get analysis data
      const analysisData = await this.coreDetectionEngineClient.getAnalysisData(analysisId);
      
      if (!analysisData) {
        return res.status(404).json({
          success: false,
          error: 'Analysis not found'
        });
      }

      // Generate preview based on format
      let preview;
      switch (format) {
        case 'pdf':
          preview = await this.generatePDFPreview(analysisData, options);
          break;
        case 'json':
          preview = await this.generateJSONPreview(analysisData, options);
          break;
        case 'csv':
          preview = await this.generateCSVPreview(analysisData, options);
          break;
        default:
          throw new Error(`Preview not supported for format: ${format}`);
      }

      res.json({
        success: true,
        format,
        preview,
        generatedAt: new Date().toISOString()
      });

    } catch (error) {
      console.error('Preview generation failed:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  }

  /**
   * Get available export formats and their configurations
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async getAvailableFormats(req, res) {
    try {
      const formats = {
        pdf: {
          name: 'PDF Report',
          description: 'Professional report with formatted detection results',
          icon: '📄',
          mimeType: 'application/pdf',
          extension: '.pdf',
          supportsBatch: true,
          requiresPreview: true,
          maxFileSize: '50MB',
          estimatedTime: '30-60 seconds'
        },
        json: {
          name: 'JSON Data',
          description: 'Complete detection result data structure',
          icon: '📋',
          mimeType: 'application/json',
          extension: '.json',
          supportsBatch: true,
          requiresPreview: false,
          maxFileSize: '10MB',
          estimatedTime: '10-20 seconds'
        },
        csv: {
          name: 'CSV Summary',
          description: 'Tabular data for spreadsheet analysis',
          icon: '📊',
          mimeType: 'text/csv',
          extension: '.csv',
          supportsBatch: true,
          requiresPreview: false,
          maxFileSize: '5MB',
          estimatedTime: '15-30 seconds'
        }
      };

      res.json({
        success: true,
        formats,
        userPermissions: {
          allowedFormats: req.user.permissions?.allowedFormats || Object.keys(formats),
          maxBatchSize: req.user.permissions?.maxBatchSize || 10,
          dataAccessLevel: req.user.permissions?.dataAccessLevel || 'standard'
        }
      });

    } catch (error) {
      console.error('Format information retrieval failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get format information'
      });
    }
  }

  // ============================================================================
  // User Export Management
  // ============================================================================

  /**
   * Get user's export history
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async getUserExportHistory(req, res) {
    try {
      const { userId } = req.params;
      const requestingUserId = req.user.id;
      const page = parseInt(req.query.page) || 1;
      const limit = parseInt(req.query.limit) || 20;

      // Check access permissions
      if (userId !== requestingUserId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to user export history'
        });
      }

      // Get export history with pagination
      const exports = await ExportJob.findByUserId(userId, {
        page,
        limit,
        sort: { createdAt: -1 }
      });

      res.json({
        success: true,
        exports: exports.data,
        pagination: {
          page: exports.page,
          limit: exports.limit,
          total: exports.total,
          pages: exports.pages
        }
      });

    } catch (error) {
      console.error('Export history retrieval failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get export history'
      });
    }
  }

  /**
   * Get user's export statistics
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async getUserExportStats(req, res) {
    try {
      const { userId } = req.params;
      const requestingUserId = req.user.id;

      // Check access permissions
      if (userId !== requestingUserId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to user export statistics'
        });
      }

      // Get export statistics
      const stats = await ExportJob.getUserStats(userId);

      res.json({
        success: true,
        stats
      });

    } catch (error) {
      console.error('Export statistics retrieval failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get export statistics'
      });
    }
  }

  /**
   * Delete user's export record
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async deleteUserExport(req, res) {
    try {
      const { userId, exportId } = req.params;
      const requestingUserId = req.user.id;

      // Check access permissions
      if (userId !== requestingUserId && !req.user.permissions?.isAdmin) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to delete this export'
        });
      }

      // Get export job
      const exportJob = await ExportJob.findById(exportId);
      
      if (!exportJob || exportJob.userId !== userId) {
        return res.status(404).json({
          success: false,
          error: 'Export not found'
        });
      }

      // Delete export job and file
      await this.deleteExportJob(exportId);

      // Log deletion event
      await this.auditLogger.logExportDeleted(requestingUserId, exportId);

      res.json({
        success: true,
        message: 'Export deleted successfully'
      });

    } catch (error) {
      console.error('Export deletion failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to delete export'
      });
    }
  }

  // ============================================================================
  // Admin Functions
  // ============================================================================

  /**
   * Get all export jobs (admin only)
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async getAllExports(req, res) {
    try {
      const page = parseInt(req.query.page) || 1;
      const limit = parseInt(req.query.limit) || 50;
      const status = req.query.status;
      const format = req.query.format;

      // Build filter
      const filter = {};
      if (status) filter.status = status;
      if (format) filter.format = format;

      // Get all exports with pagination
      const exports = await ExportJob.findAll(filter, {
        page,
        limit,
        sort: { createdAt: -1 }
      });

      res.json({
        success: true,
        exports: exports.data,
        pagination: {
          page: exports.page,
          limit: exports.limit,
          total: exports.total,
          pages: exports.pages
        }
      });

    } catch (error) {
      console.error('All exports retrieval failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get all exports'
      });
    }
  }

  /**
   * Get system-wide export statistics (admin only)
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async getSystemExportStats(req, res) {
    try {
      const stats = await ExportJob.getSystemStats();

      res.json({
        success: true,
        stats
      });

    } catch (error) {
      console.error('System export statistics retrieval failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to get system export statistics'
      });
    }
  }

  /**
   * Cleanup old export files (admin only)
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async cleanupOldExports(req, res) {
    try {
      const { olderThanDays = 30 } = req.body;

      const cleanupResult = await this.cleanupOldExportFiles(olderThanDays);

      res.json({
        success: true,
        message: 'Cleanup completed successfully',
        cleanupResult
      });

    } catch (error) {
      console.error('Export cleanup failed:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to cleanup old exports'
      });
    }
  }

  // ============================================================================
  // File Upload
  // ============================================================================

  /**
   * Upload export file to storage
   * @param {Object} req - Express request object
   * @param {Object} res - Express response object
   */
  async uploadExportFile(req, res) {
    try {
      const { content, fileName, mimeType } = req.body;
      const userId = req.user.id;

      // Validate upload request
      this.validateUploadRequest(req.body);

      // Upload file to storage
      const uploadResult = await this.uploadFileToStorage(content, fileName, mimeType, userId);

      res.json({
        success: true,
        url: uploadResult.url,
        size: uploadResult.size,
        uploadedAt: new Date().toISOString()
      });

    } catch (error) {
      console.error('File upload failed:', error);
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  }

  // ============================================================================
  // WebSocket Support
  // ============================================================================

  /**
   * Subscribe to export progress updates via WebSocket
   * @param {string} exportId - Export ID
   * @param {string} userId - User ID
   * @param {WebSocket} ws - WebSocket connection
   */
  subscribeToExportProgress(exportId, userId, ws) {
    // Subscribe to progress updates
    this.progressTracker.subscribe(exportId, userId, (progress) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'export_progress',
          exportId,
          progress
        }));
      }
    });

    // Handle WebSocket close
    ws.on('close', () => {
      this.progressTracker.unsubscribe(exportId, userId);
    });

    // Send initial status
    this.getExportProgress(exportId).then(progress => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: 'export_progress',
          exportId,
          progress
        }));
      }
    });
  }

  // ============================================================================
  // Private Helper Methods
  // ============================================================================

  /**
   * Validate export request
   * @param {Object} requestBody - Request body
   */
  validateExportRequest(requestBody) {
    const { format, analysisIds } = requestBody;

    if (!format || !['pdf', 'json', 'csv'].includes(format)) {
      throw new Error('Invalid export format. Must be pdf, json, or csv.');
    }

    if (!analysisIds || !Array.isArray(analysisIds) || analysisIds.length === 0) {
      throw new Error('Analysis IDs are required and must be a non-empty array.');
    }

    if (analysisIds.length > 100) {
      throw new Error('Too many analyses requested. Maximum 100 per export.');
    }
  }

  /**
   * Validate batch export request
   * @param {Object} requestBody - Request body
   */
  validateBatchExportRequest(requestBody) {
    this.validateExportRequest(requestBody);

    const { analysisIds } = requestBody;
    
    if (analysisIds.length > 500) {
      throw new Error('Batch export limited to 500 analyses maximum.');
    }
  }

  /**
   * Validate preview request
   * @param {Object} requestBody - Request body
   */
  validatePreviewRequest(requestBody) {
    const { format, analysisId } = requestBody;

    if (!format || !['pdf', 'json', 'csv'].includes(format)) {
      throw new Error('Invalid preview format. Must be pdf, json, or csv.');
    }

    if (!analysisId) {
      throw new Error('Analysis ID is required for preview.');
    }
  }

  /**
   * Validate upload request
   * @param {Object} requestBody - Request body
   */
  validateUploadRequest(requestBody) {
    const { content, fileName, mimeType } = requestBody;

    if (!content) {
      throw new Error('File content is required.');
    }

    if (!fileName) {
      throw new Error('File name is required.');
    }

    if (!mimeType) {
      throw new Error('MIME type is required.');
    }

    // Check file size (limit to 100MB)
    const contentSize = Buffer.byteLength(content, 'utf8');
    if (contentSize > 100 * 1024 * 1024) {
      throw new Error('File size exceeds 100MB limit.');
    }
  }

  /**
   * Check export permissions
   * @param {string} userId - User ID
   * @param {string} format - Export format
   * @param {Array} analysisIds - Analysis IDs
   * @param {Object} permissions - User permissions
   */
  async checkExportPermissions(userId, format, analysisIds, permissions) {
    // Check format permissions
    if (permissions?.allowedFormats && !permissions.allowedFormats.includes(format)) {
      throw new Error(`Export format ${format} not allowed for user`);
    }

    // Check batch size limits
    if (analysisIds.length > (permissions?.maxBatchSize || 10)) {
      throw new Error(`Batch size exceeds limit of ${permissions?.maxBatchSize || 10}`);
    }

    // Check data access level
    if (permissions?.dataAccessLevel === 'basic' && analysisIds.length > 1) {
      throw new Error('Batch export not allowed for basic users');
    }
  }

  /**
   * Check batch export permissions
   * @param {string} userId - User ID
   * @param {string} format - Export format
   * @param {Array} analysisIds - Analysis IDs
   * @param {Object} permissions - User permissions
   */
  async checkBatchExportPermissions(userId, format, analysisIds, permissions) {
    await this.checkExportPermissions(userId, format, analysisIds, permissions);

    // Additional batch-specific checks
    if (permissions?.dataAccessLevel === 'basic') {
      throw new Error('Batch export requires standard or higher access level');
    }

    if (analysisIds.length > (permissions?.maxBatchSize || 10)) {
      throw new Error(`Batch size exceeds user limit of ${permissions?.maxBatchSize || 10}`);
    }
  }

  /**
   * Create export job
   * @param {Object} jobData - Job data
   * @returns {Promise<Object>} Created job
   */
  async createExportJob(jobData) {
    const exportJob = new ExportJob(jobData);
    await exportJob.save();
    
    this.activeExports.set(exportJob.id, exportJob);
    
    return exportJob;
  }

  /**
   * Create batch export job
   * @param {Object} jobData - Job data
   * @returns {Promise<Object>} Created batch job
   */
  async createBatchExportJob(jobData) {
    const batchJob = new ExportJob({
      ...jobData,
      type: 'batch'
    });
    
    await batchJob.save();
    
    this.activeExports.set(batchJob.id, batchJob);
    
    return batchJob;
  }

  /**
   * Process export job asynchronously
   * @param {Object} exportJob - Export job to process
   */
  async processExportJob(exportJob) {
    try {
      // Update status to processing
      await this.updateExportStatus(exportJob.id, 'processing', 10, 'Retrieving analysis data...');

      // Retrieve analysis data
      const analysisData = await this.retrieveAnalysisData(exportJob.analysisIds);

      // Update progress
      await this.updateExportStatus(exportJob.id, 'generating', 50, `Generating ${exportJob.format.toUpperCase()} export...`);

      // Generate export based on format
      const exportResult = await this.generateExport(exportJob.format, analysisData, exportJob.options);

      // Update progress
      await this.updateExportStatus(exportJob.id, 'completing', 90, 'Finalizing export...');

      // Complete export
      await this.completeExportJob(exportJob.id, exportResult);

    } catch (error) {
      await this.failExportJob(exportJob.id, error);
    }
  }

  /**
   * Process batch export job asynchronously
   * @param {Object} batchJob - Batch export job to process
   */
  async processBatchExportJob(batchJob) {
    try {
      // Update status to processing
      await this.updateExportStatus(batchJob.id, 'processing', 10, 'Processing batch export...');

      // Retrieve all analysis data
      const analysisData = await this.retrieveAnalysisData(batchJob.analysisIds);

      // Update progress
      await this.updateExportStatus(batchJob.id, 'generating', 50, `Generating batch ${batchJob.format.toUpperCase()} export...`);

      // Generate batch export
      const exportResult = await this.generateBatchExport(batchJob.format, analysisData, batchJob.options);

      // Update progress
      await this.updateExportStatus(batchJob.id, 'completing', 90, 'Finalizing batch export...');

      // Complete export
      await this.completeExportJob(batchJob.id, exportResult);

    } catch (error) {
      await this.failExportJob(batchJob.id, error);
    }
  }

  /**
   * Generate export based on format
   * @param {string} format - Export format
   * @param {Array} analysisData - Analysis data
   * @param {Object} options - Export options
   * @returns {Promise<Object>} Export result
   */
  async generateExport(format, analysisData, options) {
    switch (format) {
      case 'pdf':
        return await pdfGenerator.generateExport(analysisData, options);
      case 'json':
        return await jsonGenerator.generateExport(analysisData, options);
      case 'csv':
        return await csvGenerator.generateExport(analysisData, options);
      default:
        throw new Error(`Unsupported export format: ${format}`);
    }
  }

  /**
   * Generate batch export
   * @param {string} format - Export format
   * @param {Array} analysisData - Analysis data
   * @param {Object} options - Export options
   * @returns {Promise<Object>} Batch export result
   */
  async generateBatchExport(format, analysisData, options) {
    if (options.combineIntoOne) {
      // Generate single file with all analyses
      return await this.generateExport(format, analysisData, options);
    } else {
      // Generate separate files for each analysis
      const files = [];
      for (const analysis of analysisData) {
        const result = await this.generateExport(format, [analysis], options);
        files.push(result);
      }
      return { files, type: 'multiple' };
    }
  }

  /**
   * Retrieve analysis data from Core Detection Engine
   * @param {Array} analysisIds - Analysis IDs
   * @returns {Promise<Array>} Analysis data
   */
  async retrieveAnalysisData(analysisIds) {
    const analysisData = [];

    for (const analysisId of analysisIds) {
      try {
        const data = await this.coreDetectionEngineClient.getAnalysisData(analysisId);
        if (data) {
          analysisData.push(data);
        }
      } catch (error) {
        console.error(`Failed to retrieve analysis ${analysisId}:`, error);
        throw new Error(`Failed to retrieve analysis data for ${analysisId}`);
      }
    }

    return analysisData;
  }

  /**
   * Update export status and progress
   * @param {string} exportId - Export ID
   * @param {string} status - New status
   * @param {number} progress - Progress percentage
   * @param {string} message - Status message
   */
  async updateExportStatus(exportId, status, progress, message) {
    const exportJob = await ExportJob.findById(exportId);
    if (exportJob) {
      exportJob.status = status;
      exportJob.progress = progress;
      exportJob.message = message;
      await exportJob.save();
    }

    // Update progress tracker
    await this.progressTracker.updateProgress(exportId, {
      status,
      progress,
      message,
      timestamp: new Date()
    });
  }

  /**
   * Complete export job
   * @param {string} exportId - Export ID
   * @param {Object} result - Export result
   */
  async completeExportJob(exportId, result) {
    const exportJob = await ExportJob.findById(exportId);
    if (exportJob) {
      exportJob.status = 'completed';
      exportJob.progress = 100;
      exportJob.message = 'Export completed successfully';
      exportJob.filePath = result.filePath;
      exportJob.fileName = result.fileName;
      exportJob.fileSize = result.fileSize;
      exportJob.mimeType = result.mimeType;
      exportJob.completedAt = new Date();
      await exportJob.save();
    }

    // Update progress tracker
    await this.progressTracker.updateProgress(exportId, {
      status: 'completed',
      progress: 100,
      message: 'Export completed successfully',
      timestamp: new Date()
    });

    this.activeExports.delete(exportId);
  }

  /**
   * Fail export job
   * @param {string} exportId - Export ID
   * @param {Error} error - Error object
   */
  async failExportJob(exportId, error) {
    const exportJob = await ExportJob.findById(exportId);
    if (exportJob) {
      exportJob.status = 'failed';
      exportJob.progress = 0;
      exportJob.message = 'Export failed';
      exportJob.errorMessage = error.message;
      await exportJob.save();
    }

    // Update progress tracker
    await this.progressTracker.updateProgress(exportId, {
      status: 'failed',
      progress: 0,
      message: 'Export failed',
      error: error.message,
      timestamp: new Date()
    });

    this.activeExports.delete(exportId);
  }

  /**
   * Cancel export job
   * @param {string} exportId - Export ID
   */
  async cancelExportJob(exportId) {
    const exportJob = await ExportJob.findById(exportId);
    if (exportJob) {
      exportJob.status = 'cancelled';
      exportJob.message = 'Export cancelled by user';
      await exportJob.save();
    }

    // Update progress tracker
    await this.progressTracker.updateProgress(exportId, {
      status: 'cancelled',
      progress: 0,
      message: 'Export cancelled by user',
      timestamp: new Date()
    });

    this.activeExports.delete(exportId);
  }

  /**
   * Reset export job for retry
   * @param {string} exportId - Export ID
   */
  async resetExportJobForRetry(exportId) {
    const exportJob = await ExportJob.findById(exportId);
    if (exportJob) {
      exportJob.status = 'initiating';
      exportJob.progress = 0;
      exportJob.message = 'Retrying export...';
      exportJob.errorMessage = null;
      exportJob.retryCount = (exportJob.retryCount || 0) + 1;
      await exportJob.save();
    }
  }

  /**
   * Calculate estimated completion time
   * @param {string} format - Export format
   * @param {number} analysisCount - Number of analyses
   * @returns {string} Estimated completion time
   */
  calculateEstimatedCompletion(format, analysisCount) {
    const baseTime = {
      pdf: 30000,   // 30 seconds
      json: 10000,  // 10 seconds
      csv: 15000    // 15 seconds
    };

    const estimatedMs = baseTime[format] + (analysisCount * 2000); // 2 seconds per analysis
    return new Date(Date.now() + estimatedMs).toISOString();
  }

  /**
   * Calculate batch estimated completion time
   * @param {string} format - Export format
   * @param {number} analysisCount - Number of analyses
   * @returns {string} Estimated completion time
   */
  calculateBatchEstimatedCompletion(format, analysisCount) {
    // Batch exports take longer due to coordination overhead
    const multiplier = 1.5;
    const baseTime = this.calculateEstimatedCompletion(format, analysisCount);
    const baseMs = new Date(baseTime).getTime() - Date.now();
    const estimatedMs = Math.ceil(baseMs * multiplier);
    
    return new Date(Date.now() + estimatedMs).toISOString();
  }

  /**
   * Generate download URL
   * @param {string} exportId - Export ID
   * @returns {string} Download URL
   */
  generateDownloadUrl(exportId) {
    return `${this.baseUrl}/api/exports/${exportId}/download`;
  }

  /**
   * Upload file to storage
   * @param {string} content - File content
   * @param {string} fileName - File name
   * @param {string} mimeType - MIME type
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Upload result
   */
  async uploadFileToStorage(content, fileName, mimeType, userId) {
    // Implementation would depend on storage backend (S3, local filesystem, etc.)
    // This is a simplified version
    const uploadPath = `exports/${userId}/${Date.now()}_${fileName}`;
    
    // Save file to storage (implementation depends on storage backend)
    const fs = require('fs').promises;
    const path = require('path');
    
    const fullPath = path.join(process.env.EXPORT_STORAGE_PATH || './exports', uploadPath);
    await fs.mkdir(path.dirname(fullPath), { recursive: true });
    await fs.writeFile(fullPath, content);
    
    return {
      url: `/api/exports/download/${uploadPath}`,
      size: Buffer.byteLength(content, 'utf8'),
      path: fullPath
    };
  }

  /**
   * Delete export job and associated files
   * @param {string} exportId - Export ID
   */
  async deleteExportJob(exportId) {
    const exportJob = await ExportJob.findById(exportId);
    if (exportJob) {
      // Delete associated file
      if (exportJob.filePath) {
        try {
          const fs = require('fs').promises;
          await fs.unlink(exportJob.filePath);
        } catch (error) {
          console.error(`Failed to delete export file ${exportJob.filePath}:`, error);
        }
      }

      // Delete database record
      await ExportJob.deleteById(exportId);
    }
  }

  /**
   * Cleanup old export files
   * @param {number} olderThanDays - Delete files older than this many days
   * @returns {Promise<Object>} Cleanup result
   */
  async cleanupOldExportFiles(olderThanDays) {
    const cutoffDate = new Date(Date.now() - (olderThanDays * 24 * 60 * 60 * 1000));
    
    // Find old export jobs
    const oldExports = await ExportJob.findOldExports(cutoffDate);
    
    let deletedCount = 0;
    let errorCount = 0;

    for (const exportJob of oldExports) {
      try {
        await this.deleteExportJob(exportJob.id);
        deletedCount++;
      } catch (error) {
        console.error(`Failed to cleanup export ${exportJob.id}:`, error);
        errorCount++;
      }
    }

    return {
      deletedCount,
      errorCount,
      totalProcessed: oldExports.length
    };
  }

  /**
   * Get export progress
   * @param {string} exportId - Export ID
   * @returns {Promise<Object>} Progress data
   */
  async getExportProgress(exportId) {
    return await this.progressTracker.getProgress(exportId);
  }
}

// ============================================================================
// Export Controller Instance
// ============================================================================

export const exportController = new ExportController();
