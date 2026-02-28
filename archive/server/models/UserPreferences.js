/**
 * UserPreferences Model
 * Mongoose model for user preferences including notification settings
 */

const mongoose = require('mongoose');
const Schema = mongoose.Schema;

// Notification Type Preferences Schema
const NotificationTypePreferencesSchema = new Schema({
  enabled: {
    type: Boolean,
    default: true
  },
  deliveryMethod: {
    type: String,
    enum: ['in_app', 'email', 'both'],
    default: 'in_app'
  },
  priority: {
    type: String,
    enum: ['low', 'medium', 'high', 'critical'],
    default: 'medium'
  }
}, { _id: false });

// Global Notification Settings Schema
const GlobalNotificationSettingsSchema = new Schema({
  soundEnabled: {
    type: Boolean,
    default: true
  },
  desktopNotifications: {
    type: Boolean,
    default: false
  },
  emailDigest: {
    type: Boolean,
    default: false
  },
  digestFrequency: {
    type: String,
    enum: ['immediate', 'hourly', 'daily', 'weekly'],
    default: 'daily'
  }
}, { _id: false });

// Notification Preferences Schema
const NotificationPreferencesSchema = new Schema({
  analysisCompletion: {
    type: NotificationTypePreferencesSchema,
    default: () => ({})
  },
  systemAlerts: {
    type: NotificationTypePreferencesSchema,
    default: () => ({})
  },
  complianceUpdates: {
    type: NotificationTypePreferencesSchema,
    default: () => ({})
  },
  securityAlerts: {
    type: NotificationTypePreferencesSchema,
    default: () => ({})
  },
  maintenanceNotices: {
    type: NotificationTypePreferencesSchema,
    default: () => ({})
  },
  featureUpdates: {
    type: NotificationTypePreferencesSchema,
    default: () => ({})
  },
  globalSettings: {
    type: GlobalNotificationSettingsSchema,
    default: () => ({})
  }
}, { _id: false });

// Widget Configuration Schema
const WidgetConfigurationSchema = new Schema({
  widgetId: {
    type: String,
    required: true
  },
  widgetType: {
    type: String,
    required: true
  },
  positionX: {
    type: Number,
    default: 0
  },
  positionY: {
    type: Number,
    default: 0
  },
  width: {
    type: Number,
    default: 4
  },
  height: {
    type: Number,
    default: 3
  },
  visible: {
    type: Boolean,
    default: true
  },
  refreshInterval: {
    type: Number,
    default: null
  },
  customSettings: {
    type: Schema.Types.Mixed,
    default: {}
  }
}, { _id: false });

// Theme Settings Schema
const ThemeSettingsSchema = new Schema({
  themeType: {
    type: String,
    enum: ['light', 'dark', 'high_contrast', 'auto'],
    default: 'light'
  },
  primaryColor: {
    type: String,
    default: '#1976d2'
  },
  secondaryColor: {
    type: String,
    default: '#424242'
  },
  accentColor: {
    type: String,
    default: '#ff4081'
  },
  fontSize: {
    type: String,
    enum: ['small', 'medium', 'large'],
    default: 'medium'
  },
  fontFamily: {
    type: String,
    default: 'system'
  },
  highContrast: {
    type: Boolean,
    default: false
  },
  reducedMotion: {
    type: Boolean,
    default: false
  }
}, { _id: false });

// Layout Settings Schema
const LayoutSettingsSchema = new Schema({
  layoutType: {
    type: String,
    enum: ['grid', 'list', 'compact', 'expanded', 'custom'],
    default: 'grid'
  },
  gridColumns: {
    type: Number,
    default: 12
  },
  gridGap: {
    type: Number,
    default: 16
  },
  panelSpacing: {
    type: Number,
    default: 8
  },
  sidebarWidth: {
    type: Number,
    default: 280
  },
  headerHeight: {
    type: Number,
    default: 64
  },
  responsiveBreakpoints: {
    type: Schema.Types.Mixed,
    default: {
      mobile: 768,
      tablet: 1024,
      desktop: 1440
    }
  },
  autoSave: {
    type: Boolean,
    default: true
  },
  snapToGrid: {
    type: Boolean,
    default: true
  }
}, { _id: false });

