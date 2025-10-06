/**
 * Database Migration: Add Notifications Table
 * Creates the notifications table with all necessary columns and indexes
 */

const mongoose = require('mongoose');

async function up() {
  try {
    console.log('Creating notifications collection...');

    // Create notifications collection with schema validation
    await mongoose.connection.db.createCollection('notifications', {
      validator: {
        $jsonSchema: {
          bsonType: 'object',
          required: ['userId', 'type', 'title', 'message', 'priority', 'status', 'createdAt', 'updatedAt'],
          properties: {
            userId: {
              bsonType: 'string',
              description: 'User ID who owns this notification'
            },
            type: {
              bsonType: 'string',
              enum: ['analysis_completion', 'system_alert', 'compliance_update', 'security_alert', 'maintenance_notice', 'feature_update'],
              description: 'Type of notification'
            },
            title: {
              bsonType: 'string',
              minLength: 1,
              maxLength: 200,
              description: 'Notification title'
            },
            message: {
              bsonType: 'string',
              minLength: 1,
              maxLength: 1000,
              description: 'Notification message'
            },
            content: {
              bsonType: 'string',
              maxLength: 5000,
              description: 'Additional notification content'
            },
            priority: {
              bsonType: 'string',
              enum: ['low', 'medium', 'high', 'critical'],
              description: 'Notification priority level'
            },
            status: {
              bsonType: 'string',
              enum: ['unread', 'read', 'dismissed', 'archived'],
              description: 'Notification status'
            },
            timestamp: {
              bsonType: 'date',
              description: 'When the notification was created'
            },
            readAt: {
              bsonType: 'date',
              description: 'When the notification was read'
            },
            dismissedAt: {
              bsonType: 'date',
              description: 'When the notification was dismissed'
            },
            archivedAt: {
              bsonType: 'date',
              description: 'When the notification was archived'
            },
            actions: {
              bsonType: 'array',
              items: {
                bsonType: 'object',
                required: ['id', 'label', 'type'],
                properties: {
                  id: {
                    bsonType: 'string',
                    description: 'Unique action identifier'
                  },
                  label: {
                    bsonType: 'string',
                    description: 'Action label'
                  },
                  type: {
                    bsonType: 'string',
                    enum: ['navigate', 'dismiss', 'mark_read', 'custom'],
                    description: 'Action type'
                  },
                  url: {
                    bsonType: 'string',
                    description: 'URL for navigate actions'
                  },
                  handler: {
                    bsonType: 'string',
                    description: 'Handler function name for custom actions'
                  }
                }
              },
              description: 'Available actions for this notification'
            },
            metadata: {
              bsonType: 'object',
              description: 'Additional metadata for the notification'
            },
            deliveryMethods: {
              bsonType: 'array',
              items: {
                bsonType: 'string',
                enum: ['in_app', 'email', 'both']
              },
              description: 'Delivery methods for this notification'
            },
            expiresAt: {
              bsonType: 'date',
              description: 'When the notification expires'
            },
            createdAt: {
              bsonType: 'date',
              description: 'When the notification was created'
            },
            updatedAt: {
              bsonType: 'date',
              description: 'When the notification was last updated'
            }
          }
        }
      }
    });

    // Create indexes for better performance
    console.log('Creating indexes...');

    // Index on userId for user-specific queries
    await mongoose.connection.db.collection('notifications').createIndex(
      { userId: 1 },
      { name: 'idx_userId' }
    );

    // Index on userId and status for unread notifications
    await mongoose.connection.db.collection('notifications').createIndex(
      { userId: 1, status: 1 },
      { name: 'idx_userId_status' }
    );

    // Index on userId and type for type-specific queries
    await mongoose.connection.db.collection('notifications').createIndex(
      { userId: 1, type: 1 },
      { name: 'idx_userId_type' }
    );

    // Index on userId and priority for priority-based queries
    await mongoose.connection.db.collection('notifications').createIndex(
      { userId: 1, priority: 1 },
      { name: 'idx_userId_priority' }
    );

    // Index on createdAt for time-based queries
    await mongoose.connection.db.collection('notifications').createIndex(
      { createdAt: -1 },
      { name: 'idx_createdAt_desc' }
    );

    // Compound index for efficient filtering and sorting
    await mongoose.connection.db.collection('notifications').createIndex(
      { userId: 1, status: 1, createdAt: -1 },
      { name: 'idx_userId_status_createdAt' }
    );

    // Index on expiresAt for cleanup operations
    await mongoose.connection.db.collection('notifications').createIndex(
      { expiresAt: 1 },
      { name: 'idx_expiresAt' }
    );

    // Text index for search functionality
    await mongoose.connection.db.collection('notifications').createIndex(
      { title: 'text', message: 'text', content: 'text' },
      { name: 'idx_text_search' }
    );

    console.log('Notifications collection created successfully with indexes');
  } catch (error) {
    console.error('Error creating notifications collection:', error);
    throw error;
  }
}

async function down() {
  try {
    console.log('Dropping notifications collection...');
    await mongoose.connection.db.collection('notifications').drop();
    console.log('Notifications collection dropped successfully');
  } catch (error) {
    console.error('Error dropping notifications collection:', error);
    throw error;
  }
}

module.exports = { up, down };
