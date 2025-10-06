/**
 * WebSocket Configuration for Real-Time Notifications
 * Handles WebSocket connections and real-time notification delivery
 */

const WebSocket = require('ws');
const notificationService = require('../services/notificationService');
const { authenticateWebSocket } = require('../middleware/auth');

class NotificationWebSocketServer {
  constructor(server) {
    this.wss = new WebSocket.Server({ 
      server,
      path: '/ws/notifications',
      verifyClient: this.verifyClient.bind(this)
    });
    
    this.connections = new Map(); // userId -> Set of WebSocket connections
    this.setupEventHandlers();
    
    console.log('Notification WebSocket server started on /ws/notifications');
  }

  /**
   * Verify client connection and authenticate user
   */
  async verifyClient(info) {
    try {
      const url = new URL(info.req.url, `http://${info.req.headers.host}`);
      const token = url.searchParams.get('token') || info.req.headers.authorization?.replace('Bearer ', '');
      
      if (!token) {
        console.log('WebSocket connection rejected: No token provided');
        return false;
      }

      // Authenticate the token
      const user = await authenticateWebSocket(token);
      if (!user) {
        console.log('WebSocket connection rejected: Invalid token');
        return false;
      }

      // Store user info for later use
      info.req.user = user;
      return true;
    } catch (error) {
      console.error('WebSocket verification error:', error);
      return false;
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  setupEventHandlers() {
    this.wss.on('connection', (ws, req) => {
      const user = req.user;
      const userId = user.id || user._id;

      console.log(`WebSocket connected for user: ${userId}`);

      // Add connection to user's connection set
      if (!this.connections.has(userId)) {
        this.connections.set(userId, new Set());
      }
      this.connections.get(userId).add(ws);

      // Register with notification service
      notificationService.addWebSocketConnection(userId, ws);

      // Send initial connection confirmation
      this.sendToConnection(ws, {
        type: 'connection_established',
        data: {
          userId,
          timestamp: new Date().toISOString(),
          message: 'WebSocket connection established'
        }
      });

      // Handle incoming messages
      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this.handleMessage(ws, userId, message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          this.sendError(ws, 'Invalid message format');
        }
      });

      // Handle connection close
      ws.on('close', (code, reason) => {
        console.log(`WebSocket disconnected for user: ${userId}, code: ${code}, reason: ${reason}`);
        this.removeConnection(userId, ws);
      });

      // Handle connection errors
      ws.on('error', (error) => {
        console.error(`WebSocket error for user: ${userId}:`, error);
        this.removeConnection(userId, ws);
      });

      // Send ping to keep connection alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.ping();
        } else {
          clearInterval(pingInterval);
        }
      }, 30000); // Ping every 30 seconds

