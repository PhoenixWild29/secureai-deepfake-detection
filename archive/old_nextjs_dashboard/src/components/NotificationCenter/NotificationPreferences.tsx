import React, { useState, useCallback } from 'react';
import { 
  CogIcon,
  BellIcon,
  EnvelopeIcon,
  GlobeAltIcon,
  DevicePhoneMobileIcon,
  SpeakerWaveIcon,
  DesktopComputerIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { 
  NotificationPreferencesProps, 
  NotificationPreferences,
  NotificationType,
  DeliveryMethod,
  NotificationPriority
} from '@/types/notifications';
import { auditLogger } from '@/utils/auditLogger';
import styles from './NotificationCenter.module.css';

/**
 * NotificationPreferences component
 * Allows users to configure notification types and delivery methods
 */
export const NotificationPreferences: React.FC<NotificationPreferencesProps> = ({
  preferences,
  onPreferencesChange,
  showAdvanced = false,
  className = '',
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['global']));
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [localPreferences, setLocalPreferences] = useState<NotificationPreferences>(preferences);

  // Available notification types
  const notificationTypes: NotificationType[] = [
    'analysis_complete', 'analysis_failed', 'analysis_started', 'analysis_progress',
    'system_error', 'system_warning', 'system_info', 'user_action_required',
    'security_alert', 'maintenance_notice', 'feature_update', 'data_export_complete',
    'data_export_failed', 'quota_warning', 'quota_exceeded', 'backup_complete',
    'backup_failed', 'integration_success', 'integration_failed', 'custom'
  ];

  // Available delivery methods
  const deliveryMethods: DeliveryMethod[] = ['in_app', 'email', 'webhook', 'sms', 'push'];

  // Available priorities
  const priorities: NotificationPriority[] = ['low', 'normal', 'high', 'urgent'];

  // Toggle section expansion
  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId);
      } else {
        newSet.add(sectionId);
      }
      return newSet;
    });
  };

  // Update preferences
  const updatePreferences = useCallback((updates: Partial<NotificationPreferences>) => {
    const newPreferences = { ...localPreferences, ...updates };
    setLocalPreferences(newPreferences);
    setHasChanges(true);
  }, [localPreferences]);

  // Update notification type preference
  const updateNotificationTypePreference = (
    type: NotificationType, 
    updates: Partial<typeof localPreferences.types[NotificationType]>
  ) => {
    const newTypes = {
      ...localPreferences.types,
      [type]: {
        ...localPreferences.types[type],
        ...updates,
      },
    };
    updatePreferences({ types: newTypes });
  };

  // Update delivery method preference
  const updateDeliveryMethodPreference = (
    method: DeliveryMethod,
    updates: Partial<typeof localPreferences.deliveryMethods[DeliveryMethod]>
  ) => {
    const newDeliveryMethods = {
      ...localPreferences.deliveryMethods,
      [method]: {
        ...localPreferences.deliveryMethods[method],
        ...updates,
      },
    };
    updatePreferences({ deliveryMethods: newDeliveryMethods });
  };

  // Update global settings
  const updateGlobalSettings = (updates: Partial<typeof localPreferences.global>) => {
    const newGlobal = {
      ...localPreferences.global,
      ...updates,
    };
    updatePreferences({ global: newGlobal });
  };

  // Save preferences
  const savePreferences = async () => {
    if (!onPreferencesChange) return;

    setIsSaving(true);
    try {
      await onPreferencesChange(localPreferences);
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save preferences:', error);
    } finally {
      setIsSaving(false);
    }
  };

  // Reset preferences
  const resetPreferences = () => {
    setLocalPreferences(preferences);
    setHasChanges(false);
  };

  // Get delivery method icon
  const getDeliveryMethodIcon = (method: DeliveryMethod) => {
    switch (method) {
      case 'in_app':
        return <BellIcon className={styles.preferencesDeliveryMethodIcon} />;
      case 'email':
        return <EnvelopeIcon className={styles.preferencesDeliveryMethodIcon} />;
      case 'webhook':
        return <GlobeAltIcon className={styles.preferencesDeliveryMethodIcon} />;
      case 'sms':
        return <DevicePhoneMobileIcon className={styles.preferencesDeliveryMethodIcon} />;
      case 'push':
        return <DesktopComputerIcon className={styles.preferencesDeliveryMethodIcon} />;
      default:
        return <BellIcon className={styles.preferencesDeliveryMethodIcon} />;
    }
  };

  // Get delivery method label
  const getDeliveryMethodLabel = (method: DeliveryMethod) => {
    switch (method) {
      case 'in_app':
        return 'In-App';
      case 'email':
        return 'Email';
      case 'webhook':
        return 'Webhook';
      case 'sms':
        return 'SMS';
      case 'push':
        return 'Push';
      default:
        return method;
    }
  };

  // Get priority color
  const getPriorityColor = (priority: NotificationPriority) => {
    switch (priority) {
      case 'urgent':
        return styles.preferencesPriorityUrgent;
      case 'high':
        return styles.preferencesPriorityHigh;
      case 'normal':
        return styles.preferencesPriorityNormal;
      case 'low':
        return styles.preferencesPriorityLow;
      default:
        return styles.preferencesPriorityNormal;
    }
  };

  return (
    <div className={`${styles.notificationPreferences} ${className}`}>
      {/* Header */}
      <div className={styles.preferencesHeader}>
        <div className={styles.preferencesTitle}>
          <CogIcon className={styles.preferencesTitleIcon} />
          <h3 className={styles.preferencesTitleText}>Notification Preferences</h3>
        </div>

        <div className={styles.preferencesActions}>
          {hasChanges && (
            <button
              className={styles.preferencesActionButton}
              onClick={resetPreferences}
              disabled={isSaving}
            >
              Reset
            </button>
          )}
          <button
            className={`${styles.preferencesActionButton} ${styles.preferencesActionButtonPrimary}`}
            onClick={savePreferences}
            disabled={!hasChanges || isSaving}
          >
            {isSaving ? (
              <>
                <ArrowPathIcon className={styles.preferencesActionSpinner} />
                Saving...
              </>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </div>

      {/* Global Settings */}
      <div className={styles.preferencesSection}>
        <button
          className={styles.preferencesSectionHeader}
          onClick={() => toggleSection('global')}
          aria-expanded={expandedSections.has('global')}
        >
          <div className={styles.preferencesSectionTitle}>
            <BellIcon className={styles.preferencesSectionIcon} />
            <h4 className={styles.preferencesSectionTitleText}>Global Settings</h4>
          </div>
          {expandedSections.has('global') ? (
            <ChevronDownIcon className={styles.preferencesSectionExpandIcon} />
          ) : (
            <ChevronRightIcon className={styles.preferencesSectionExpandIcon} />
          )}
        </button>

        {expandedSections.has('global') && (
          <div className={styles.preferencesSectionContent}>
            <div className={styles.preferencesGlobalSettings}>
              <label className={styles.preferencesGlobalSetting}>
                <input
                  type="checkbox"
                  checked={localPreferences.global.enabled}
                  onChange={(e) => updateGlobalSettings({ enabled: e.target.checked })}
                  className={styles.preferencesGlobalCheckbox}
                />
                <span className={styles.preferencesGlobalLabel}>Enable all notifications</span>
              </label>

              <label className={styles.preferencesGlobalSetting}>
                <input
                  type="checkbox"
                  checked={localPreferences.global.showBadges}
                  onChange={(e) => updateGlobalSettings({ showBadges: e.target.checked })}
                  className={styles.preferencesGlobalCheckbox}
                />
                <span className={styles.preferencesGlobalLabel}>Show notification badges</span>
              </label>

              <label className={styles.preferencesGlobalSetting}>
                <input
                  type="checkbox"
                  checked={localPreferences.global.playSounds}
                  onChange={(e) => updateGlobalSettings({ playSounds: e.target.checked })}
                  className={styles.preferencesGlobalCheckbox}
                />
                <span className={styles.preferencesGlobalLabel}>Play notification sounds</span>
              </label>

              <label className={styles.preferencesGlobalSetting}>
                <input
                  type="checkbox"
                  checked={localPreferences.global.showDesktopNotifications}
                  onChange={(e) => updateGlobalSettings({ showDesktopNotifications: e.target.checked })}
                  className={styles.preferencesGlobalCheckbox}
                />
                <span className={styles.preferencesGlobalLabel}>Show desktop notifications</span>
              </label>

              <div className={styles.preferencesGlobalSetting}>
                <label className={styles.preferencesGlobalLabel}>
                  Default Priority
                </label>
                <select
                  value={localPreferences.global.defaultPriority}
                  onChange={(e) => updateGlobalSettings({ defaultPriority: e.target.value as NotificationPriority })}
                  className={styles.preferencesGlobalSelect}
                >
                  {priorities.map(priority => (
                    <option key={priority} value={priority}>
                      {priority.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.preferencesGlobalSetting}>
                <label className={styles.preferencesGlobalLabel}>
                  Max History Count
                </label>
                <input
                  type="number"
                  min="10"
                  max="10000"
                  value={localPreferences.global.maxHistoryCount}
                  onChange={(e) => updateGlobalSettings({ maxHistoryCount: parseInt(e.target.value) })}
                  className={styles.preferencesGlobalInput}
                />
              </div>

              <div className={styles.preferencesGlobalSetting}>
                <label className={styles.preferencesGlobalLabel}>
                  Auto-dismiss Timeout (ms)
                </label>
                <input
                  type="number"
                  min="0"
                  max="60000"
                  value={localPreferences.global.autoDismissTimeout || 0}
                  onChange={(e) => updateGlobalSettings({ autoDismissTimeout: parseInt(e.target.value) || undefined })}
                  className={styles.preferencesGlobalInput}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Delivery Methods */}
      <div className={styles.preferencesSection}>
        <button
          className={styles.preferencesSectionHeader}
          onClick={() => toggleSection('delivery')}
          aria-expanded={expandedSections.has('delivery')}
        >
          <div className={styles.preferencesSectionTitle}>
            <GlobeAltIcon className={styles.preferencesSectionIcon} />
            <h4 className={styles.preferencesSectionTitleText}>Delivery Methods</h4>
          </div>
          {expandedSections.has('delivery') ? (
            <ChevronDownIcon className={styles.preferencesSectionExpandIcon} />
          ) : (
            <ChevronRightIcon className={styles.preferencesSectionExpandIcon} />
          )}
        </button>

        {expandedSections.has('delivery') && (
          <div className={styles.preferencesSectionContent}>
            <div className={styles.preferencesDeliveryMethods}>
              {deliveryMethods.map(method => (
                <div key={method} className={styles.preferencesDeliveryMethod}>
                  <div className={styles.preferencesDeliveryMethodHeader}>
                    {getDeliveryMethodIcon(method)}
                    <h5 className={styles.preferencesDeliveryMethodTitle}>
                      {getDeliveryMethodLabel(method)}
                    </h5>
                    <label className={styles.preferencesDeliveryMethodToggle}>
                      <input
                        type="checkbox"
                        checked={localPreferences.deliveryMethods[method].enabled}
                        onChange={(e) => updateDeliveryMethodPreference(method, { enabled: e.target.checked })}
                        className={styles.preferencesDeliveryMethodCheckbox}
                      />
                      <span className={styles.preferencesDeliveryMethodToggleSlider} />
                    </label>
                  </div>
                  
                  {localPreferences.deliveryMethods[method].enabled && (
                    <div className={styles.preferencesDeliveryMethodConfig}>
                      <p className={styles.preferencesDeliveryMethodDescription}>
                        Configure {getDeliveryMethodLabel(method).toLowerCase()} delivery settings
                      </p>
                      {/* Additional configuration options would go here */}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Notification Types */}
      <div className={styles.preferencesSection}>
        <button
          className={styles.preferencesSectionHeader}
          onClick={() => toggleSection('types')}
          aria-expanded={expandedSections.has('types')}
        >
          <div className={styles.preferencesSectionTitle}>
            <ExclamationTriangleIcon className={styles.preferencesSectionIcon} />
            <h4 className={styles.preferencesSectionTitleText}>Notification Types</h4>
          </div>
          {expandedSections.has('types') ? (
            <ChevronDownIcon className={styles.preferencesSectionExpandIcon} />
          ) : (
            <ChevronRightIcon className={styles.preferencesSectionExpandIcon} />
          )}
        </button>

        {expandedSections.has('types') && (
          <div className={styles.preferencesSectionContent}>
            <div className={styles.preferencesNotificationTypes}>
              {notificationTypes.map(type => {
                const typePreference = localPreferences.types[type];
                return (
                  <div key={type} className={styles.preferencesNotificationType}>
                    <div className={styles.preferencesNotificationTypeHeader}>
                      <h5 className={styles.preferencesNotificationTypeTitle}>
                        {type.replace(/_/g, ' ').toUpperCase()}
                      </h5>
                      <label className={styles.preferencesNotificationTypeToggle}>
                        <input
                          type="checkbox"
                          checked={typePreference.enabled}
                          onChange={(e) => updateNotificationTypePreference(type, { enabled: e.target.checked })}
                          className={styles.preferencesNotificationTypeCheckbox}
                        />
                        <span className={styles.preferencesNotificationTypeToggleSlider} />
                      </label>
                    </div>

                    {typePreference.enabled && (
                      <div className={styles.preferencesNotificationTypeConfig}>
                        <div className={styles.preferencesNotificationTypeSettings}>
                          <div className={styles.preferencesNotificationTypeSetting}>
                            <label className={styles.preferencesNotificationTypeSettingLabel}>
                              Priority
                            </label>
                            <select
                              value={typePreference.priority}
                              onChange={(e) => updateNotificationTypePreference(type, { priority: e.target.value as NotificationPriority })}
                              className={styles.preferencesNotificationTypeSelect}
                            >
                              {priorities.map(priority => (
                                <option key={priority} value={priority}>
                                  {priority.toUpperCase()}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div className={styles.preferencesNotificationTypeDeliveryMethods}>
                            <label className={styles.preferencesNotificationTypeSettingLabel}>
                              Delivery Methods
                            </label>
                            <div className={styles.preferencesNotificationTypeDeliveryOptions}>
                              {deliveryMethods.map(method => (
                                <label key={method} className={styles.preferencesNotificationTypeDeliveryOption}>
                                  <input
                                    type="checkbox"
                                    checked={typePreference.deliveryMethods.includes(method)}
                                    onChange={(e) => {
                                      const methods = typePreference.deliveryMethods;
                                      const newMethods = e.target.checked
                                        ? [...methods, method]
                                        : methods.filter(m => m !== method);
                                      updateNotificationTypePreference(type, { deliveryMethods: newMethods });
                                    }}
                                    className={styles.preferencesNotificationTypeDeliveryCheckbox}
                                  />
                                  <span className={styles.preferencesNotificationTypeDeliveryLabel}>
                                    {getDeliveryMethodLabel(method)}
                                  </span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Advanced Settings */}
      {showAdvanced && (
        <div className={styles.preferencesSection}>
          <button
            className={styles.preferencesSectionHeader}
            onClick={() => toggleSection('advanced')}
            aria-expanded={expandedSections.has('advanced')}
          >
            <div className={styles.preferencesSectionTitle}>
              <CogIcon className={styles.preferencesSectionIcon} />
              <h4 className={styles.preferencesSectionTitleText}>Advanced Settings</h4>
            </div>
            {expandedSections.has('advanced') ? (
              <ChevronDownIcon className={styles.preferencesSectionExpandIcon} />
            ) : (
              <ChevronRightIcon className={styles.preferencesSectionExpandIcon} />
            )}
          </button>

          {expandedSections.has('advanced') && (
            <div className={styles.preferencesSectionContent}>
              <div className={styles.preferencesAdvancedSettings}>
                <p className={styles.preferencesAdvancedDescription}>
                  Advanced notification settings and configuration options.
                </p>
                {/* Additional advanced settings would go here */}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationPreferences;