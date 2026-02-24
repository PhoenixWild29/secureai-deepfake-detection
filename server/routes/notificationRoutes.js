/**
 * Notification Routes
 * Backend API routes for notification management
 */

const express = require('express');
const router = express.Router();
const notificationService = require('../services/notificationService');
const { authenticateToken } = require('../middleware/auth_middleware');
const { validateNotificationFilter, validatePreferences } = require('../middleware/validation');

/**
 * GET /api/v1/notifications/:userId
 * Get notifications for a user with optional filtering
 */
router.get('/:userId', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    const filter = req.query;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    // Validate filter parameters
    const validationResult = validateNotificationFilter(filter);
    if (!validationResult.isValid) {
      return res.status(400).json({
        success: false,
        error: validationResult.errors.join(', ')
      });
    }

    const result = await notificationService.getNotifications(userId, filter);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error fetching notifications:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch notifications'
    });
  }
});

/**
 * GET /api/v1/notifications/:userId/history
 * Get notification history with advanced filtering
 */
router.get('/:userId/history', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    const filter = req.query;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const result = await notificationService.getNotificationHistory(userId, filter);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error fetching notification history:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch notification history'
    });
  }
});

/**
 * POST /api/v1/notifications/:notificationId/read
 * Mark notification as read
 */
router.post('/:notificationId/read', authenticateToken, async (req, res) => {
  try {
    const { notificationId } = req.params;
    const userId = req.user.id;

    const result = await notificationService.markAsRead(notificationId, userId);
    
    if (!result.success) {
      return res.status(400).json(result);
    }

    res.json({
      success: true,
      data: result.data
    });
  } catch (error) {
    console.error('Error marking notification as read:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to mark notification as read'
    });
  }
});

/**
 * POST /api/v1/notifications/:notificationId/dismiss
 * Dismiss notification
 */
router.post('/:notificationId/dismiss', authenticateToken, async (req, res) => {
  try {
    const { notificationId } = req.params;
    const userId = req.user.id;

    const result = await notificationService.dismissNotification(notificationId, userId);
    
    if (!result.success) {
      return res.status(400).json(result);
    }

    res.json({
      success: true,
      data: result.data
    });
  } catch (error) {
    console.error('Error dismissing notification:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to dismiss notification'
    });
  }
});

/**
 * POST /api/v1/notifications/:notificationId/archive
 * Archive notification
 */
router.post('/:notificationId/archive', authenticateToken, async (req, res) => {
  try {
    const { notificationId } = req.params;
    const userId = req.user.id;

    const result = await notificationService.archiveNotification(notificationId, userId);
    
    if (!result.success) {
      return res.status(400).json(result);
    }

    res.json({
      success: true,
      data: result.data
    });
  } catch (error) {
    console.error('Error archiving notification:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to archive notification'
    });
  }
});

/**
 * DELETE /api/v1/notifications/:notificationId
 * Delete notification
 */
router.delete('/:notificationId', authenticateToken, async (req, res) => {
  try {
    const { notificationId } = req.params;
    const userId = req.user.id;

    const result = await notificationService.deleteNotification(notificationId, userId);
    
    if (!result.success) {
      return res.status(400).json(result);
    }

    res.json({
      success: true,
      data: result.data
    });
  } catch (error) {
    console.error('Error deleting notification:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to delete notification'
    });
  }
});

/**
 * POST /api/v1/notifications/:userId/mark-all-read
 * Mark all notifications as read for a user
 */
router.post('/:userId/mark-all-read', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const result = await notificationService.markAllAsRead(userId);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error marking all notifications as read:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to mark all notifications as read'
    });
  }
});

/**
 * GET /api/v1/notifications/:userId/preferences
 * Get user notification preferences
 */
router.get('/:userId/preferences', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const preferences = await notificationService.getPreferences(userId);
    
    res.json({
      success: true,
      data: preferences
    });
  } catch (error) {
    console.error('Error fetching preferences:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch preferences'
    });
  }
});

/**
 * PUT /api/v1/notifications/:userId/preferences
 * Update user notification preferences
 */
router.put('/:userId/preferences', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    const preferences = req.body;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    // Validate preferences
    const validationResult = validatePreferences(preferences);
    if (!validationResult.isValid) {
      return res.status(400).json({
        success: false,
        error: validationResult.errors.join(', ')
      });
    }

    const result = await notificationService.updatePreferences(userId, preferences);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error updating preferences:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update preferences'
    });
  }
});

/**
 * GET /api/v1/notifications/:userId/stats
 * Get notification statistics for a user
 */
router.get('/:userId/stats', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const stats = await notificationService.getStats(userId);
    
    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch stats'
    });
  }
});

/**
 * POST /api/v1/notifications/:userId/test
 * Send test notification
 */
router.post('/:userId/test', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    const { type } = req.body;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const result = await notificationService.sendTestNotification(userId, type);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error sending test notification:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to send test notification'
    });
  }
});

/**
 * GET /api/v1/notifications/:userId/export
 * Export notification history
 */
router.get('/:userId/export', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    const { format = 'csv' } = req.query;
    const filter = req.query;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const result = await notificationService.exportHistory(userId, format, filter);
    
    // Set appropriate headers for file download
    const filename = `notifications_${userId}_${new Date().toISOString().split('T')[0]}.${format}`;
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    
    if (format === 'csv') {
      res.setHeader('Content-Type', 'text/csv');
    } else if (format === 'json') {
      res.setHeader('Content-Type', 'application/json');
    } else if (format === 'pdf') {
      res.setHeader('Content-Type', 'application/pdf');
    }

    res.send(result);
  } catch (error) {
    console.error('Error exporting notifications:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to export notifications'
    });
  }
});

/**
 * POST /api/v1/notifications/preferences/validate
 * Validate notification preferences
 */
router.post('/preferences/validate', authenticateToken, async (req, res) => {
  try {
    const preferences = req.body;

    const validationResult = validatePreferences(preferences);
    
    res.json({
      success: validationResult.isValid,
      data: {
        isValid: validationResult.isValid,
        errors: validationResult.errors
      }
    });
  } catch (error) {
    console.error('Error validating preferences:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to validate preferences'
    });
  }
});

/**
 * POST /api/v1/notifications/bulk-action
 * Perform bulk actions on notifications
 */
router.post('/bulk-action', authenticateToken, async (req, res) => {
  try {
    const { action, notificationIds } = req.body;
    const userId = req.user.id;

    if (!action || !notificationIds || !Array.isArray(notificationIds)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid bulk action parameters'
      });
    }

    const result = await notificationService.performBulkAction(userId, action, notificationIds);
    
    res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error('Error performing bulk action:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to perform bulk action'
    });
  }
});

/**
 * GET /api/v1/notifications/:userId/unread-count
 * Get unread notification count
 */
router.get('/:userId/unread-count', authenticateToken, async (req, res) => {
  try {
    const { userId } = req.params;
    
    // Validate user access
    if (req.user.id !== userId && !req.user.isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Access denied'
      });
    }

    const count = await notificationService.getUnreadCount(userId);
    
    res.json({
      success: true,
      data: { count }
    });
  } catch (error) {
    console.error('Error fetching unread count:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch unread count'
    });
  }
});

module.exports = router;
