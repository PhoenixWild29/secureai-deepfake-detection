/**
 * Progress Bar Component
 * Reusable animated progress bar component for displaying analysis progress
 */

import React, { useState, useEffect, useRef } from 'react';
import './ProgressBar.css';

/**
 * Progress bar component props
 * @typedef {Object} ProgressBarProps
 * @property {number} progress - Progress value (0-100)
 * @property {string} [label] - Progress label
 * @property {string} [size] - Size variant ('small', 'medium', 'large')
 * @property {string} [variant] - Color variant ('primary', 'success', 'warning', 'error')
 * @property {boolean} [animated] - Enable smooth animations
 * @property {boolean} [showPercentage] - Show percentage text
 * @property {boolean} [showLabel] - Show progress label
 * @property {string} [className] - Additional CSS classes
 * @property {Object} [style] - Additional inline styles
 */

/**
 * Progress Bar Component
 * @param {ProgressBarProps} props - Component props
 * @returns {JSX.Element} - Progress bar component
 */
const ProgressBar = ({
  progress = 0,
  label = '',
  size = 'medium',
  variant = 'primary',
  animated = true,
  showPercentage = true,
  showLabel = true,
  className = '',
  style = {}
}) => {
  const [displayProgress, setDisplayProgress] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const animationRef = useRef(null);
  const progressRef = useRef(null);

  // Clamp progress value between 0 and 100
  const clampedProgress = Math.max(0, Math.min(100, progress));

  // Animate progress changes
  useEffect(() => {
    if (!animated) {
      setDisplayProgress(clampedProgress);
      return;
    }

    setIsAnimating(true);
    
    // Cancel any existing animation
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    const startProgress = displayProgress;
    const targetProgress = clampedProgress;
    const duration = 500; // Animation duration in ms
    const startTime = Date.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progressRatio = Math.min(elapsed / duration, 1);
      
      // Use easing function for smooth animation
      const easedProgress = easeOutCubic(progressRatio);
      const currentProgress = startProgress + (targetProgress - startProgress) * easedProgress;
      
      setDisplayProgress(currentProgress);
      
      if (progressRatio < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    // Cleanup function
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [clampedProgress, animated, displayProgress]);

  // Easing function for smooth animation
  const easeOutCubic = (t) => {
    return 1 - Math.pow(1 - t, 3);
  };

  // Get size classes
  const getSizeClasses = () => {
    const sizeClasses = {
      small: 'progress-bar--small',
      medium: 'progress-bar--medium',
      large: 'progress-bar--large'
    };
    return sizeClasses[size] || sizeClasses.medium;
  };

  // Get variant classes
  const getVariantClasses = () => {
    const variantClasses = {
      primary: 'progress-bar--primary',
      success: 'progress-bar--success',
      warning: 'progress-bar--warning',
      error: 'progress-bar--error'
    };
    return variantClasses[variant] || variantClasses.primary;
  };

  // Get animation classes
  const getAnimationClasses = () => {
    return animated ? 'progress-bar--animated' : '';
  };

  // Build CSS classes
  const cssClasses = [
    'progress-bar',
    getSizeClasses(),
    getVariantClasses(),
    getAnimationClasses(),
    isAnimating ? 'progress-bar--animating' : '',
    className
  ].filter(Boolean).join(' ');

  // Format percentage display
  const formatPercentage = (value) => {
    return `${Math.round(value)}%`;
  };

  // Get progress bar width
  const progressWidth = `${displayProgress}%`;

  return (
    <div className={cssClasses} style={style}>
      {/* Progress Label */}
      {showLabel && label && (
        <div className="progress-bar__label">
          <span className="progress-bar__label-text">{label}</span>
          {showPercentage && (
            <span className="progress-bar__percentage">
              {formatPercentage(displayProgress)}
            </span>
          )}
        </div>
      )}

      {/* Progress Bar Container */}
      <div className="progress-bar__container">
        <div 
          ref={progressRef}
          className="progress-bar__track"
          role="progressbar"
          aria-valuenow={displayProgress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label || 'Progress'}
        >
          <div 
            className="progress-bar__fill"
            style={{ width: progressWidth }}
          />
          
          {/* Progress Glow Effect */}
          {animated && (
            <div 
              className="progress-bar__glow"
              style={{ width: progressWidth }}
            />
          )}
        </div>
      </div>

      {/* Percentage Only (when no label) */}
      {!showLabel && showPercentage && (
        <div className="progress-bar__percentage-only">
          {formatPercentage(displayProgress)}
        </div>
      )}
    </div>
  );
};

/**
 * Circular Progress Bar Component
 * @param {Object} props - Component props
 * @returns {JSX.Element} - Circular progress bar component
 */
export const CircularProgressBar = ({
  progress = 0,
  size = 100,
  strokeWidth = 8,
  variant = 'primary',
  animated = true,
  showPercentage = true,
  label = '',
  className = '',
  style = {}
}) => {
  const [displayProgress, setDisplayProgress] = useState(0);
  const animationRef = useRef(null);

  // Clamp progress value between 0 and 100
  const clampedProgress = Math.max(0, Math.min(100, progress));

  // Animate progress changes
  useEffect(() => {
    if (!animated) {
      setDisplayProgress(clampedProgress);
      return;
    }

    const startProgress = displayProgress;
    const targetProgress = clampedProgress;
    const duration = 500;
    const startTime = Date.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progressRatio = Math.min(elapsed / duration, 1);
      
      const easedProgress = easeOutCubic(progressRatio);
      const currentProgress = startProgress + (targetProgress - startProgress) * easedProgress;
      
      setDisplayProgress(currentProgress);
      
      if (progressRatio < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [clampedProgress, animated, displayProgress]);

  // Easing function
  const easeOutCubic = (t) => {
    return 1 - Math.pow(1 - t, 3);
  };

  // Calculate circle properties
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (displayProgress / 100) * circumference;

  // Get variant color
  const getVariantColor = () => {
    const colors = {
      primary: '#3b82f6',
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444'
    };
    return colors[variant] || colors.primary;
  };

  const cssClasses = [
    'circular-progress-bar',
    `circular-progress-bar--${variant}`,
    animated ? 'circular-progress-bar--animated' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={cssClasses} style={{ width: size, height: size, ...style }}>
      <svg
        width={size}
        height={size}
        className="circular-progress-bar__svg"
      >
        {/* Background Circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          fill="none"
          className="circular-progress-bar__background"
        />
        
        {/* Progress Circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={getVariantColor()}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="circular-progress-bar__progress"
          style={{
            transform: 'rotate(-90deg)',
            transformOrigin: `${size / 2}px ${size / 2}px`
          }}
        />
      </svg>
      
      {/* Center Content */}
      <div className="circular-progress-bar__content">
        {showPercentage && (
          <div className="circular-progress-bar__percentage">
            {Math.round(displayProgress)}%
          </div>
        )}
        {label && (
          <div className="circular-progress-bar__label">
            {label}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Step Progress Bar Component
 * @param {Object} props - Component props
 * @returns {JSX.Element} - Step progress bar component
 */
export const StepProgressBar = ({
  steps = [],
  currentStep = 0,
  variant = 'primary',
  animated = true,
  className = '',
  style = {}
}) => {
  const [displayStep, setDisplayStep] = useState(0);

  useEffect(() => {
    if (!animated) {
      setDisplayStep(currentStep);
      return;
    }

    const duration = 300;
    const startTime = Date.now();
    const startStep = displayStep;

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progressRatio = Math.min(elapsed / duration, 1);
      
      const easedProgress = easeOutCubic(progressRatio);
      const currentStepValue = startStep + (currentStep - startStep) * easedProgress;
      
      setDisplayStep(currentStepValue);
      
      if (progressRatio < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [currentStep, animated, displayStep]);

  const easeOutCubic = (t) => {
    return 1 - Math.pow(1 - t, 3);
  };

  const cssClasses = [
    'step-progress-bar',
    `step-progress-bar--${variant}`,
    animated ? 'step-progress-bar--animated' : '',
    className
  ].filter(Boolean).join(' ');

  return (
    <div className={cssClasses} style={style}>
      {steps.map((step, index) => {
        const isCompleted = index < displayStep;
        const isCurrent = index === Math.floor(displayStep);
        const isPending = index > displayStep;

        return (
          <div
            key={index}
            className={[
              'step-progress-bar__step',
              isCompleted ? 'step-progress-bar__step--completed' : '',
              isCurrent ? 'step-progress-bar__step--current' : '',
              isPending ? 'step-progress-bar__step--pending' : ''
            ].filter(Boolean).join(' ')}
          >
            <div className="step-progress-bar__step-indicator">
              {isCompleted ? (
                <span className="step-progress-bar__checkmark">✓</span>
              ) : (
                <span className="step-progress-bar__number">{index + 1}</span>
              )}
            </div>
            <div className="step-progress-bar__step-content">
              <div className="step-progress-bar__step-label">{step.label}</div>
              {step.description && (
                <div className="step-progress-bar__step-description">
                  {step.description}
                </div>
              )}
            </div>
            {index < steps.length - 1 && (
              <div className="step-progress-bar__connector" />
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ProgressBar;