      // Store ping interval for cleanup
      ws.pingInterval = pingInterval;
    });

    // Handle server errors
    this.wss.on('error', (error) => {
      console.error('WebSocket server error:', error);
    });
  }

  /**
   * Handle incoming WebSocket messages
   */
  async handleMessage(ws, userId, message) {
    try {
      switch (message.type) {
        case 'ping':
          this.sendToConnection(ws, { type: 'pong', timestamp: new Date().toISOString() });
          break;

        case 'subscribe':
          // Subscribe to specific notification types
          await this.handleSubscription(ws, userId, message.data);
          break;

        case 'unsubscribe':
          // Unsubscribe from specific notification types
          await this.handleUnsubscription(ws, userId, message.data);
          break;

        case 'mark_as_read':
          // Mark notification as read
          await this.handleMarkAsRead(userId, message.data);
          break;

        case 'dismiss':
          // Dismiss notification
          await this.handleDismiss(userId, message.data);
          break;

        case 'get_stats':
          // Get current notification stats
          await this.handleGetStats(ws, userId);
          break;

        default:
          this.sendError(ws, `Unknown message type: ${message.type}`);
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
      this.sendError(ws, 'Error processing message');
    }
  }

  /**
   * Handle subscription to notification types
   */
  async handleSubscription(ws, userId, data) {
    try {
      const { types } = data;
      
      // Store subscription preferences for this connection
      ws.subscribedTypes = types || ['all'];
      
      this.sendToConnection(ws, {
        type: 'subscription_confirmed',
        data: {
          types: ws.subscribedTypes,
          timestamp: new Date().toISOString()
        }
      });
    } catch (error) {
      console.error('Error handling subscription:', error);
      this.sendError(ws, 'Error processing subscription');
    }
  }

  /**
   * Handle unsubscription from notification types
   */
  async handleUnsubscription(ws, userId, data) {
    try {
      const { types } = data;
      
      if (types) {
        ws.subscribedTypes = ws.subscribedTypes?.filter(type => !types.includes(type)) || [];
      } else {
        ws.subscribedTypes = [];
      }
      
      this.sendToConnection(ws, {
        type: 'unsubscription_confirmed',
        data: {
          types: ws.subscribedTypes,
          timestamp: new Date().toISOString()
        }
      });
    } catch (error) {
      console.error('Error handling unsubscription:', error);
      this.sendError(ws, 'Error processing unsubscription');
    }
  }

  /**
   * Handle mark as read request
   */
  async handleMarkAsRead(userId, data) {
    try {
      const { notificationId } = data;
      
      if (!notificationId) {
        throw new Error('Notification ID is required');
      }

      const result = await notificationService.markAsRead(notificationId);
      
      if (result.success) {
        // Broadcast update to all user's connections
        this.broadcastToUser(userId, {
          type: 'notification_updated',
          data: result.data,
          timestamp: new Date().toISOString()
        });
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Error handling mark as read:', error);
      // Could send error back to specific connection if needed
    }
  }

  /**
   * Handle dismiss request
   */
  async handleDismiss(userId, data) {
    try {
      const { notificationId } = data;
      
      if (!notificationId) {
        throw new Error('Notification ID is required');
      }

      const result = await notificationService.dismissNotification(notificationId);
      
      if (result.success) {
        // Broadcast update to all user's connections
        this.broadcastToUser(userId, {
          type: 'notification_updated',
          data: result.data,
          timestamp: new Date().toISOString()
        });
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('Error handling dismiss:', error);
      // Could send error back to specific connection if needed
    }
  }

  /**
   * Handle get stats request
   */
  async handleGetStats(ws, userId) {
    try {
      const stats = await notificationService.getNotificationStats(userId);
      
      this.sendToConnection(ws, {
        type: 'stats_response',
        data: stats,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error handling get stats:', error);
      this.sendError(ws, 'Error fetching stats');
    }
  }

  /**
   * Send message to a specific WebSocket connection
   */
  sendToConnection(ws, message) {
    if (ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(message));
      } catch (error) {
        console.error('Error sending message to WebSocket:', error);
      }
    }
  }

  /**
   * Send error message to a specific WebSocket connection
   */
  sendError(ws, errorMessage) {
    this.sendToConnection(ws, {
      type: 'error',
      data: {
        message: errorMessage,
        timestamp: new Date().toISOString()
      }
    });
  }

  /**
   * Broadcast message to all connections for a specific user
   */
  broadcastToUser(userId, message) {
    const userConnections = this.connections.get(userId);
    if (userConnections) {
      userConnections.forEach(ws => {
        this.sendToConnection(ws, message);
      });
    }
  }

  /**
   * Broadcast message to all connected users
   */
  broadcastToAll(message) {
    this.connections.forEach((connections, userId) => {
      connections.forEach(ws => {
        this.sendToConnection(ws, message);
      });
    });
  }

  /**
   * Send notification to specific user
   */
  async sendNotificationToUser(userId, notification) {
    const message = {
      type: 'notification_created',
      data: notification,
      timestamp: new Date().toISOString()
    };

    this.broadcastToUser(userId, message);
  }

  /**
   * Send notification update to specific user
   */
  async sendNotificationUpdateToUser(userId, notification) {
    const message = {
      type: 'notification_updated',
      data: notification,
      timestamp: new Date().toISOString()
    };

    this.broadcastToUser(userId, message);
  }

  /**
   * Send notification deletion to specific user
   */
  async sendNotificationDeletionToUser(userId, notificationId) {
    const message = {
      type: 'notification_deleted',
      data: { id: notificationId },
      timestamp: new Date().toISOString()
    };

    this.broadcastToUser(userId, message);
  }

  /**
   * Send stats update to specific user
   */
  async sendStatsUpdateToUser(userId, stats) {
    const message = {
      type: 'stats_updated',
      data: stats,
      timestamp: new Date().toISOString()
    };

    this.broadcastToUser(userId, message);
  }

  /**
   * Remove connection from user's connection set
   */
  removeConnection(userId, ws) {
    const userConnections = this.connections.get(userId);
    if (userConnections) {
      userConnections.delete(ws);
      
      // Clean up ping interval
      if (ws.pingInterval) {
        clearInterval(ws.pingInterval);
      }
      
      // Remove user's connection set if empty
      if (userConnections.size === 0) {
        this.connections.delete(userId);
      }
    }

    // Remove from notification service
    notificationService.removeWebSocketConnection(userId, ws);
  }

  /**
   * Get connection statistics
   */
  getConnectionStats() {
    const stats = {
      totalConnections: 0,
      uniqueUsers: this.connections.size,
      connectionsByUser: {}
    };

    this.connections.forEach((connections, userId) => {
      stats.totalConnections += connections.size;
      stats.connectionsByUser[userId] = connections.size;
    });

    return stats;
  }

  /**
   * Close all connections gracefully
   */
  async closeAllConnections() {
    console.log('Closing all WebSocket connections...');
    
    this.connections.forEach((connections, userId) => {
      connections.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close(1000, 'Server shutting down');
        }
      });
    });

    this.connections.clear();
  }

  /**
   * Shutdown WebSocket server
   */
  async shutdown() {
    console.log('Shutting down WebSocket server...');
    
    await this.closeAllConnections();
    
    return new Promise((resolve) => {
      this.wss.close(() => {
        console.log('WebSocket server closed');
        resolve();
      });
    });
  }
}