// Accessibility Settings Schema
const AccessibilitySettingsSchema = new Schema({
  screenReader: {
    type: Boolean,
    default: false
  },
  keyboardNavigation: {
    type: Boolean,
    default: true
  },
  focusIndicators: {
    type: Boolean,
    default: true
  },
  colorBlindSupport: {
    type: Boolean,
    default: false
  },
  textScaling: {
    type: Number,
    default: 1.0
  },
  voiceCommands: {
    type: Boolean,
    default: false
  },
  alternativeText: {
    type: Boolean,
    default: true
  }
}, { _id: false });

// Main UserPreferences Schema
const UserPreferencesSchema = new Schema({
  userId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  role: {
    type: String,
    enum: ['admin', 'analyst', 'viewer', 'security_officer', 'compliance_manager', 'system_admin'],
    default: 'viewer',
    index: true
  },
  
  // Notification preferences (new)
  notificationPreferences: {
    type: NotificationPreferencesSchema,
    default: () => ({})
  },
  
  // Dashboard preferences
  widgets: {
    type: [WidgetConfigurationSchema],
    default: []
  },
  theme: {
    type: ThemeSettingsSchema,
    default: () => ({})
  },
  layout: {
    type: LayoutSettingsSchema,
    default: () => ({})
  },
  accessibility: {
    type: AccessibilitySettingsSchema,
    default: () => ({})
  },
  
  // Custom settings
  customSettings: {
    type: Schema.Types.Mixed,
    default: {}
  },
  
  // System fields
  version: {
    type: String,
    default: '1.0.0'
  },
  isActive: {
    type: Boolean,
    default: true
  },
  createdAt: {
    type: Date,
    default: Date.now
  },
  updatedAt: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true,
  collection: 'user_preferences'
});

// Indexes for performance
UserPreferencesSchema.index({ userId: 1 });
UserPreferencesSchema.index({ role: 1 });
UserPreferencesSchema.index({ updatedAt: -1 });
UserPreferencesSchema.index({ isActive: 1 });

// Pre-save middleware
UserPreferencesSchema.pre('save', function(next) {
  this.updatedAt = new Date();
  next();
});

// Instance methods
UserPreferencesSchema.methods.updateNotificationPreferences = function(preferences) {
  this.notificationPreferences = { ...this.notificationPreferences, ...preferences };
  return this.save();
};

UserPreferencesSchema.methods.updateWidgetConfiguration = function(widgetId, updates) {
  const widgetIndex = this.widgets.findIndex(w => w.widgetId === widgetId);
  if (widgetIndex !== -1) {
    this.widgets[widgetIndex] = { ...this.widgets[widgetIndex], ...updates };
  } else {
    this.widgets.push({ widgetId, ...updates });
  }
  return this.save();
};

UserPreferencesSchema.methods.removeWidget = function(widgetId) {
  this.widgets = this.widgets.filter(w => w.widgetId !== widgetId);
  return this.save();
};

UserPreferencesSchema.methods.updateTheme = function(themeUpdates) {
  this.theme = { ...this.theme, ...themeUpdates };
  return this.save();
};

UserPreferencesSchema.methods.updateLayout = function(layoutUpdates) {
  this.layout = { ...this.layout, ...layoutUpdates };
  return this.save();
};

UserPreferencesSchema.methods.updateAccessibility = function(accessibilityUpdates) {
  this.accessibility = { ...this.accessibility, ...accessibilityUpdates };
  return this.save();
};

// Static methods
UserPreferencesSchema.statics.findByUserId = function(userId) {
  return this.findOne({ userId, isActive: true });
};

UserPreferencesSchema.statics.findByRole = function(role) {
  return this.find({ role, isActive: true });
};

