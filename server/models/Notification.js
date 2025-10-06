/**
 * Notification Model
 * Mongoose model for notification data
 */

const mongoose = require('mongoose');
const Schema = mongoose.Schema;

// Notification Action Schema
const NotificationActionSchema = new Schema({
  id: {
    type: String,
    required: true
  },
  label: {
    type: String,
    required: true
  },
  type: {
    type: String,
    enum: ['navigate', 'dismiss', 'mark_read', 'custom'],
    required: true
  },
  url: {
    type: String,
    default: null
  },
  handler: {
    type: String, // Store function name or identifier
    default: null
  },
  icon: {
    type: String,
    default: null
  }
}, { _id: false });

// Notification Schema
const NotificationSchema = new Schema({
  userId: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  type: {
    type: String,
    enum: [
      'analysis_completion',
      'system_alert',
      'compliance_update',
      'security_alert',
      'maintenance_notice',
      'feature_update'
    ],
    required: true,
    index: true
  },
  title: {
    type: String,
    required: true,
    maxlength: 200
  },
  message: {
    type: String,
    required: true,
    maxlength: 1000
  },
  content: {
    type: String,
    maxlength: 5000,
    default: null
  },
  priority: {
    type: String,
    enum: ['low', 'medium', 'high', 'critical'],
    default: 'medium',
    index: true
  },
  status: {
    type: String,
    enum: ['unread', 'read', 'dismissed', 'archived'],
    default: 'unread',
    index: true
  },
  timestamp: {
    type: Date,
    default: Date.now,
    index: true
  },
  readAt: {
    type: Date,
    default: null
  },
  dismissedAt: {
    type: Date,
    default: null
  },
  archivedAt: {
    type: Date,
    default: null
  },
  archivedBy: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    default: null
  },
  actions: {
    type: [NotificationActionSchema],
    default: []
  },
  metadata: {
    type: Schema.Types.Mixed,
    default: {}
  },
  deliveryMethods: {
    type: [String],
    enum: ['in_app', 'email', 'both'],
    default: ['in_app']
  },
  expiresAt: {
    type: Date,
    default: null,
    index: { expireAfterSeconds: 0 } // TTL index
  },
  // System fields
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  },
  // Email delivery tracking
  emailSent: {
    type: Boolean,
    default: false
  },
  emailSentAt: {
    type: Date,
    default: null
  },
  emailDeliveryStatus: {
    type: String,
    enum: ['pending', 'sent', 'delivered', 'failed', 'bounced'],
    default: 'pending'
  },
  // Real-time delivery tracking
  realTimeDelivered: {
    type: Boolean,
    default: false
  },
  realTimeDeliveredAt: {
    type: Date,
    default: null
  },
  // Source tracking
  source: {
    type: String,
    enum: ['system', 'user', 'api', 'webhook', 'scheduled'],
    default: 'system'
  },
  sourceId: {
    type: String,
    default: null
  },
  // Analytics
  clickCount: {
    type: Number,
    default: 0
  },
  lastClickedAt: {
    type: Date,
    default: null
  },
  // Tags for categorization
  tags: {
    type: [String],
    default: []
  },
  // Related entities
  relatedAnalysisId: {
    type: Schema.Types.ObjectId,
    ref: 'Analysis',
    default: null
  },
  relatedUserId: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    default: null
  },
  relatedSystemComponent: {
    type: String,
    default: null
  }
}, {
  timestamps: true,
  collection: 'notifications'
});

// Indexes for performance
NotificationSchema.index({ userId: 1, status: 1, timestamp: -1 });
NotificationSchema.index({ userId: 1, type: 1, timestamp: -1 });
NotificationSchema.index({ userId: 1, priority: 1, timestamp: -1 });
NotificationSchema.index({ status: 1, timestamp: -1 });
NotificationSchema.index({ type: 1, timestamp: -1 });
NotificationSchema.index({ priority: 1, timestamp: -1 });
NotificationSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
NotificationSchema.index({ createdAt: 1 });
NotificationSchema.index({ updatedAt: 1 });

