#!/usr/bin/env python3
"""
MLflow Model Registry
Model registration, versioning, and deployment management for trained models
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from enum import Enum
import mlflow
from mlflow.tracking import MlflowClient
from mlflow.exceptions import MlflowException
import json

logger = logging.getLogger(__name__)


class ModelStage(Enum):
    """Model deployment stages."""
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class ModelStatus(Enum):
    """Model validation status."""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    DEPLOYED = "deployed"


class ModelRegistry:
    """
    MLflow model registry manager for model versioning and deployment.
    Handles model registration, validation, and stage transitions.
    """
    
    def __init__(self, client: MlflowClient):
        """
        Initialize model registry.
        
        Args:
            client: MLflow client instance
        """
        self.client = client
        self.default_model_name = "deepfake-detection-ensemble"
        
        logger.info("Model registry initialized")
    
    def create_model(
        self,
        model_name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a new registered model.
        
        Args:
            model_name: Name of the model
            description: Model description
            tags: Model tags
            
        Returns:
            Model name
        """
        try:
            # Create registered model
            self.client.create_registered_model(
                name=model_name,
                description=description,
                tags=tags
            )
            
            logger.info(f"Created registered model: {model_name}")
            return model_name
            
        except MlflowException as e:
            if "already exists" in str(e):
                logger.info(f"Model {model_name} already exists")
                return model_name
            else:
                logger.error(f"Error creating model: {str(e)}")
                raise
    
    def register_model_version(
        self,
        model_name: str,
        model_uri: str,
        run_id: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Register a new model version.
        
        Args:
            model_name: Name of the model
            model_uri: URI of the model artifact
            run_id: MLflow run ID
            description: Version description
            tags: Version tags
            
        Returns:
            Model version
        """
        try:
            # Create model if it doesn't exist
            self.create_model(model_name)
            
            # Register model version
            model_version = self.client.create_model_version(
                name=model_name,
                source=model_uri,
                run_id=run_id,
                description=description,
                tags=tags
            )
            
            logger.info(f"Registered model version: {model_name} v{model_version.version}")
            return model_version.version
            
        except MlflowException as e:
            logger.error(f"Error registering model version: {str(e)}")
            raise
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a registered model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model information dictionary or None if not found
        """
        try:
            model = self.client.get_registered_model(model_name)
            
            return {
                'name': model.name,
                'description': model.description,
                'tags': {tag.key: tag.value for tag in model.tags},
                'creation_timestamp': model.creation_timestamp,
                'last_updated_timestamp': model.last_updated_timestamp,
                'latest_versions': [
                    {
                        'version': version.version,
                        'stage': version.current_stage,
                        'description': version.description,
                        'creation_timestamp': version.creation_timestamp,
                        'last_updated_timestamp': version.last_updated_timestamp
                    }
                    for version in model.latest_versions
                ]
            }
            
        except MlflowException as e:
            logger.error(f"Error getting model info: {str(e)}")
            return None
    
    def get_model_version_info(
        self,
        model_name: str,
        version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model version.
        
        Args:
            model_name: Name of the model
            version: Model version
            
        Returns:
            Model version information dictionary or None if not found
        """
        try:
            model_version = self.client.get_model_version(model_name, version)
            
            return {
                'name': model_version.name,
                'version': model_version.version,
                'stage': model_version.current_stage,
                'description': model_version.description,
                'source': model_version.source,
                'run_id': model_version.run_id,
                'status': model_version.status,
                'creation_timestamp': model_version.creation_timestamp,
                'last_updated_timestamp': model_version.last_updated_timestamp,
                'tags': {tag.key: tag.value for tag in model_version.tags}
            }
            
        except MlflowException as e:
            logger.error(f"Error getting model version info: {str(e)}")
            return None
    
    def get_latest_model_version(
        self,
        model_name: str,
        stage: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest model version.
        
        Args:
            model_name: Name of the model
            stage: Specific stage (if None, gets latest regardless of stage)
            
        Returns:
            Latest model version information or None if not found
        """
        try:
            if stage:
                versions = self.client.get_latest_versions(model_name, stages=[stage])
            else:
                versions = self.client.get_latest_versions(model_name)
            
            if not versions:
                return None
            
            # Get the latest version
            latest_version = versions[0]
            return self.get_model_version_info(model_name, latest_version.version)
            
        except MlflowException as e:
            logger.error(f"Error getting latest model version: {str(e)}")
            return None
    
    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str,
        description: Optional[str] = None
    ) -> bool:
        """
        Transition model to a specific stage.
        
        Args:
            model_name: Name of the model
            version: Model version
            stage: Target stage
            description: Transition description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                description=description
            )
            
            logger.info(f"Transitioned {model_name} v{version} to {stage}")
            return True
            
        except MlflowException as e:
            logger.error(f"Error transitioning model stage: {str(e)}")
            return False
    
    def validate_model(
        self,
        model_name: str,
        version: str,
        validation_threshold: float = 0.95,
        metrics: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate model against performance threshold.
        
        Args:
            model_name: Name of the model
            version: Model version
            validation_threshold: AUC threshold for validation
            metrics: Model performance metrics
            
        Returns:
            Tuple of (is_valid, validation_result)
        """
        try:
            # Get model version info
            model_info = self.get_model_version_info(model_name, version)
            if not model_info:
                return False, {'error': 'Model version not found'}
            
            # Get run metrics if not provided
            if not metrics:
                run_id = model_info['run_id']
                run = self.client.get_run(run_id)
                metrics = {metric.key: metric.value for metric in run.data.metrics}
            
            # Check AUC score
            auc_score = metrics.get('auc_score', 0.0)
            is_valid = auc_score >= validation_threshold
            
            validation_result = {
                'model_name': model_name,
                'version': version,
                'auc_score': auc_score,
                'validation_threshold': validation_threshold,
                'is_valid': is_valid,
                'metrics': metrics,
                'validation_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Update model tags with validation result
            tags = {
                'validation_status': 'validated' if is_valid else 'rejected',
                'auc_score': str(auc_score),
                'validation_threshold': str(validation_threshold),
                'validation_timestamp': validation_result['validation_timestamp']
            }
            
            self.client.set_model_version_tag(model_name, version, 'validation_status', tags['validation_status'])
            self.client.set_model_version_tag(model_name, version, 'auc_score', tags['auc_score'])
            self.client.set_model_version_tag(model_name, version, 'validation_threshold', tags['validation_threshold'])
            self.client.set_model_version_tag(model_name, version, 'validation_timestamp', tags['validation_timestamp'])
            
            logger.info(f"Model validation completed: {model_name} v{version} - {'Valid' if is_valid else 'Invalid'}")
            return is_valid, validation_result
            
        except MlflowException as e:
            logger.error(f"Error validating model: {str(e)}")
            return False, {'error': str(e)}
    
    def deploy_model(
        self,
        model_name: str,
        version: str,
        stage: str = "Production",
        description: Optional[str] = None
    ) -> bool:
        """
        Deploy model to production stage.
        
        Args:
            model_name: Name of the model
            version: Model version
            stage: Deployment stage
            description: Deployment description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate model first
            is_valid, validation_result = self.validate_model(model_name, version)
            if not is_valid:
                logger.error(f"Cannot deploy invalid model: {model_name} v{version}")
                return False
            
            # Transition to production stage
            success = self.transition_model_stage(
                model_name, version, stage, description
            )
            
            if success:
                # Update deployment tags
                self.client.set_model_version_tag(
                    model_name, version, 'deployment_status', 'deployed'
                )
                self.client.set_model_version_tag(
                    model_name, version, 'deployment_timestamp',
                    datetime.now(timezone.utc).isoformat()
                )
                
                logger.info(f"Model deployed: {model_name} v{version} to {stage}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deploying model: {str(e)}")
            return False
    
    def archive_model(
        self,
        model_name: str,
        version: str,
        description: Optional[str] = None
    ) -> bool:
        """
        Archive a model version.
        
        Args:
            model_name: Name of the model
            version: Model version
            description: Archive description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.transition_model_stage(
                model_name, version, "Archived", description
            )
            
            if success:
                # Update archive tags
                self.client.set_model_version_tag(
                    model_name, version, 'archive_status', 'archived'
                )
                self.client.set_model_version_tag(
                    model_name, version, 'archive_timestamp',
                    datetime.now(timezone.utc).isoformat()
                )
                
                logger.info(f"Model archived: {model_name} v{version}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error archiving model: {str(e)}")
            return False
    
    def get_model_versions(
        self,
        model_name: str,
        stage: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all versions of a model.
        
        Args:
            model_name: Name of the model
            stage: Filter by stage (if None, gets all versions)
            
        Returns:
            List of model version information
        """
        try:
            if stage:
                versions = self.client.get_latest_versions(model_name, stages=[stage])
            else:
                versions = self.client.get_latest_versions(model_name)
            
            version_info = []
            for version in versions:
                info = self.get_model_version_info(model_name, version.version)
                if info:
                    version_info.append(info)
            
            return version_info
            
        except MlflowException as e:
            logger.error(f"Error getting model versions: {str(e)}")
            return []
    
    def search_models(
        self,
        filter_string: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search registered models.
        
        Args:
            filter_string: Filter string for search
            max_results: Maximum number of results
            
        Returns:
            List of model information
        """
        try:
            models = self.client.search_registered_models(
                filter_string=filter_string,
                max_results=max_results
            )
            
            model_info = []
            for model in models:
                info = self.get_model_info(model.name)
                if info:
                    model_info.append(info)
            
            return model_info
            
        except MlflowException as e:
            logger.error(f"Error searching models: {str(e)}")
            return []
    
    def delete_model_version(
        self,
        model_name: str,
        version: str
    ) -> bool:
        """
        Delete a model version.
        
        Args:
            model_name: Name of the model
            version: Model version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_model_version(model_name, version)
            logger.info(f"Deleted model version: {model_name} v{version}")
            return True
            
        except MlflowException as e:
            logger.error(f"Error deleting model version: {str(e)}")
            return False
    
    def get_model_uri(
        self,
        model_name: str,
        version: Optional[str] = None,
        stage: Optional[str] = None
    ) -> Optional[str]:
        """
        Get model URI for loading.
        
        Args:
            model_name: Name of the model
            version: Specific version (if None, gets latest)
            stage: Specific stage (if None, gets latest regardless of stage)
            
        Returns:
            Model URI or None if not found
        """
        try:
            if version:
                model_info = self.get_model_version_info(model_name, version)
                return model_info['source'] if model_info else None
            else:
                model_info = self.get_latest_model_version(model_name, stage)
                return model_info['source'] if model_info else None
                
        except Exception as e:
            logger.error(f"Error getting model URI: {str(e)}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check model registry health.
        
        Returns:
            Health status information
        """
        try:
            # Try to search models
            models = self.search_models(max_results=1)
            
            return {
                'status': 'healthy',
                'total_models': len(models),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Global model registry instance
model_registry = ModelRegistry(mlflow_client.client)


# Utility functions for easy access
def register_model_version(
    model_name: str,
    model_uri: str,
    run_id: str,
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> str:
    """Register a new model version."""
    return model_registry.register_model_version(model_name, model_uri, run_id, description, tags)


def validate_model_performance(
    model_name: str,
    version: str,
    validation_threshold: float = 0.95,
    metrics: Optional[Dict[str, float]] = None
) -> Tuple[bool, Dict[str, Any]]:
    """Validate model against performance threshold."""
    return model_registry.validate_model(model_name, version, validation_threshold, metrics)


def deploy_model_to_production(
    model_name: str,
    version: str,
    description: Optional[str] = None
) -> bool:
    """Deploy model to production."""
    return model_registry.deploy_model(model_name, version, "Production", description)


def get_latest_production_model(model_name: str) -> Optional[Dict[str, Any]]:
    """Get latest production model."""
    return model_registry.get_latest_model_version(model_name, "Production")


# Export
__all__ = [
    'ModelStage',
    'ModelStatus',
    'ModelRegistry',
    'model_registry',
    'register_model_version',
    'validate_model_performance',
    'deploy_model_to_production',
    'get_latest_production_model'
]
