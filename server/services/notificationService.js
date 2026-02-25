/**
 * Notification Service Layer
 * Business logic for handling notifications, preferences, and real-time updates
 */

const mongoose = require('mongoose');
const Notification = require('../models/Notification');
const UserPreferences = require('../models/UserPreferences');
const { WebSocket } = require('ws');

class NotificationService {
  constructor() {
    this.websocketConnections = new Map();
    this.setupWebSocketServer();
  }

  /**
   * Create a new notification
   */
  async createNotification(notificationData) {
    try {
      const {
        userId,
        type,
        title,
        message,
        content,
        priority = 'medium',
        metadata = {},
        actions = [],
        deliveryMethods = ['in_app'],
        expiresAt
      } = notificationData;

      // Validate required fields
      if (!userId || !type || !title || !message) {
        throw new Error('Missing required notification fields');
      }

      // Get user preferences to determine delivery methods
      const userPreferences = await UserPreferences.findByUserId(userId);
      if (userPreferences && userPreferences.notificationPreferences) {
        const typePreferences = userPreferences.notificationPreferences[type];
        if (typePreferences && typePreferences.enabled) {
          deliveryMethods.push(typePreferences.deliveryMethod);
        }
      }

      // Create notification
      const notification = new Notification({
        userId,
        type,
        title,
        message,
        content,
        priority,
        status: 'unread',
        actions: actions.map(action => ({
          id: action.id || mongoose.Types.ObjectId().toString(),
          label: action.label,
          type: action.type,
          url: action.url,
          handler: action.handler
        })),
        metadata,
        deliveryMethods: [...new Set(deliveryMethods)], // Remove duplicates
        expiresAt,
        createdAt: new Date(),
        updatedAt: new Date()
      });

      const savedNotification = await notification.save();

      // Send real-time update
      await this.sendRealTimeUpdate(userId, 'notification_created', savedNotification);

      // Send email if configured
      if (deliveryMethods.includes('email') || deliveryMethods.includes('both')) {
        await this.sendEmailNotification(savedNotification);
      }

      return {
        success: true,
        data: savedNotification
      };
    } catch (error) {
      console.error('Error creating notification:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get notifications for a user with filtering
   */
  async getNotifications(userId, filter = {}) {
    try {
      const {
        types,
        status,
        priority,
        dateRange,
        searchQuery,
        limit = 50,
        offset = 0
      } = filter;

      // Build query
      const query = { userId };

      if (types && types.length > 0) {
        query.type = { $in: types };
      }

      if (status && status.length > 0) {
        query.status = { $in: status };
      }

      if (priority && priority.length > 0) {
        query.priority = { $in: priority };
      }

      if (dateRange && dateRange.start && dateRange.end) {
        query.createdAt = {
          $gte: new Date(dateRange.start),
          $lte: new Date(dateRange.end)
        };
      }

      if (searchQuery) {
        query.$or = [
          { title: { $regex: searchQuery, $options: 'i' } },
          { message: { $regex: searchQuery, $options: 'i' } },
          { content: { $regex: searchQuery, $options: 'i' } }
        ];
      }

      // Get notifications
      const notifications = await Notification.find(query)
        .sort({ createdAt: -1 })
        .limit(limit)
        .skip(offset)
        .lean();

      // Get total count
      const total = await Notification.countDocuments(query);

      // Get statistics
      const stats = await this.getNotificationStats(userId);

      return {
        success: true,
        data: {
          notifications,
          total,
          hasMore: offset + notifications.length < total,
          stats
        }
      };
    } catch (error) {
      console.error('Error getting notifications:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get notification history with advanced filtering
   */
  async getNotificationHistory(userId, filter = {}) {
    try {
      const {
        types,
        status,
        priority,
        dateRange,
        searchQuery,
        includeArchived = false,
        limit = 100,
        offset = 0,
        sortBy = 'createdAt',
        sortOrder = 'desc'
      } = filter;

      // Build query
      const query = { userId };

      if (!includeArchived) {
        query.status = { $ne: 'archived' };
      }

      if (types && types.length > 0) {
        query.type = { $in: types };
      }

      if (status && status.length > 0) {
        query.status = { $in: status };
      }

      if (priority && priority.length > 0) {
        query.priority = { $in: priority };
      }

      if (dateRange && dateRange.start && dateRange.end) {
        query.createdAt = {
          $gte: new Date(dateRange.start),
          $lte: new Date(dateRange.end)
        };
      }

      if (searchQuery) {
        query.$or = [
          { title: { $regex: searchQuery, $options: 'i' } },
          { message: { $regex: searchQuery, $options: 'i' } },
          { content: { $regex: searchQuery, $options: 'i' } }
        ];
      }

      // Build sort object
      const sort = {};
      sort[sortBy] = sortOrder === 'asc' ? 1 : -1;

      // Get notifications
      const notifications = await Notification.find(query)
        .sort(sort)
        .limit(limit)
        .skip(offset)
        .lean();

      // Get total count
      const total = await Notification.countDocuments(query);

      return {
        success: true,
        data: {
          notifications,
          total,
          hasMore: offset + notifications.length < total
        }
      };
    } catch (error) {
      console.error('Error getting notification history:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Mark notification as read
   */
  async markAsRead(notificationId) {
    try {
      const notification = await Notification.findById(notificationId);
      if (!notification) {
        throw new Error('Notification not found');
      }

      if (notification.status === 'unread') {
        notification.status = 'read';
        notification.readAt = new Date();
        notification.updatedAt = new Date();
        await notification.save();

        // Send real-time update
        await this.sendRealTimeUpdate(notification.userId, 'notification_updated', notification);

        // Update stats
        await this.updateNotificationStats(notification.userId);
      }

      return {
        success: true,
        data: notification
      };
    } catch (error) {
      console.error('Error marking notification as read:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Dismiss notification
   */
  async dismissNotification(notificationId) {
    try {
      const notification = await Notification.findById(notificationId);
      if (!notification) {
        throw new Error('Notification not found');
      }

      notification.status = 'dismissed';
      notification.dismissedAt = new Date();
      notification.updatedAt = new Date();
      await notification.save();

      // Send real-time update
      await this.sendRealTimeUpdate(notification.userId, 'notification_updated', notification);

      // Update stats
      await this.updateNotificationStats(notification.userId);

      return {
        success: true,
        data: notification
      };
    } catch (error) {
      console.error('Error dismissing notification:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Archive notification
   */
  async archiveNotification(notificationId) {
    try {
      const notification = await Notification.findById(notificationId);
      if (!notification) {
        throw new Error('Notification not found');
      }

      notification.status = 'archived';
      notification.archivedAt = new Date();
      notification.updatedAt = new Date();
      await notification.save();

      // Send real-time update
      await this.sendRealTimeUpdate(notification.userId, 'notification_updated', notification);

      return {
        success: true,
        data: notification
      };
    } catch (error) {
      console.error('Error archiving notification:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Delete notification
   */
  async deleteNotification(notificationId) {
    try {
      const notification = await Notification.findById(notificationId);
      if (!notification) {
        throw new Error('Notification not found');
      }

      await Notification.findByIdAndDelete(notificationId);

      // Send real-time update
      await this.sendRealTimeUpdate(notification.userId, 'notification_deleted', { id: notificationId });

      // Update stats
      await this.updateNotificationStats(notification.userId);

      return {
        success: true,
        data: { id: notificationId }
      };
    } catch (error) {
      console.error('Error deleting notification:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Mark all notifications as read for a user
   */
  async markAllAsRead(userId) {
    try {
      const result = await Notification.updateMany(
        { userId, status: 'unread' },
        { 
          status: 'read', 
          readAt: new Date(),
          updatedAt: new Date()
        }
      );

      // Send real-time update
      await this.sendRealTimeUpdate(userId, 'stats_updated', await this.getNotificationStats(userId));

      return {
        success: true,
        data: { modifiedCount: result.modifiedCount }
      };
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get user notification preferences
   */
  async getPreferences(userId) {
    try {
      let preferences = await UserPreferences.findByUserId(userId);
      
      if (!preferences) {
        // Create default preferences
        preferences = await UserPreferences.createDefaultPreferences(userId);
      }

      return {
        success: true,
        data: preferences.notificationPreferences
      };
    } catch (error) {
      console.error('Error getting preferences:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Update user notification preferences
   */
  async updatePreferences(userId, preferences) {
    try {
      // Validate preferences
      const validation = UserPreferences.validatePreferences({ notificationPreferences: preferences });
      if (!validation.isValid) {
        throw new Error(`Invalid preferences: ${validation.errors.join(', ')}`);
      }

      let userPreferences = await UserPreferences.findByUserId(userId);
      
      if (!userPreferences) {
        userPreferences = await UserPreferences.createDefaultPreferences(userId);
      }

      // Update notification preferences
      userPreferences.notificationPreferences = {
        ...userPreferences.notificationPreferences,
        ...preferences
      };

      await userPreferences.save();

      return {
        success: true,
        data: userPreferences.notificationPreferences
      };
    } catch (error) {
      console.error('Error updating preferences:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get notification statistics for a user
   */
  async getNotificationStats(userId) {
    try {
      const stats = await Notification.aggregate([
        { $match: { userId } },
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            unread: {
              $sum: { $cond: [{ $eq: ['$status', 'unread'] }, 1, 0] }
            },
            byType: {
              $push: {
                type: '$type',
                status: '$status'
              }
            },
            byPriority: {
              $push: {
                priority: '$priority',
                status: '$status'
              }
            },
            byStatus: {
              $push: '$status'
            }
          }
        }
      ]);

      if (stats.length === 0) {
        return {
          total: 0,
          unread: 0,
          byType: {},
          byPriority: {},
          byStatus: {}
        };
      }

      const stat = stats[0];
      
      // Process byType
      const byType = {};
      stat.byType.forEach(item => {
        if (!byType[item.type]) {
          byType[item.type] = 0;
        }
        if (item.status === 'unread') {
          byType[item.type]++;
        }
      });

      // Process byPriority
      const byPriority = {};
      stat.byPriority.forEach(item => {
        if (!byPriority[item.priority]) {
          byPriority[item.priority] = 0;
        }
        if (item.status === 'unread') {
          byPriority[item.priority]++;
        }
      });

      // Process byStatus
      const byStatus = {};
      stat.byStatus.forEach(status => {
        byStatus[status] = (byStatus[status] || 0) + 1;
      });

      return {
        total: stat.total,
        unread: stat.unread,
        byType,
        byPriority,
        byStatus
      };
    } catch (error) {
      console.error('Error getting notification stats:', error);
      return {
        total: 0,
        unread: 0,
        byType: {},
        byPriority: {},
        byStatus: {}
      };
    }
  }

  /**
   * Update notification statistics and send real-time update
   */
  async updateNotificationStats(userId) {
    try {
      const stats = await this.getNotificationStats(userId);
      await this.sendRealTimeUpdate(userId, 'stats_updated', stats);
    } catch (error) {
      console.error('Error updating notification stats:', error);
    }
  }

  /**
   * Send test notification
   */
  async sendTestNotification(userId, type) {
    try {
      const testNotification = {
        userId,
        type,
        title: `Test ${type.replace('_', ' ')} Notification`,
        message: 'This is a test notification to verify your notification settings.',
        content: 'Test notification content for verification purposes.',
        priority: 'medium',
        metadata: {
          test: true,
          timestamp: new Date().toISOString()
        },
        actions: [
          {
            id: 'test_action',
            label: 'Test Action',
            type: 'custom',
            handler: () => console.log('Test action executed')
          }
        ]
      };

      return await this.createNotification(testNotification);
    } catch (error) {
      console.error('Error sending test notification:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Export notification history
   */
  async exportHistory(userId, format = 'csv', filter = {}) {
    try {
      const response = await this.getNotificationHistory(userId, { ...filter, limit: 10000 });
      
      if (!response.success) {
        throw new Error(response.error);
      }

      const notifications = response.data.notifications;
      
      if (format === 'csv') {
        return this.exportToCSV(notifications);
      } else if (format === 'json') {
        return this.exportToJSON(notifications);
      } else {
        throw new Error('Unsupported export format');
      }
    } catch (error) {
      console.error('Error exporting notification history:', error);
      throw error;
    }
  }

  /**
   * Export notifications to CSV format
   */
  exportToCSV(notifications) {
    const headers = [
      'ID', 'Type', 'Title', 'Message', 'Priority', 'Status', 
      'Created At', 'Read At', 'Dismissed At', 'Archived At'
    ];
    
    const rows = notifications.map(notification => [
      notification._id,
      notification.type,
      notification.title,
      notification.message,
      notification.priority,
      notification.status,
      notification.createdAt,
      notification.readAt || '',
      notification.dismissedAt || '',
      notification.archivedAt || ''
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(','))
      .join('\n');

    return Buffer.from(csvContent, 'utf8');
  }

  /**
   * Export notifications to JSON format
   */
  exportToJSON(notifications) {
    return Buffer.from(JSON.stringify(notifications, null, 2), 'utf8');
  }

  /**
   * Setup WebSocket server for real-time updates
   */
  setupWebSocketServer() {
    // This would typically be integrated with your existing WebSocket server
    // For now, we'll store connections in memory
    console.log('Notification service WebSocket server setup');
  }

  /**
   * Send real-time update to connected clients
   */
  async sendRealTimeUpdate(userId, type, data) {
    try {
      const message = {
        type,
        data,
        timestamp: new Date().toISOString()
      };

      // Send to WebSocket connections
      const connections = this.websocketConnections.get(userId);
      if (connections) {
        connections.forEach(ws => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
          }
        });
      }

      // Also send to any global notification channels
      // This could be integrated with Redis pub/sub or other messaging systems
    } catch (error) {
      console.error('Error sending real-time update:', error);
    }
  }

  /**
   * Add WebSocket connection for a user
   */
  addWebSocketConnection(userId, ws) {
    if (!this.websocketConnections.has(userId)) {
      this.websocketConnections.set(userId, new Set());
    }
    this.websocketConnections.get(userId).add(ws);

    // Handle connection close
    ws.on('close', () => {
      this.removeWebSocketConnection(userId, ws);
    });
  }

  /**
   * Remove WebSocket connection for a user
   */
  removeWebSocketConnection(userId, ws) {
    const connections = this.websocketConnections.get(userId);
    if (connections) {
      connections.delete(ws);
      if (connections.size === 0) {
        this.websocketConnections.delete(userId);
      }
    }
  }

  /**
   * Send email notification
   */
  async sendEmailNotification(notification) {
    try {
      // This would integrate with your existing email service
      // For now, we'll just log the notification
      console.log('Email notification would be sent:', {
        to: notification.userId, // This would be the user's email
        subject: notification.title,
        body: notification.message,
        type: notification.type,
        priority: notification.priority
      });

      // Example integration with email service:
      // await emailService.send({
      //   to: user.email,
      //   subject: notification.title,
      //   template: 'notification',
      //   data: {
      //     notification,
      //     user
      //   }
      // });
    } catch (error) {
      console.error('Error sending email notification:', error);
    }
  }

  /**
   * Clean up expired notifications
   */
  async cleanupExpiredNotifications() {
    try {
      const result = await Notification.updateMany(
        { 
          expiresAt: { $lt: new Date() },
          status: { $ne: 'archived' }
        },
        { 
          status: 'archived',
          archivedAt: new Date(),
          updatedAt: new Date()
        }
      );

      console.log(`Cleaned up ${result.modifiedCount} expired notifications`);
      return result.modifiedCount;
    } catch (error) {
      console.error('Error cleaning up expired notifications:', error);
      return 0;
    }
  }

  /**
   * Get notification analytics
   */
  async getNotificationAnalytics(userId, dateRange) {
    try {
      const { start, end } = dateRange;
      
      const analytics = await Notification.aggregate([
        {
          $match: {
            userId,
            createdAt: {
              $gte: new Date(start),
              $lte: new Date(end)
            }
          }
        },
        {
          $group: {
            _id: {
              type: '$type',
              date: {
                $dateToString: {
                  format: '%Y-%m-%d',
                  date: '$createdAt'
                }
              }
            },
            count: { $sum: 1 },
            unreadCount: {
              $sum: { $cond: [{ $eq: ['$status', 'unread'] }, 1, 0] }
            }
          }
        },
        {
          $sort: { '_id.date': 1 }
        }
      ]);

      return {
        success: true,
        data: analytics
      };
    } catch (error) {
      console.error('Error getting notification analytics:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

// Export singleton instance
module.exports = new NotificationService();