UserPreferencesSchema.statics.getDefaultPreferences = function(role = 'viewer') {
  const defaultPreferences = {
    role,
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
    },
    widgets: [],
    theme: {
      themeType: 'light',
      primaryColor: '#1976d2',
      secondaryColor: '#424242',
      accentColor: '#ff4081',
      fontSize: 'medium',
      fontFamily: 'system',
      highContrast: false,
      reducedMotion: false
    },
    layout: {
      layoutType: 'grid',
      gridColumns: 12,
      gridGap: 16,
      panelSpacing: 8,
      sidebarWidth: 280,
      headerHeight: 64,
      responsiveBreakpoints: {
        mobile: 768,
        tablet: 1024,
        desktop: 1440
      },
      autoSave: true,
      snapToGrid: true
    },
    accessibility: {
      screenReader: false,
      keyboardNavigation: true,
      focusIndicators: true,
      colorBlindSupport: false,
      textScaling: 1.0,
      voiceCommands: false,
      alternativeText: true
    },
    customSettings: {},
    version: '1.0.0',
    isActive: true
  };

  // Role-specific defaults
  if (role === 'admin') {
    defaultPreferences.notificationPreferences.systemAlerts.priority = 'critical';
    defaultPreferences.notificationPreferences.securityAlerts.priority = 'critical';
    defaultPreferences.theme.themeType = 'dark';
  } else if (role === 'security_officer') {
    defaultPreferences.notificationPreferences.securityAlerts.enabled = true;
    defaultPreferences.notificationPreferences.securityAlerts.deliveryMethod = 'both';
    defaultPreferences.notificationPreferences.securityAlerts.priority = 'critical';
    defaultPreferences.theme.themeType = 'dark';
    defaultPreferences.theme.primaryColor = '#d32f2f';
  } else if (role === 'compliance_manager') {
    defaultPreferences.notificationPreferences.complianceUpdates.enabled = true;
    defaultPreferences.notificationPreferences.complianceUpdates.deliveryMethod = 'both';
    defaultPreferences.notificationPreferences.complianceUpdates.priority = 'high';
    defaultPreferences.theme.primaryColor = '#388e3c';
  }

  return defaultPreferences;
};

UserPreferencesSchema.statics.createDefaultPreferences = function(userId, role = 'viewer') {
  const defaultPreferences = this.getDefaultPreferences(role);
  return this.create({
    userId,
    ...defaultPreferences
  });
};

UserPreferencesSchema.statics.validatePreferences = function(preferences) {
  const errors = [];
  const warnings = [];

  // Validate widget configurations
  if (preferences.widgets) {
    const widgetIds = preferences.widgets.map(w => w.widgetId);
    if (widgetIds.length !== new Set(widgetIds).size) {
      errors.push('Widget IDs must be unique');
    }

    // Check for overlapping widgets
    for (let i = 0; i < preferences.widgets.length; i++) {
      for (let j = i + 1; j < preferences.widgets.length; j++) {
        const widget1 = preferences.widgets[i];
        const widget2 = preferences.widgets[j];
        
        if (widget1.positionX < widget2.positionX + widget2.width &&
            widget1.positionX + widget1.width > widget2.positionX &&
            widget1.positionY < widget2.positionY + widget2.height &&
            widget1.positionY + widget1.height > widget2.positionY) {
          errors.push(`Widgets '${widget1.widgetId}' and '${widget2.widgetId}' overlap`);
        }
      }
    }
  }

  // Validate notification preferences
  if (preferences.notificationPreferences) {
    const np = preferences.notificationPreferences;
    
    // Check if email is enabled but no email address provided
    Object.keys(np).forEach(key => {
      if (key !== 'globalSettings' && np[key].deliveryMethod === 'email') {
        warnings.push(`${key} notifications set to email but no email address configured`);
      }
    });
  }

  // Validate accessibility settings
  if (preferences.accessibility) {
    if (preferences.accessibility.textScaling < 0.5) {
      warnings.push('Text scaling below 0.5 may affect readability');
    } else if (preferences.accessibility.textScaling > 2.0) {
      warnings.push('Text scaling above 2.0 may affect layout');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

// Export the model
const UserPreferences = mongoose.model('UserPreferences', UserPreferencesSchema);

module.exports = UserPreferences;
