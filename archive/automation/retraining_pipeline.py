#!/usr/bin/env python3
"""
Automated Retraining Pipeline
Scheduled retraining system with data freshness monitoring and performance degradation detection
"""

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from celery import Celery
from celery.schedules import crontab
import pandas as pd
import numpy as np

from mlflow_integration.client import mlflow_client
from mlflow_integration.model_registry import model_registry
from services.s3_data_lake import s3_data_lake
from database.models.ml_model_version import (
    MLModelVersion, TrainingJob, ModelStatus, TrainingStatus, ModelType
)
from validation.model_validator import ModelValidator

logger = logging.getLogger(__name__)

# Initialize Celery app for retraining
retraining_app = Celery('retraining_pipeline')

# Celery Beat configuration for scheduled tasks
retraining_app.conf.beat_schedule = {
    'check-retraining-triggers': {
        'task': 'check_retraining_triggers',
        'schedule': crontab(minute=0, hour=6),  # Daily at 6 AM
    },
    'monitor-model-performance': {
        'task': 'monitor_model_performance',
        'schedule': crontab(minute=0, hour=0),  # Daily at midnight
    },
    'cleanup-old-models': {
        'task': 'cleanup_old_models',
        'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Weekly on Sunday at 2 AM
    },
}


class RetrainingPipeline:
    """
    Automated retraining pipeline manager.
    """
    
    def __init__(
        self,
        data_freshness_threshold_days: int = 7,
        performance_degradation_threshold: float = 0.05,
        auto_deploy: bool = False,
        max_models_per_type: int = 10
    ):
        """
        Initialize retraining pipeline.
        
        Args:
            data_freshness_threshold_days: Data freshness threshold in days
            performance_degradation_threshold: Performance degradation threshold
            auto_deploy: Whether to auto-deploy validated models
            max_models_per_type: Maximum models to keep per type
        """
        self.data_freshness_threshold_days = data_freshness_threshold_days
        self.performance_degradation_threshold = performance_degradation_threshold
        self.auto_deploy = auto_deploy
        self.max_models_per_type = max_models_per_type
        
        logger.info("Retraining pipeline initialized")
    
    def check_data_freshness(self, dataset_path: str) -> Dict[str, Any]:
        """
        Check if training data is fresh enough.
        
        Args:
            dataset_path: S3 path to training dataset
            
        Returns:
            Data freshness check results
        """
        try:
            logger.info(f"Checking data freshness for {dataset_path}")
            
            # Get dataset info
            dataset_info = s3_data_lake.get_dataset_info(dataset_path)
            
            if not dataset_info:
                return {
                    'is_fresh': False,
                    'reason': 'Dataset not accessible',
                    'last_modified': None,
                    'days_since_update': None
                }
            
            last_modified = dataset_info.get('last_modified')
            if not last_modified:
                return {
                    'is_fresh': False,
                    'reason': 'Last modified date not available',
                    'last_modified': None,
                    'days_since_update': None
                }
            
            # Calculate days since last update
            if isinstance(last_modified, str):
                last_modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            
            days_since_update = (datetime.now(timezone.utc) - last_modified).days
            
            is_fresh = days_since_update <= self.data_freshness_threshold_days
            
            return {
                'is_fresh': is_fresh,
                'reason': f"Data is {'fresh' if is_fresh else 'stale'}",
                'last_modified': last_modified.isoformat(),
                'days_since_update': days_since_update,
                'threshold_days': self.data_freshness_threshold_days
            }
            
        except Exception as e:
            logger.error(f"Error checking data freshness: {str(e)}")
            return {
                'is_fresh': False,
                'reason': f'Error: {str(e)}',
                'last_modified': None,
                'days_since_update': None
            }
    
    def check_performance_degradation(
        self,
        model_name: str,
        current_metrics: Dict[str, float],
        baseline_metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Check if model performance has degraded.
        
        Args:
            model_name: Model name
            current_metrics: Current performance metrics
            baseline_metrics: Baseline performance metrics
            
        Returns:
            Performance degradation check results
        """
        try:
            logger.info(f"Checking performance degradation for {model_name}")
            
            # Get baseline metrics if not provided
            if baseline_metrics is None:
                baseline_metrics = self._get_baseline_metrics(model_name)
            
            if not baseline_metrics:
                return {
                    'has_degraded': False,
                    'reason': 'No baseline metrics available',
                    'current_auc': current_metrics.get('auc_score', 0),
                    'baseline_auc': None,
                    'degradation': None
                }
            
            current_auc = current_metrics.get('auc_score', 0)
            baseline_auc = baseline_metrics.get('auc_score', 0)
            
            degradation = baseline_auc - current_auc
            has_degraded = degradation > self.performance_degradation_threshold
            
            return {
                'has_degraded': has_degraded,
                'reason': f"Performance {'degraded' if has_degraded else 'stable'}",
                'current_auc': current_auc,
                'baseline_auc': baseline_auc,
                'degradation': degradation,
                'threshold': self.performance_degradation_threshold
            }
            
        except Exception as e:
            logger.error(f"Error checking performance degradation: {str(e)}")
            return {
                'has_degraded': False,
                'reason': f'Error: {str(e)}',
                'current_auc': current_metrics.get('auc_score', 0),
                'baseline_auc': None,
                'degradation': None
            }
    
    def _get_baseline_metrics(self, model_name: str) -> Optional[Dict[str, float]]:
        """
        Get baseline performance metrics for a model.
        
        Args:
            model_name: Model name
            
        Returns:
            Baseline metrics dictionary
        """
        try:
            # Get latest production model
            latest_model = model_registry.get_latest_model_version(model_name, "Production")
            
            if not latest_model:
                return None
            
            # Get metrics from MLflow run
            run_id = latest_model.get('run_id')
            if run_id:
                metrics = mlflow_client.get_run_metrics(run_id)
                return metrics
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting baseline metrics: {str(e)}")
            return None
    
    def should_retrain(
        self,
        model_name: str,
        dataset_path: str,
        current_metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Determine if model should be retrained.
        
        Args:
            model_name: Model name
            dataset_path: Training dataset path
            current_metrics: Current performance metrics
            
        Returns:
            Retraining decision results
        """
        try:
            logger.info(f"Evaluating retraining need for {model_name}")
            
            retraining_decision = {
                'should_retrain': False,
                'reasons': [],
                'data_freshness': {},
                'performance_degradation': {},
                'recommendation': 'No retraining needed'
            }
            
            # Check data freshness
            data_freshness = self.check_data_freshness(dataset_path)
            retraining_decision['data_freshness'] = data_freshness
            
            if not data_freshness['is_fresh']:
                retraining_decision['should_retrain'] = True
                retraining_decision['reasons'].append('Data is stale')
            
            # Check performance degradation
            if current_metrics:
                performance_degradation = self.check_performance_degradation(
                    model_name, current_metrics
                )
                retraining_decision['performance_degradation'] = performance_degradation
                
                if performance_degradation['has_degraded']:
                    retraining_decision['should_retrain'] = True
                    retraining_decision['reasons'].append('Performance degraded')
            
            # Set recommendation
            if retraining_decision['should_retrain']:
                retraining_decision['recommendation'] = 'Retraining recommended'
            else:
                retraining_decision['recommendation'] = 'No retraining needed'
            
            logger.info(f"Retraining decision for {model_name}: {retraining_decision['recommendation']}")
            return retraining_decision
            
        except Exception as e:
            logger.error(f"Error evaluating retraining need: {str(e)}")
            return {
                'should_retrain': False,
                'reasons': [f'Error: {str(e)}'],
                'recommendation': 'Error in evaluation'
            }
    
    def trigger_retraining(
        self,
        model_name: str,
        dataset_path: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
        validation_threshold: float = 0.95
    ) -> Dict[str, Any]:
        """
        Trigger model retraining.
        
        Args:
            model_name: Model name
            dataset_path: Training dataset path
            hyperparameters: Training hyperparameters
            validation_threshold: Validation threshold
            
        Returns:
            Retraining trigger results
        """
        try:
            logger.info(f"Triggering retraining for {model_name}")
            
            # Create new training job
            job_id = uuid.uuid4()
            job_name = f"retraining-{model_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Start Celery training task
            from celery_app.training_tasks import train_ensemble_model_task
            
            task_result = train_ensemble_model_task.delay(
                job_id=str(job_id),
                dataset_path=dataset_path,
                model_type='ensemble',  # Default to ensemble
                hyperparameters=hyperparameters or {},
                validation_threshold=validation_threshold,
                job_name=job_name
            )
            
            # Create training job record
            training_job = TrainingJob(
                id=job_id,
                job_name=job_name,
                model_type=ModelType.ENSEMBLE,
                dataset_path=dataset_path,
                hyperparameters=hyperparameters,
                validation_threshold=validation_threshold,
                status=TrainingStatus.RUNNING,
                celery_task_id=task_result.id
            )
            
            # TODO: Save to database
            # await database.save(training_job)
            
            logger.info(f"Retraining triggered for {model_name}: job {job_id}")
            
            return {
                'status': 'triggered',
                'job_id': str(job_id),
                'task_id': task_result.id,
                'model_name': model_name,
                'job_name': job_name,
                'message': 'Retraining job started successfully'
            }
            
        except Exception as e:
            logger.error(f"Error triggering retraining: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'message': 'Failed to trigger retraining'
            }
    
    def cleanup_old_models(self, model_name: str) -> Dict[str, Any]:
        """
        Clean up old model versions.
        
        Args:
            model_name: Model name
            
        Returns:
            Cleanup results
        """
        try:
            logger.info(f"Cleaning up old models for {model_name}")
            
            # Get all model versions
            model_versions = model_registry.get_model_versions(model_name)
            
            if len(model_versions) <= self.max_models_per_type:
                return {
                    'status': 'no_cleanup_needed',
                    'current_count': len(model_versions),
                    'max_count': self.max_models_per_type,
                    'message': 'No cleanup needed'
                }
            
            # Sort by creation timestamp (oldest first)
            sorted_versions = sorted(
                model_versions,
                key=lambda x: x.get('creation_timestamp', ''),
                reverse=False
            )
            
            # Archive old models
            models_to_archive = sorted_versions[:-self.max_models_per_type]
            archived_count = 0
            
            for model_version in models_to_archive:
                version = model_version.get('version')
                stage = model_version.get('stage', 'None')
                
                # Only archive non-production models
                if stage != 'Production':
                    success = model_registry.archive_model(
                        model_name, version, "Automated cleanup"
                    )
                    if success:
                        archived_count += 1
            
            logger.info(f"Cleaned up {archived_count} old models for {model_name}")
            
            return {
                'status': 'completed',
                'archived_count': archived_count,
                'remaining_count': len(model_versions) - archived_count,
                'max_count': self.max_models_per_type,
                'message': f'Archived {archived_count} old models'
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up old models: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'message': 'Failed to cleanup old models'
            }


# Celery tasks for automated retraining

@retraining_app.task(name='check_retraining_triggers')
def check_retraining_triggers():
    """
    Check all models for retraining triggers.
    """
    try:
        logger.info("Checking retraining triggers for all models")
        
        # Get all registered models
        models = model_registry.search_models()
        
        retraining_pipeline = RetrainingPipeline()
        triggered_jobs = []
        
        for model_info in models:
            model_name = model_info['name']
            
            # Skip if not a deepfake detection model
            if 'deepfake-detection' not in model_name:
                continue
            
            # Get latest production model
            latest_model = model_registry.get_latest_model_version(model_name, "Production")
            
            if not latest_model:
                logger.warning(f"No production model found for {model_name}")
                continue
            
            # Get training data path
            training_data_path = latest_model.get('training_data_s3_path')
            if not training_data_path:
                logger.warning(f"No training data path found for {model_name}")
                continue
            
            # Evaluate retraining need
            retraining_decision = retraining_pipeline.should_retrain(
                model_name, training_data_path
            )
            
            if retraining_decision['should_retrain']:
                logger.info(f"Retraining triggered for {model_name}: {retraining_decision['reasons']}")
                
                # Trigger retraining
                retraining_result = retraining_pipeline.trigger_retraining(
                    model_name, training_data_path
                )
                
                triggered_jobs.append({
                    'model_name': model_name,
                    'job_id': retraining_result.get('job_id'),
                    'reasons': retraining_decision['reasons']
                })
        
        logger.info(f"Retraining check completed. Triggered {len(triggered_jobs)} jobs")
        return {
            'status': 'completed',
            'triggered_jobs': triggered_jobs,
            'total_models_checked': len(models)
        }
        
    except Exception as e:
        logger.error(f"Error checking retraining triggers: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


@retraining_app.task(name='monitor_model_performance')
def monitor_model_performance():
    """
    Monitor model performance and detect degradation.
    """
    try:
        logger.info("Monitoring model performance")
        
        # TODO: Implement performance monitoring
        # This would involve:
        # 1. Running models on recent test data
        # 2. Comparing performance to baseline
        # 3. Alerting on significant degradation
        
        logger.info("Model performance monitoring completed")
        return {
            'status': 'completed',
            'message': 'Performance monitoring completed'
        }
        
    except Exception as e:
        logger.error(f"Error monitoring model performance: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


@retraining_app.task(name='cleanup_old_models')
def cleanup_old_models():
    """
    Clean up old model versions.
    """
    try:
        logger.info("Cleaning up old model versions")
        
        retraining_pipeline = RetrainingPipeline()
        cleanup_results = []
        
        # Get all registered models
        models = model_registry.search_models()
        
        for model_info in models:
            model_name = model_info['name']
            
            # Skip if not a deepfake detection model
            if 'deepfake-detection' not in model_name:
                continue
            
            # Cleanup old models
            cleanup_result = retraining_pipeline.cleanup_old_models(model_name)
            cleanup_results.append({
                'model_name': model_name,
                'result': cleanup_result
            })
        
        logger.info("Model cleanup completed")
        return {
            'status': 'completed',
            'cleanup_results': cleanup_results
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old models: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }


# Utility functions for easy access
def create_retraining_pipeline(**kwargs) -> RetrainingPipeline:
    """Create retraining pipeline instance."""
    return RetrainingPipeline(**kwargs)


def check_model_retraining_need(
    model_name: str,
    dataset_path: str,
    current_metrics: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Check if model needs retraining."""
    pipeline = RetrainingPipeline()
    return pipeline.should_retrain(model_name, dataset_path, current_metrics)


def trigger_model_retraining(
    model_name: str,
    dataset_path: str,
    hyperparameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Trigger model retraining."""
    pipeline = RetrainingPipeline()
    return pipeline.trigger_retraining(model_name, dataset_path, hyperparameters)


# Export
__all__ = [
    'RetrainingPipeline',
    'retraining_app',
    'check_retraining_triggers',
    'monitor_model_performance',
    'cleanup_old_models',
    'create_retraining_pipeline',
    'check_model_retraining_need',
    'trigger_model_retraining'
]