// Virtual for notification age
NotificationSchema.virtual('age').get(function() {
  return Date.now() - this.timestamp.getTime();
});

// Virtual for is expired
NotificationSchema.virtual('isExpired').get(function() {
  return this.expiresAt && this.expiresAt < new Date();
});

// Virtual for is unread
NotificationSchema.virtual('isUnread').get(function() {
  return this.status === 'unread';
});

// Pre-save middleware
NotificationSchema.pre('save', function(next) {
  this.updatedAt = new Date();
  
  // Set readAt when status changes to read
  if (this.isModified('status') && this.status === 'read' && !this.readAt) {
    this.readAt = new Date();
  }
  
  // Set dismissedAt when status changes to dismissed
  if (this.isModified('status') && this.status === 'dismissed' && !this.dismissedAt) {
    this.dismissedAt = new Date();
  }
  
  // Set archivedAt when status changes to archived
  if (this.isModified('status') && this.status === 'archived' && !this.archivedAt) {
    this.archivedAt = new Date();
  }
  
  next();
});

// Instance methods
NotificationSchema.methods.markAsRead = function() {
  this.status = 'read';
  this.readAt = new Date();
  return this.save();
};

NotificationSchema.methods.dismiss = function() {
  this.status = 'dismissed';
  this.dismissedAt = new Date();
  return this.save();
};

NotificationSchema.methods.archive = function(userId) {
  this.status = 'archived';
  this.archivedAt = new Date();
  this.archivedBy = userId;
  return this.save();
};

NotificationSchema.methods.incrementClickCount = function() {
  this.clickCount += 1;
  this.lastClickedAt = new Date();
  return this.save();
};

NotificationSchema.methods.isAccessibleBy = function(userId) {
  return this.userId.toString() === userId.toString();
};

// Static methods
NotificationSchema.statics.findByUser = function(userId, options = {}) {
  const query = { userId };
  
  if (options.status) {
    query.status = options.status;
  }
  
  if (options.type) {
    query.type = options.type;
  }
  
  if (options.priority) {
    query.priority = options.priority;
  }
  
  if (options.unreadOnly) {
    query.status = 'unread';
  }
  
  return this.find(query)
    .sort({ timestamp: -1 })
    .limit(options.limit || 50)
    .skip(options.skip || 0);
};

NotificationSchema.statics.getUnreadCount = function(userId) {
  return this.countDocuments({ userId, status: 'unread' });
};

NotificationSchema.statics.getStats = function(userId) {
  return this.aggregate([
    { $match: { userId: mongoose.Types.ObjectId(userId) } },
    {
      $group: {
        _id: null,
        total: { $sum: 1 },
        unread: { $sum: { $cond: [{ $eq: ['$status', 'unread'] }, 1, 0] } },
        read: { $sum: { $cond: [{ $eq: ['$status', 'read'] }, 1, 0] } },
        dismissed: { $sum: { $cond: [{ $eq: ['$status', 'dismissed'] }, 1, 0] } },
        archived: { $sum: { $cond: [{ $eq: ['$status', 'archived'] }, 1, 0] } },
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
        }
      }
    }
  ]);
};

NotificationSchema.statics.markAllAsRead = function(userId) {
  return this.updateMany(
    { userId, status: 'unread' },
    { 
      $set: { 
        status: 'read', 
        readAt: new Date() 
      } 
    }
  );
};

NotificationSchema.statics.deleteExpired = function() {
  return this.deleteMany({
    expiresAt: { $lt: new Date() }
  });
};

NotificationSchema.statics.cleanupOldNotifications = function(daysOld = 90) {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - daysOld);
  
  return this.deleteMany({
    createdAt: { $lt: cutoffDate },
    status: { $in: ['dismissed', 'archived'] }
  });
};

// Export the model
const Notification = mongoose.model('Notification', NotificationSchema);

module.exports = Notification;
