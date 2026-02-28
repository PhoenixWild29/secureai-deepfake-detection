import React, { useState } from 'react';
import { 
  LightBulbIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ArrowRightIcon,
  DocumentTextIcon,
  PlayIcon,
  ExternalLinkIcon,
  UserIcon,
  CogIcon
} from '@heroicons/react/24/outline';
import { 
  TroubleshootingGuideProps, 
  TroubleshootingStep, 
  TroubleshootingType,
  TroubleshootingPriority 
} from '@/types/errorRecovery';
import styles from './ErrorRecoveryInterface.module.css';

/**
 * TroubleshootingGuide component
 * Displays troubleshooting guidance with suggested actions based on error type and context
 */
export const TroubleshootingGuide: React.FC<TroubleshootingGuideProps> = ({
  error,
  steps,
  onStepComplete,
  className = '',
}) => {
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const getStepIcon = (type: TroubleshootingType) => {
    switch (type) {
      case 'check_system':
        return <CogIcon className={styles.troubleshootingStepIcon} />;
      case 'verify_input':
        return <DocumentTextIcon className={styles.troubleshootingStepIcon} />;
      case 'restart_service':
        return <PlayIcon className={styles.troubleshootingStepIcon} />;
      case 'clear_cache':
        return <CogIcon className={styles.troubleshootingStepIcon} />;
      case 'update_configuration':
        return <CogIcon className={styles.troubleshootingStepIcon} />;
      case 'contact_support':
        return <UserIcon className={styles.troubleshootingStepIcon} />;
      case 'manual_intervention':
        return <ExclamationTriangleIcon className={styles.troubleshootingStepIcon} />;
      default:
        return <InformationCircleIcon className={styles.troubleshootingStepIcon} />;
    }
  };

  const getPriorityColor = (priority: TroubleshootingPriority) => {
    switch (priority) {
      case 'urgent':
        return styles.troubleshootingPriorityUrgent;
      case 'high':
        return styles.troubleshootingPriorityHigh;
      case 'medium':
        return styles.troubleshootingPriorityMedium;
      case 'low':
        return styles.troubleshootingPriorityLow;
      default:
        return styles.troubleshootingPriorityMedium;
    }
  };

  const getPriorityIcon = (priority: TroubleshootingPriority) => {
    switch (priority) {
      case 'urgent':
        return <ExclamationTriangleIcon className={styles.troubleshootingPriorityIconUrgent} />;
      case 'high':
        return <ExclamationTriangleIcon className={styles.troubleshootingPriorityIconHigh} />;
      case 'medium':
        return <InformationCircleIcon className={styles.troubleshootingPriorityIconMedium} />;
      case 'low':
        return <InformationCircleIcon className={styles.troubleshootingPriorityIconLow} />;
      default:
        return <InformationCircleIcon className={styles.troubleshootingPriorityIconMedium} />;
    }
  };

  const formatEstimatedTime = (timeInMinutes?: number) => {
    if (!timeInMinutes) return 'Unknown';
    
    if (timeInMinutes < 1) {
      return '< 1 minute';
    } else if (timeInMinutes < 60) {
      return `${timeInMinutes} minute${timeInMinutes > 1 ? 's' : ''}`;
    } else {
      const hours = Math.floor(timeInMinutes / 60);
      const minutes = timeInMinutes % 60;
      if (minutes === 0) {
        return `${hours} hour${hours > 1 ? 's' : ''}`;
      } else {
        return `${hours}h ${minutes}m`;
      }
    }
  };

  const toggleStepExpansion = (stepId: string) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stepId)) {
        newSet.delete(stepId);
      } else {
        newSet.add(stepId);
      }
      return newSet;
    });
  };

  const markStepComplete = (stepId: string) => {
    setCompletedSteps(prev => {
      const newSet = new Set(prev);
      newSet.add(stepId);
      return newSet;
    });

    if (onStepComplete) {
      onStepComplete(stepId);
    }
  };

  const isStepCompleted = (stepId: string) => completedSteps.has(stepId);
  const isStepExpanded = (stepId: string) => expandedSteps.has(stepId);

  // Sort steps by priority
  const sortedSteps = [...steps].sort((a, b) => {
    const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 };
    return priorityOrder[a.priority] - priorityOrder[b.priority];
  });

  const completedCount = completedSteps.size;
  const totalCount = steps.length;
  const progressPercentage = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <div className={`${styles.troubleshootingGuide} ${className}`}>
      {/* Header */}
      <div className={styles.troubleshootingGuideHeader}>
        <div className={styles.troubleshootingGuideTitle}>
          <LightBulbIcon className={styles.troubleshootingGuideIcon} />
          <h3 className={styles.troubleshootingGuideTitleText}>Troubleshooting Guide</h3>
        </div>
        
        <div className={styles.troubleshootingGuideProgress}>
          <div className={styles.troubleshootingGuideProgressBar}>
            <div 
              className={styles.troubleshootingGuideProgressFill}
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          <span className={styles.troubleshootingGuideProgressText}>
            {completedCount} of {totalCount} steps completed
          </span>
        </div>
      </div>

      {/* Error Context */}
      <div className={styles.troubleshootingGuideContext}>
        <h4 className={styles.troubleshootingGuideContextTitle}>
          Troubleshooting for: {error.type.replace(/_/g, ' ').toUpperCase()}
        </h4>
        <p className={styles.troubleshootingGuideContextDescription}>
          Follow these steps to resolve the error. Steps are ordered by priority and estimated effectiveness.
        </p>
      </div>

      {/* Steps List */}
      <div className={styles.troubleshootingGuideSteps}>
        {sortedSteps.map((step, index) => {
          const isCompleted = isStepCompleted(step.id);
          const isExpanded = isStepExpanded(step.id);

          return (
            <div 
              key={step.id} 
              className={`${styles.troubleshootingStep} ${
                isCompleted ? styles.troubleshootingStepCompleted : ''
              }`}
            >
              {/* Step Header */}
              <div 
                className={styles.troubleshootingStepHeader}
                onClick={() => toggleStepExpansion(step.id)}
                role="button"
                tabIndex={0}
                aria-expanded={isExpanded}
              >
                <div className={styles.troubleshootingStepMain}>
                  <div className={styles.troubleshootingStepNumber}>
                    {isCompleted ? (
                      <CheckCircleIcon className={styles.troubleshootingStepNumberIconCompleted} />
                    ) : (
                      <span className={styles.troubleshootingStepNumberText}>
                        {index + 1}
                      </span>
                    )}
                  </div>

                  <div className={styles.troubleshootingStepContent}>
                    <div className={styles.troubleshootingStepTitle}>
                      <h5 className={styles.troubleshootingStepTitleText}>
                        {step.title}
                      </h5>
                      <div className={`${styles.troubleshootingStepPriority} ${getPriorityColor(step.priority)}`}>
                        {getPriorityIcon(step.priority)}
                        <span className={styles.troubleshootingStepPriorityText}>
                          {step.priority.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <p className={styles.troubleshootingStepDescription}>
                      {step.description}
                    </p>

                    <div className={styles.troubleshootingStepMeta}>
                      <div className={styles.troubleshootingStepMetaItem}>
                        {getStepIcon(step.type)}
                        <span className={styles.troubleshootingStepMetaText}>
                          {step.type.replace(/_/g, ' ').toUpperCase()}
                        </span>
                      </div>
                      
                      <div className={styles.troubleshootingStepMetaItem}>
                        <ClockIcon className={styles.troubleshootingStepMetaIcon} />
                        <span className={styles.troubleshootingStepMetaText}>
                          {formatEstimatedTime(step.estimatedTime)}
                        </span>
                      </div>

                      {step.requiresUserAction && (
                        <div className={styles.troubleshootingStepMetaItem}>
                          <UserIcon className={styles.troubleshootingStepMetaIcon} />
                          <span className={styles.troubleshootingStepMetaText}>
                            Requires User Action
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className={styles.troubleshootingStepExpand}>
                  <ArrowRightIcon 
                    className={`${styles.troubleshootingStepExpandIcon} ${
                      isExpanded ? styles.troubleshootingStepExpandIconExpanded : ''
                    }`} 
                  />
                </div>
              </div>

              {/* Step Details */}
              {isExpanded && (
                <div className={styles.troubleshootingStepDetails}>
                  {/* Prerequisites */}
                  {step.prerequisites && step.prerequisites.length > 0 && (
                    <div className={styles.troubleshootingStepPrerequisites}>
                      <h6 className={styles.troubleshootingStepPrerequisitesTitle}>
                        Prerequisites
                      </h6>
                      <ul className={styles.troubleshootingStepPrerequisitesList}>
                        {step.prerequisites.map((prerequisite, idx) => (
                          <li key={idx} className={styles.troubleshootingStepPrerequisitesItem}>
                            {prerequisite}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Expected Outcome */}
                  {step.expectedOutcome && (
                    <div className={styles.troubleshootingStepOutcome}>
                      <h6 className={styles.troubleshootingStepOutcomeTitle}>
                        Expected Outcome
                      </h6>
                      <p className={styles.troubleshootingStepOutcomeText}>
                        {step.expectedOutcome}
                      </p>
                    </div>
                  )}

                  {/* Resources */}
                  {step.resources && (
                    <div className={styles.troubleshootingStepResources}>
                      <h6 className={styles.troubleshootingStepResourcesTitle}>
                        Additional Resources
                      </h6>
                      <div className={styles.troubleshootingStepResourcesList}>
                        {step.resources.documentation && (
                          <a 
                            href={step.resources.documentation}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={styles.troubleshootingStepResourceLink}
                          >
                            <DocumentTextIcon className={styles.troubleshootingStepResourceIcon} />
                            <span>Documentation</span>
                            <ExternalLinkIcon className={styles.troubleshootingStepResourceExternalIcon} />
                          </a>
                        )}
                        {step.resources.video && (
                          <a 
                            href={step.resources.video}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={styles.troubleshootingStepResourceLink}
                          >
                            <PlayIcon className={styles.troubleshootingStepResourceIcon} />
                            <span>Video Guide</span>
                            <ExternalLinkIcon className={styles.troubleshootingStepResourceExternalIcon} />
                          </a>
                        )}
                        {step.resources.support && (
                          <a 
                            href={step.resources.support}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={styles.troubleshootingStepResourceLink}
                          >
                            <UserIcon className={styles.troubleshootingStepResourceIcon} />
                            <span>Support</span>
                            <ExternalLinkIcon className={styles.troubleshootingStepResourceExternalIcon} />
                          </a>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Action Button */}
                  {!isCompleted && (
                    <div className={styles.troubleshootingStepActions}>
                      <button
                        className={styles.troubleshootingStepCompleteButton}
                        onClick={() => markStepComplete(step.id)}
                        aria-label={`Mark step "${step.title}" as completed`}
                      >
                        <CheckCircleIcon className={styles.troubleshootingStepCompleteButtonIcon} />
                        Mark as Completed
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Completion Summary */}
      {completedCount > 0 && (
        <div className={styles.troubleshootingGuideSummary}>
          <div className={styles.troubleshootingGuideSummaryHeader}>
            <CheckCircleIcon className={styles.troubleshootingGuideSummaryIcon} />
            <h4 className={styles.troubleshootingGuideSummaryTitle}>
              Troubleshooting Progress
            </h4>
          </div>
          <p className={styles.troubleshootingGuideSummaryText}>
            You've completed {completedCount} of {totalCount} troubleshooting steps. 
            {completedCount === totalCount 
              ? ' All steps have been completed. If the error persists, please contact support.'
              : ' Continue with the remaining steps to resolve the error.'
            }
          </p>
        </div>
      )}
    </div>
  );
};

export default TroubleshootingGuide;
