import React from 'react';
import { BellIcon } from '@heroicons/react/24/outline';
import { NotificationBadgeProps } from '@/types/notifications';
import styles from './NotificationCenter.module.css';

/**
 * NotificationBadge component
 * Displays unread notification count badge
 */
export const NotificationBadge: React.FC<NotificationBadgeProps> = ({
  count,
  showCount = true,
  maxCount = 99,
  size = 'medium',
  color = 'red',
  pulsing = false,
  className = '',
}) => {
  const displayCount = count > maxCount ? `${maxCount}+` : count.toString();
  const shouldShowBadge = count > 0;

  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return styles.badgeSmall;
      case 'large':
        return styles.badgeLarge;
      default:
        return styles.badgeMedium;
    }
  };

  const getColorClasses = () => {
    switch (color) {
      case 'blue':
        return styles.badgeBlue;
      case 'green':
        return styles.badgeGreen;
      case 'yellow':
        return styles.badgeYellow;
      case 'purple':
        return styles.badgePurple;
      default:
        return styles.badgeRed;
    }
  };

  const getPulsingClass = () => {
    return pulsing ? styles.badgePulsing : '';
  };

  return (
    <div className={`${styles.notificationBadge} ${className}`}>
      <BellIcon className={styles.notificationBadgeIcon} />
      
      {shouldShowBadge && (
        <span 
          className={`${styles.notificationBadgeCount} ${getSizeClasses()} ${getColorClasses()} ${getPulsingClass()}`}
          aria-label={`${count} unread notifications`}
        >
          {showCount && displayCount}
        </span>
      )}
    </div>
  );
};

export default NotificationBadge;