// WebSocket message types and utilities
const WebSocketMessageTypes = {
  // Connection management
  CONNECTION_ESTABLISHED: 'connection_established',
  PING: 'ping',
  PONG: 'pong',
  
  // Notifications
  NOTIFICATION_CREATED: 'notification_created',
  NOTIFICATION_UPDATED: 'notification_updated',
  NOTIFICATION_DELETED: 'notification_deleted',
  
  // Stats
  STATS_UPDATED: 'stats_updated',
  STATS_RESPONSE: 'stats_response',
  
  // Subscriptions
  SUBSCRIBE: 'subscribe',
  UNSUBSCRIBE: 'unsubscribe',
  SUBSCRIPTION_CONFIRMED: 'subscription_confirmed',
  UNSUBSCRIPTION_CONFIRMED: 'unsubscription_confirmed',
  
  // Actions
  MARK_AS_READ: 'mark_as_read',
  DISMISS: 'dismiss',
  GET_STATS: 'get_stats',
  
  // Errors
  ERROR: 'error'
};

// Utility functions for WebSocket message handling
const WebSocketUtils = {
  /**
   * Create a standardized WebSocket message
   */
  createMessage(type, data, timestamp = null) {
    return {
      type,
      data,
      timestamp: timestamp || new Date().toISOString()
    };
  },

  /**
   * Create an error message
   */
  createErrorMessage(message, code = null) {
    return {
      type: WebSocketMessageTypes.ERROR,
      data: {
        message,
        code,
        timestamp: new Date().toISOString()
      }
    };
  },

  /**
   * Validate WebSocket message format
   */
  validateMessage(message) {
    if (!message || typeof message !== 'object') {
      return { valid: false, error: 'Message must be an object' };
    }

    if (!message.type || typeof message.type !== 'string') {
      return { valid: false, error: 'Message must have a valid type' };
    }

    if (!Object.values(WebSocketMessageTypes).includes(message.type)) {
      return { valid: false, error: 'Invalid message type' };
    }

    return { valid: true };
  }
};

module.exports = {
  NotificationWebSocketServer,
  WebSocketMessageTypes,
  WebSocketUtils
};
