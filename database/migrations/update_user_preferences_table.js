/**
 * Database Migration: Update User Preferences Table for Notifications
 * Adds notification preferences fields to the user_preferences table
 */

const mongoose = require('mongoose');

async function up() {
  try {
    console.log('Updating user_preferences collection for notification settings...');

    // Add notification preferences to existing user preferences
    await mongoose.connection.db.collection('user_preferences').updateMany(
      { notificationPreferences: { $exists: false } },
      {
        $set: {
          notificationPreferences: {
            analysisCompletion: {
              enabled: true,
              deliveryMethod: 'in_app',
              priority: 'medium'
            },
            systemAlerts: {
              enabled: true,
              deliveryMethod: 'both',
              priority: 'high'
            },
            complianceUpdates: {
              enabled: true,
              deliveryMethod: 'email',
              priority: 'medium'
            },
            securityAlerts: {
              enabled: true,
              deliveryMethod: 'both',
              priority: 'critical'
            },
            maintenanceNotices: {
              enabled: true,
              deliveryMethod: 'in_app',
              priority: 'low'
            },
            featureUpdates: {
              enabled: false,
              deliveryMethod: 'email',
              priority: 'low'
            },
            globalSettings: {
              soundEnabled: true,
              desktopNotifications: false,
              emailDigest: false,
              digestFrequency: 'daily'
            }
          }
        }
      }
    );

    // Update the collection validator to include notification preferences
    await mongoose.connection.db.command({
      collMod: 'user_preferences',
      validator: {
        $jsonSchema: {
          bsonType: 'object',
          required: ['userId'],
          properties: {
            userId: {
              bsonType: 'string',
              description: 'User ID'
            },
            role: {
              bsonType: 'string',
              enum: ['admin', 'analyst', 'viewer', 'security_officer', 'compliance_manager', 'system_admin'],
              description: 'User role'
            },
            notificationPreferences: {
              bsonType: 'object',
              properties: {
                analysisCompletion: {
                  bsonType: 'object',
                  required: ['enabled', 'deliveryMethod', 'priority'],
                  properties: {
                    enabled: {
                      bsonType: 'bool',
                      description: 'Whether analysis completion notifications are enabled'
                    },
                    deliveryMethod: {
                      bsonType: 'string',
                      enum: ['in_app', 'email', 'both'],
                      description: 'Delivery method for analysis completion notifications'
                    },
                    priority: {
                      bsonType: 'string',
                      enum: ['low', 'medium', 'high', 'critical'],
                      description: 'Priority level for analysis completion notifications'
                    }
                  }
                },
                systemAlerts: {
                  bsonType: 'object',
                  required: ['enabled', 'deliveryMethod', 'priority'],
                  properties: {
                    enabled: {
                      bsonType: 'bool',
                      description: 'Whether system alert notifications are enabled'
                    },
                    deliveryMethod: {
                      bsonType: 'string',
                      enum: ['in_app', 'email', 'both'],
                      description: 'Delivery method for system alert notifications'
                    },
                    priority: {
                      bsonType: 'string',
                      enum: ['low', 'medium', 'high', 'critical'],
                      description: 'Priority level for system alert notifications'
                    }
                  }
                },
                complianceUpdates: {
                  bsonType: 'object',
                  required: ['enabled', 'deliveryMethod', 'priority'],
                  properties: {
                    enabled: {
                      bsonType: 'bool',
                      description: 'Whether compliance update notifications are enabled'
                    },
                    deliveryMethod: {
                      bsonType: 'string',
                      enum: ['in_app', 'email', 'both'],
                      description: 'Delivery method for compliance update notifications'
                    },
                    priority: {
                      bsonType: 'string',
                      enum: ['low', 'medium', 'high', 'critical'],
                      description: 'Priority level for compliance update notifications'
                    }
                  }
                },
                securityAlerts: {
                  bsonType: 'object',
                  required: ['enabled', 'deliveryMethod', 'priority'],
                  properties: {
                    enabled: {
                      bsonType: 'bool',
                      description: 'Whether security alert notifications are enabled'
                    },
                    deliveryMethod: {
                      bsonType: 'string',
                      enum: ['in_app', 'email', 'both'],
                      description: 'Delivery method for security alert notifications'
                    },
                    priority: {
                      bsonType: 'string',
                      enum: ['low', 'medium', 'high', 'critical'],
                      description: 'Priority level for security alert notifications'
                    }
                  }
                },
                maintenanceNotices: {
                  bsonType: 'object',
                  required: ['enabled', 'deliveryMethod', 'priority'],
                  properties: {
                    enabled: {
                      bsonType: 'bool',
                      description: 'Whether maintenance notice notifications are enabled'
                    },
                    deliveryMethod: {
                      bsonType: 'string',
                      enum: ['in_app', 'email', 'both'],
                      description: 'Delivery method for maintenance notice notifications'
                    },
                    priority: {
                      bsonType: 'string',
                      enum: ['low', 'medium', 'high', 'critical'],
                      description: 'Priority level for maintenance notice notifications'
                    }
                  }
                },
                featureUpdates: {
                  bsonType: 'object',
                  required: ['enabled', 'deliveryMethod', 'priority'],
                  properties: {
                    enabled: {
                      bsonType: 'bool',
                      description: 'Whether feature update notifications are enabled'
                    },
                    deliveryMethod: {
                      bsonType: 'string',
                      enum: ['in_app', 'email', 'both'],
                      description: 'Delivery method for feature update notifications'
                    },
                    priority: {
                      bsonType: 'string',
                      enum: ['low', 'medium', 'high', 'critical'],
                      description: 'Priority level for feature update notifications'
                    }
                  }
                },
                globalSettings: {
                  bsonType: 'object',
                  required: ['soundEnabled', 'desktopNotifications', 'emailDigest', 'digestFrequency'],
                  properties: {
                    soundEnabled: {
                      bsonType: 'bool',
                      description: 'Whether sound notifications are enabled'
                    },
                    desktopNotifications: {
                      bsonType: 'bool',
                      description: 'Whether desktop notifications are enabled'
                    },
                    emailDigest: {
                      bsonType: 'bool',
                      description: 'Whether email digest is enabled'
                    },
                    digestFrequency: {
                      bsonType: 'string',
                      enum: ['immediate', 'hourly', 'daily', 'weekly'],
                      description: 'Frequency of email digest'
                    }
                  }
                }
              }
            },
            widgets: {
              bsonType: 'array',
              description: 'Dashboard widget configurations'
            },
            theme: {
              bsonType: 'object',
              description: 'Theme settings'
            },
            layout: {
              bsonType: 'object',
              description: 'Layout settings'
            },
            accessibility: {
              bsonType: 'object',
              description: 'Accessibility settings'
            },
            customSettings: {
              bsonType: 'object',
              description: 'Custom user settings'
            },
            version: {
              bsonType: 'string',
              description: 'Preferences version'
            },
            isActive: {
              bsonType: 'bool',
              description: 'Whether preferences are active'
            },
            createdAt: {
              bsonType: 'date',
              description: 'When preferences were created'
            },
            updatedAt: {
              bsonType: 'date',
              description: 'When preferences were last updated'
            }
          }
        }
      }
    });

    // Create indexes for notification preferences
    console.log('Creating indexes for notification preferences...');

    // Index on userId for user-specific queries
    await mongoose.connection.db.collection('user_preferences').createIndex(
      { userId: 1 },
      { name: 'idx_userId' }
    );

    // Index on role for role-based queries
    await mongoose.connection.db.collection('user_preferences').createIndex(
      { role: 1 },
      { name: 'idx_role' }
    );

    // Index on notification preferences for efficient queries
    await mongoose.connection.db.collection('user_preferences').createIndex(
      { 'notificationPreferences.analysisCompletion.enabled': 1 },
      { name: 'idx_notification_analysis_enabled' }
    );

    await mongoose.connection.db.collection('user_preferences').createIndex(
      { 'notificationPreferences.systemAlerts.enabled': 1 },
      { name: 'idx_notification_system_enabled' }
    );

    await mongoose.connection.db.collection('user_preferences').createIndex(
      { 'notificationPreferences.securityAlerts.enabled': 1 },
      { name: 'idx_notification_security_enabled' }
    );

    // Index on global settings
    await mongoose.connection.db.collection('user_preferences').createIndex(
      { 'notificationPreferences.globalSettings.emailDigest': 1 },
      { name: 'idx_notification_email_digest' }
    );

    await mongoose.connection.db.collection('user_preferences').createIndex(
      { 'notificationPreferences.globalSettings.desktopNotifications': 1 },
      { name: 'idx_notification_desktop_enabled' }
    );

    // Compound index for efficient notification preference queries
    await mongoose.connection.db.collection('user_preferences').createIndex(
      { 
        userId: 1, 
        'notificationPreferences.globalSettings.emailDigest': 1,
        'notificationPreferences.globalSettings.desktopNotifications': 1
      },
      { name: 'idx_user_notification_settings' }
    );

    console.log('User preferences collection updated successfully for notifications');
  } catch (error) {
    console.error('Error updating user_preferences collection:', error);
    throw error;
  }
}

