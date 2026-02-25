#!/usr/bin/env python3
"""
Training Service Orchestration
High-level service for coordinating model training, validation, and deployment workflows
"""

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

from mlflow_integration.client import mlflow_client
from mlflow_integration.model_registry import model_registry
from services.s3_data_lake import s3_data_lake
from training.ensemble_trainer import EnsembleTrainer, train_ensemble_model
from validation.model_validator import ModelValidator
from automation.retraining_pipeline import RetrainingPipeline
from database.models.ml_model_version import (
    MLModelVersion, TrainingJob, ModelStatus, TrainingStatus, ModelType
)

logger = logging.getLogger(__name__)


class TrainingWorkflowStatus(Enum):
    """Training workflow status."""
    INITIALIZED = "initialized"
    DATA_LOADING = "data_loading"
    TRAINING = "training"
    VALIDATION = "validation"
    REGISTRATION = "registration"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"
    FAILED = "failed"


class TrainingService:
    """
    High-level training service orchestrator.
    Coordinates the entire model training workflow from data loading to deployment.
    """
    
    def __init__(
        self,
        validation_threshold: float = 0.95,
        auto_deploy: bool = False,
        enable_retraining: bool = True
    ):
        """
        Initialize training service.
        
        Args:
            validation_threshold: Model validation threshold
            auto_deploy: Whether to auto-deploy validated models
            enable_retraining: Whether to enable automated retraining
        """
        self.validation_threshold = validation_threshold
        self.auto_deploy = auto_deploy
        self.enable_retraining = enable_retraining
        
        # Initialize components
        self.validator = ModelValidator(validation_threshold)
        self.retraining_pipeline = RetrainingPipeline(auto_deploy=auto_deploy) if enable_retraining else None
        
        logger.info("Training service initialized")
    
    async def train_model(
        self,
        dataset_path: str,
        model_type: str = "ensemble",
        hyperparameters: Optional[Dict[str, Any]] = None,
        job_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train a new model with full workflow orchestration.
        
        Args:
            dataset_path: S3 path to training dataset
            model_type: Type of model to train
            hyperparameters: Training hyperparameters
            job_name: Training job name
            description: Model description
            
        Returns:
            Training workflow results
        """
        try:
            logger.info(f"Starting training workflow for {model_type} model")
            
            # Initialize workflow
            workflow_id = str(uuid.uuid4())
            workflow_status = TrainingWorkflowStatus.INITIALIZED
            
            # Create training job record
            job_id = uuid.uuid4()
            training_job = TrainingJob(
                id=job_id,
                job_name=job_name or f"training-{model_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                model_type=ModelType(model_type),
                dataset_path=dataset_path,
                hyperparameters=hyperparameters,
                validation_threshold=self.validation_threshold,
                status=TrainingStatus.PENDING
            )
            
            # TODO: Save to database
            # await database.save(training_job)
            
            workflow_results = {
                'workflow_id': workflow_id,
                'job_id': str(job_id),
                'status': workflow_status.value,
                'stages': {},
                'start_time': datetime.now(timezone.utc).isoformat(),
                'model_type': model_type,
                'dataset_path': dataset_path
            }
            
            # Stage 1: Data Loading and Validation
            logger.info("Stage 1: Loading and validating training data")
            workflow_status = TrainingWorkflowStatus.DATA_LOADING
            
            data_results = await self._load_and_validate_data(dataset_path)
            workflow_results['stages']['data_loading'] = data_results
            
            if not data_results['success']:
                workflow_results['status'] = TrainingWorkflowStatus.FAILED.value
                workflow_results['error'] = data_results['error']
                return workflow_results
            
            # Stage 2: Model Training
            logger.info("Stage 2: Training model")
            workflow_status = TrainingWorkflowStatus.TRAINING
            
            training_results = await self._train_model(
                data_results['data'], model_type, hyperparameters, job_id
            )
            workflow_results['stages']['training'] = training_results
            
            if not training_results['success']:
                workflow_results['status'] = TrainingWorkflowStatus.FAILED.value
                workflow_results['error'] = training_results['error']
                return workflow_results
            
            # Stage 3: Model Validation
            logger.info("Stage 3: Validating model performance")
            workflow_status = TrainingWorkflowStatus.VALIDATION
            
            validation_results = await self._validate_model(
                training_results['model'], data_results['data'], model_type
            )
            workflow_results['stages']['validation'] = validation_results
            
            if not validation_results['success']:
                workflow_results['status'] = TrainingWorkflowStatus.FAILED.value
                workflow_results['error'] = validation_results['error']
                return workflow_results
            
            # Stage 4: Model Registration
            logger.info("Stage 4: Registering model")
            workflow_status = TrainingWorkflowStatus.REGISTRATION
            
            registration_results = await self._register_model(
                training_results['model'], validation_results['metrics'],
                model_type, job_id, description
            )
            workflow_results['stages']['registration'] = registration_results
            
            if not registration_results['success']:
                workflow_results['status'] = TrainingWorkflowStatus.FAILED.value
                workflow_results['error'] = registration_results['error']
                return workflow_results
            
            # Stage 5: Model Deployment (if auto-deploy enabled)
            if self.auto_deploy and validation_results['is_valid']:
                logger.info("Stage 5: Deploying model")
                workflow_status = TrainingWorkflowStatus.DEPLOYMENT
                
                deployment_results = await self._deploy_model(
                    registration_results['model_name'],
                    registration_results['model_version']
                )
                workflow_results['stages']['deployment'] = deployment_results
                
                if not deployment_results['success']:
                    logger.warning(f"Deployment failed: {deployment_results['error']}")
                    # Don't fail the entire workflow for deployment issues
            
            # Complete workflow
            workflow_status = TrainingWorkflowStatus.COMPLETED
            workflow_results['status'] = workflow_status.value
            workflow_results['end_time'] = datetime.now(timezone.utc).isoformat()
            workflow_results['model_name'] = registration_results.get('model_name')
            workflow_results['model_version'] = registration_results.get('model_version')
            workflow_results['validation_passed'] = validation_results['is_valid']
            
            # Update training job status
            # TODO: Update database
            # await database.update_training_job_status(job_id, TrainingStatus.COMPLETED)
            
            logger.info(f"Training workflow completed successfully: {workflow_id}")
            return workflow_results
            
        except Exception as e:
            logger.error(f"Training workflow failed: {str(e)}")
            return {
                'workflow_id': workflow_id,
                'job_id': str(job_id),
                'status': TrainingWorkflowStatus.FAILED.value,
                'error': str(e),
                'end_time': datetime.now(timezone.utc).isoformat()
            }
    
    async def _load_and_validate_data(self, dataset_path: str) -> Dict[str, Any]:
        """
        Load and validate training data.
        
        Args:
            dataset_path: S3 dataset path
            
        Returns:
            Data loading results
        """
        try:
            # Validate dataset path
            if not s3_data_lake.validate_dataset_path(dataset_path):
                return {
                    'success': False,
                    'error': f'Dataset path not accessible: {dataset_path}'
                }
            
            # Load training data
            training_data = s3_data_lake.load_training_data(dataset_path)
            
            # Validate data quality
            validation_results = s3_data_lake.validate_training_data(
                training_data['data'],
                required_columns=['features', 'labels'],  # Adjust based on actual structure
                min_rows=100
            )
            
            if not validation_results['is_valid']:
                return {
                    'success': False,
                    'error': f'Data validation failed: {validation_results["errors"]}'
                }
            
            return {
                'success': True,
                'data': training_data['data'],
                'data_info': {
                    'rows': training_data['rows'],
                    'columns': training_data['columns'],
                    'format': training_data['format'],
                    'memory_usage_mb': training_data['memory_usage_mb']
                },
                'validation_results': validation_results
            }
            
        except Exception as e:
            logger.error(f"Error loading and validating data: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _train_model(
        self,
        data: pd.DataFrame,
        model_type: str,
        hyperparameters: Optional[Dict[str, Any]],
        job_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Train the model.
        
        Args:
            data: Training data
            model_type: Model type
            hyperparameters: Training hyperparameters
            job_id: Training job ID
            
        Returns:
            Training results
        """
        try:
            # Start MLflow run
            run_id = mlflow_client.start_run(
                run_name=f"training-{model_type}-{job_id}",
                tags={
                    'job_id': str(job_id),
                    'model_type': model_type
                }
            )
            
            # Log hyperparameters
            mlflow_client.log_parameters(hyperparameters or {})
            
            # Prepare training data
            feature_columns = [col for col in data.columns if col != 'labels']
            label_column = 'labels'
            
            # Train model
            trainer, training_results = train_ensemble_model(
                data, feature_columns, label_column, hyperparameters
            )
            
            # Log training metrics
            mlflow_client.log_metrics({
                'best_val_accuracy': training_results['best_val_accuracy'],
                'final_train_loss': training_results['final_train_loss'],
                'final_train_accuracy': training_results['final_train_accuracy'],
                'final_val_loss': training_results['final_val_loss'],
                'final_val_accuracy': training_results['final_val_accuracy']
            })
            
            return {
                'success': True,
                'model': trainer,
                'training_results': training_results,
                'mlflow_run_id': run_id,
                'feature_columns': feature_columns,
                'label_column': label_column
            }
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            mlflow_client.end_run(status="FAILED")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _validate_model(
        self,
        model,
        data: pd.DataFrame,
        model_type: str
    ) -> Dict[str, Any]:
        """
        Validate model performance.
        
        Args:
            model: Trained model
            data: Training data
            model_type: Model type
            
        Returns:
            Validation results
        """
        try:
            # Prepare validation data (use a subset for validation)
            feature_columns = [col for col in data.columns if col != 'labels']
            label_column = 'labels'
            
            # Split data for validation
            from sklearn.model_selection import train_test_split
            X = data[feature_columns].values
            y = data[label_column].values
            
            _, X_val, _, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Create validation dataset
            val_data = pd.DataFrame(X_val, columns=feature_columns)
            val_data[label_column] = y_val
            
            # Validate model
            validation_results = self.validator.validate_model_performance(
                model, val_data, feature_columns, label_column, model_type
            )
            
            # Log validation metrics to MLflow
            mlflow_client.log_metrics(validation_results['metrics'])
            
            return {
                'success': True,
                'is_valid': validation_results['is_valid'],
                'metrics': validation_results['metrics'],
                'validation_results': validation_results
            }
            
        except Exception as e:
            logger.error(f"Error validating model: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _register_model(
        self,
        model,
        metrics: Dict[str, float],
        model_type: str,
        job_id: uuid.UUID,
        description: Optional[str]
    ) -> Dict[str, Any]:
        """
        Register model in MLflow model registry.
        
        Args:
            model: Trained model
            metrics: Validation metrics
            model_type: Model type
            job_id: Training job ID
            description: Model description
            
        Returns:
            Registration results
        """
        try:
            # Log model to MLflow
            model_uri = mlflow_client.log_model(
                model, f"{model_type}_model", model_type="pytorch"
            )
            
            # Register model
            model_name = f"deepfake-detection-{model_type}"
            model_version = model_registry.register_model_version(
                model_name, model_uri, mlflow_client.get_run().info.run_id,
                description=description or f"{model_type} model trained on {datetime.now().strftime('%Y-%m-%d')}",
                tags={
                    'job_id': str(job_id),
                    'auc_score': str(metrics.get('auc_score', 0)),
                    'validation_threshold': str(self.validation_threshold)
                }
            )
            
            # Create MLModelVersion database record
            model_version_record = MLModelVersion(
                model_name=model_name,
                version=model_version,
                model_type=ModelType(model_type),
                mlflow_run_id=mlflow_client.get_run().info.run_id,
                mlflow_model_uri=model_uri,
                training_job_id=job_id,
                hyperparameters={},  # TODO: Get from training job
                auc_score=metrics.get('auc_score'),
                accuracy=metrics.get('accuracy'),
                precision=metrics.get('precision'),
                recall=metrics.get('recall'),
                f1_score=metrics.get('f1_score'),
                validation_threshold=self.validation_threshold,
                status=ModelStatus.VALIDATED,
                description=description
            )
            
            # TODO: Save to database
            # await database.save(model_version_record)
            
            return {
                'success': True,
                'model_name': model_name,
                'model_version': model_version,
                'model_uri': model_uri,
                'model_version_record': model_version_record
            }
            
        except Exception as e:
            logger.error(f"Error registering model: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _deploy_model(
        self,
        model_name: str,
        model_version: str
    ) -> Dict[str, Any]:
        """
        Deploy model to production.
        
        Args:
            model_name: Model name
            model_version: Model version
            
        Returns:
            Deployment results
        """
        try:
            # Deploy model
            success = model_registry.deploy_model(
                model_name, model_version, "Production",
                f"Auto-deployed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            if not success:
                return {
                    'success': False,
                    'error': 'Model deployment failed'
                }
            
            return {
                'success': True,
                'model_name': model_name,
                'model_version': model_version,
                'stage': 'Production',
                'deployed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error deploying model: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get training job status.
        
        Args:
            job_id: Training job ID
            
        Returns:
            Job status information
        """
        try:
            # TODO: Get from database
            # training_job = await database.get(TrainingJob, uuid.UUID(job_id))
            
            # Mock response for now
            return {
                'job_id': job_id,
                'status': TrainingStatus.RUNNING.value,
                'progress_percentage': 75.0,
                'current_stage': 'validation',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'message': 'Training in progress'
            }
            
        except Exception as e:
            logger.error(f"Error getting training status: {str(e)}")
            return {
                'job_id': job_id,
                'status': TrainingStatus.FAILED.value,
                'error': str(e)
            }
    
    async def list_trained_models(
        self,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        List trained models.
        
        Args:
            model_type: Filter by model type
            status: Filter by status
            limit: Maximum number of results
            
        Returns:
            List of trained models
        """
        try:
            # TODO: Query database
            # models = await database.query_model_versions(
            #     model_type=model_type, status=status, limit=limit
            # )
            
            # Mock response for now
            return {
                'models': [],
                'total_count': 0,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Error listing trained models: {str(e)}")
            return {
                'models': [],
                'total_count': 0,
                'error': str(e)
            }


# Global training service instance
training_service = TrainingService()


# Utility functions for easy access
async def train_new_model(
    dataset_path: str,
    model_type: str = "ensemble",
    hyperparameters: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Train a new model."""
    return await training_service.train_model(
        dataset_path, model_type, hyperparameters, **kwargs
    )


async def get_training_job_status(job_id: str) -> Dict[str, Any]:
    """Get training job status."""
    return await training_service.get_training_status(job_id)


async def list_available_models(**kwargs) -> Dict[str, Any]:
    """List available trained models."""
    return await training_service.list_trained_models(**kwargs)


# Export
__all__ = [
    'TrainingWorkflowStatus',
    'TrainingService',
    'training_service',
    'train_new_model',
    'get_training_job_status',
    'list_available_models'
]