async function down() {
  try {
    console.log('Removing notification preferences from user_preferences collection...');

    // Remove notification preferences from all documents
    await mongoose.connection.db.collection('user_preferences').updateMany(
      { notificationPreferences: { $exists: true } },
      {
        $unset: {
          notificationPreferences: 1
        }
      }
    );

    // Drop notification-related indexes
    const indexesToDrop = [
      'idx_notification_analysis_enabled',
      'idx_notification_system_enabled',
      'idx_notification_security_enabled',
      'idx_notification_email_digest',
      'idx_notification_desktop_enabled',
      'idx_user_notification_settings'
    ];

    for (const indexName of indexesToDrop) {
      try {
        await mongoose.connection.db.collection('user_preferences').dropIndex(indexName);
        console.log(`Dropped index: ${indexName}`);
      } catch (error) {
        console.log(`Index ${indexName} not found or already dropped`);
      }
    }

    // Update the collection validator to remove notification preferences
    await mongoose.connection.db.command({
      collMod: 'user_preferences',
      validator: {
        $jsonSchema: {
          bsonType: 'object',
          required: ['userId'],
          properties: {
            userId: {
              bsonType: 'string',
              description: 'User ID'
            },
            role: {
              bsonType: 'string',
              enum: ['admin', 'analyst', 'viewer', 'security_officer', 'compliance_manager', 'system_admin'],
              description: 'User role'
            },
            widgets: {
              bsonType: 'array',
              description: 'Dashboard widget configurations'
            },
            theme: {
              bsonType: 'object',
              description: 'Theme settings'
            },
            layout: {
              bsonType: 'object',
              description: 'Layout settings'
            },
            accessibility: {
              bsonType: 'object',
              description: 'Accessibility settings'
            },
            customSettings: {
              bsonType: 'object',
              description: 'Custom user settings'
            },
            version: {
              bsonType: 'string',
              description: 'Preferences version'
            },
            isActive: {
              bsonType: 'bool',
              description: 'Whether preferences are active'
            },
            createdAt: {
              bsonType: 'date',
              description: 'When preferences were created'
            },
            updatedAt: {
              bsonType: 'date',
              description: 'When preferences were last updated'
            }
          }
        }
      }
    });

    console.log('Notification preferences removed from user_preferences collection');
  } catch (error) {
    console.error('Error removing notification preferences:', error);
    throw error;
  }
}

module.exports = { up, down };
