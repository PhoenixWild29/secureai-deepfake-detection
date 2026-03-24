#!/usr/bin/env python3
"""
MLflow Integration Client
MLflow client configuration and experiment tracking for model training pipeline
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
import mlflow
import mlflow.sklearn
import mlflow.pytorch
import mlflow.tensorflow
from mlflow.tracking import MlflowClient
from mlflow.entities import Run, Experiment
from mlflow.exceptions import MlflowException
import json
import uuid

logger = logging.getLogger(__name__)


class MLflowClientManager:
    """
    MLflow client manager for experiment tracking and model registry.
    Handles experiment creation, run management, and model registration.
    """
    
    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        registry_uri: Optional[str] = None,
        experiment_name: str = "deepfake-detection-training"
    ):
        """
        Initialize MLflow client manager.
        
        Args:
            tracking_uri: MLflow tracking server URI
            registry_uri: MLflow model registry URI
            experiment_name: Default experiment name
        """
        self.tracking_uri = tracking_uri or os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        self.registry_uri = registry_uri or os.getenv('MLFLOW_REGISTRY_URI', self.tracking_uri)
        self.experiment_name = experiment_name
        
        # Configure MLflow
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_registry_uri(self.registry_uri)
        
        # Initialize client
        self.client = MlflowClient(tracking_uri=self.tracking_uri)
        
        # Get or create experiment
        self.experiment_id = self._get_or_create_experiment()
        
        logger.info(f"MLflow client initialized: {self.tracking_uri}")
        logger.info(f"Experiment: {self.experiment_name} (ID: {self.experiment_id})")
    
    def _get_or_create_experiment(self) -> str:
        """
        Get or create MLflow experiment.
        
        Returns:
            Experiment ID
        """
        try:
            # Try to get existing experiment
            experiment = self.client.get_experiment_by_name(self.experiment_name)
            if experiment:
                logger.info(f"Using existing experiment: {self.experiment_name}")
                return experiment.experiment_id
            
            # Create new experiment
            experiment_id = self.client.create_experiment(self.experiment_name)
            logger.info(f"Created new experiment: {self.experiment_name} (ID: {experiment_id})")
            return experiment_id
            
        except MlflowException as e:
            logger.error(f"Error managing experiment: {str(e)}")
            raise
    
    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Start a new MLflow run.
        
        Args:
            run_name: Name for the run
            tags: Tags to associate with the run
            description: Description of the run
            
        Returns:
            Run ID
        """
        try:
            # Generate run name if not provided
            if not run_name:
                run_name = f"training-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            
            # Set default tags
            default_tags = {
                'run_type': 'training',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'framework': 'ensemble'
            }
            if tags:
                default_tags.update(tags)
            
            # Start run
            run = mlflow.start_run(
                experiment_id=self.experiment_id,
                run_name=run_name,
                description=description
            )
            
            # Set tags
            mlflow.set_tags(default_tags)
            
            logger.info(f"Started MLflow run: {run_name} (ID: {run.info.run_id})")
            return run.info.run_id
            
        except MlflowException as e:
            logger.error(f"Error starting MLflow run: {str(e)}")
            raise
    
    def end_run(self, status: str = "FINISHED", run_id: Optional[str] = None):
        """
        End the current MLflow run.
        
        Args:
            status: Run status (FINISHED, FAILED, KILLED)
            run_id: Specific run ID to end (if None, ends current run)
        """
        try:
            if run_id:
                # End specific run
                self.client.set_terminated(run_id, status=status)
                logger.info(f"Ended MLflow run: {run_id} with status: {status}")
            else:
                # End current run
                mlflow.end_run(status=status)
                logger.info(f"Ended current MLflow run with status: {status}")
                
        except MlflowException as e:
            logger.error(f"Error ending MLflow run: {str(e)}")
            raise
    
    def log_parameters(self, params: Dict[str, Any], run_id: Optional[str] = None):
        """
        Log parameters to MLflow run.
        
        Args:
            params: Parameters to log
            run_id: Specific run ID (if None, logs to current run)
        """
        try:
            if run_id:
                # Log to specific run
                for key, value in params.items():
                    self.client.log_param(run_id, key, value)
            else:
                # Log to current run
                mlflow.log_params(params)
            
            logger.debug(f"Logged {len(params)} parameters to MLflow")
            
        except MlflowException as e:
            logger.error(f"Error logging parameters: {str(e)}")
            raise
    
    def log_metrics(self, metrics: Dict[str, float], run_id: Optional[str] = None):
        """
        Log metrics to MLflow run.
        
        Args:
            metrics: Metrics to log
            run_id: Specific run ID (if None, logs to current run)
        """
        try:
            if run_id:
                # Log to specific run
                for key, value in metrics.items():
                    self.client.log_metric(run_id, key, value)
            else:
                # Log to current run
                mlflow.log_metrics(metrics)
            
            logger.debug(f"Logged {len(metrics)} metrics to MLflow")
            
        except MlflowException as e:
            logger.error(f"Error logging metrics: {str(e)}")
            raise
    
    def log_artifacts(self, artifacts: Dict[str, Any], run_id: Optional[str] = None):
        """
        Log artifacts to MLflow run.
        
        Args:
            artifacts: Artifacts to log (file paths or data)
            run_id: Specific run ID (if None, logs to current run)
        """
        try:
            if run_id:
                # Log to specific run
                for artifact_name, artifact_data in artifacts.items():
                    if isinstance(artifact_data, str) and os.path.exists(artifact_data):
                        # File path
                        self.client.log_artifact(run_id, artifact_data, artifact_name)
                    else:
                        # Data - save to temporary file first
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                            json.dump(artifact_data, tmp_file)
                            self.client.log_artifact(run_id, tmp_file.name, artifact_name)
                            os.unlink(tmp_file.name)
            else:
                # Log to current run
                for artifact_name, artifact_data in artifacts.items():
                    if isinstance(artifact_data, str) and os.path.exists(artifact_data):
                        mlflow.log_artifact(artifact_data, artifact_name)
                    else:
                        # Data - save to temporary file first
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                            json.dump(artifact_data, tmp_file)
                            mlflow.log_artifact(tmp_file.name, artifact_name)
                            os.unlink(tmp_file.name)
            
            logger.debug(f"Logged {len(artifacts)} artifacts to MLflow")
            
        except MlflowException as e:
            logger.error(f"Error logging artifacts: {str(e)}")
            raise
    
    def log_model(
        self,
        model,
        model_name: str,
        model_type: str = "ensemble",
        run_id: Optional[str] = None
    ) -> str:
        """
        Log model to MLflow run.
        
        Args:
            model: Model object to log
            model_name: Name for the model
            model_type: Type of model (ensemble, sklearn, pytorch, tensorflow)
            run_id: Specific run ID (if None, logs to current run)
            
        Returns:
            Model URI
        """
        try:
            if run_id:
                # Log to specific run
                if model_type == "sklearn":
                    model_uri = mlflow.sklearn.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
                elif model_type == "pytorch":
                    model_uri = mlflow.pytorch.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
                elif model_type == "tensorflow":
                    model_uri = mlflow.tensorflow.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
                else:
                    # Generic model logging
                    model_uri = mlflow.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
            else:
                # Log to current run
                if model_type == "sklearn":
                    model_uri = mlflow.sklearn.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
                elif model_type == "pytorch":
                    model_uri = mlflow.pytorch.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
                elif model_type == "tensorflow":
                    model_uri = mlflow.tensorflow.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
                else:
                    # Generic model logging
                    model_uri = mlflow.log_model(
                        model, model_name, registered_model_name=model_name
                    ).model_uri
            
            logger.info(f"Logged model: {model_name} (URI: {model_uri})")
            return model_uri
            
        except MlflowException as e:
            logger.error(f"Error logging model: {str(e)}")
            raise
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """
        Get MLflow run by ID.
        
        Args:
            run_id: Run ID
            
        Returns:
            MLflow run object or None if not found
        """
        try:
            run = self.client.get_run(run_id)
            return run
        except MlflowException as e:
            logger.error(f"Error getting run {run_id}: {str(e)}")
            return None
    
    def get_run_metrics(self, run_id: str) -> Dict[str, float]:
        """
        Get metrics for a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            Dictionary of metrics
        """
        try:
            run = self.client.get_run(run_id)
            metrics = {}
            for metric in run.data.metrics:
                metrics[metric.key] = metric.value
            return metrics
        except MlflowException as e:
            logger.error(f"Error getting run metrics: {str(e)}")
            return {}
    
    def get_run_params(self, run_id: str) -> Dict[str, str]:
        """
        Get parameters for a specific run.
        
        Args:
            run_id: Run ID
            
        Returns:
            Dictionary of parameters
        """
        try:
            run = self.client.get_run(run_id)
            params = {}
            for param in run.data.params:
                params[param.key] = param.value
            return params
        except MlflowException as e:
            logger.error(f"Error getting run parameters: {str(e)}")
            return {}
    
    def search_runs(
        self,
        filter_string: Optional[str] = None,
        max_results: int = 100
    ) -> List[Run]:
        """
        Search MLflow runs.
        
        Args:
            filter_string: Filter string for search
            max_results: Maximum number of results
            
        Returns:
            List of MLflow runs
        """
        try:
            runs = self.client.search_runs(
                experiment_ids=[self.experiment_id],
                filter_string=filter_string,
                max_results=max_results
            )
            return runs
        except MlflowException as e:
            logger.error(f"Error searching runs: {str(e)}")
            return []
    
    def register_model(
        self,
        model_uri: str,
        model_name: str,
        description: Optional[str] = None
    ) -> str:
        """
        Register model in MLflow model registry.
        
        Args:
            model_uri: Model URI
            model_name: Model name
            description: Model description
            
        Returns:
            Model version
        """
        try:
            # Create model if it doesn't exist
            try:
                self.client.create_registered_model(model_name, description)
            except MlflowException:
                # Model already exists, continue
                pass
            
            # Register model version
            model_version = self.client.create_model_version(
                name=model_name,
                source=model_uri,
                description=description
            )
            
            logger.info(f"Registered model: {model_name} version {model_version.version}")
            return model_version.version
            
        except MlflowException as e:
            logger.error(f"Error registering model: {str(e)}")
            raise
    
    def transition_model_stage(
        self,
        model_name: str,
        version: str,
        stage: str,
        description: Optional[str] = None
    ):
        """
        Transition model to a specific stage.
        
        Args:
            model_name: Model name
            version: Model version
            stage: Target stage (Staging, Production, Archived)
            description: Transition description
        """
        try:
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                description=description
            )
            
            logger.info(f"Transitioned model {model_name} version {version} to {stage}")
            
        except MlflowException as e:
            logger.error(f"Error transitioning model stage: {str(e)}")
            raise
    
    def get_model_versions(self, model_name: str) -> List[Any]:
        """
        Get all versions of a model.
        
        Args:
            model_name: Model name
            
        Returns:
            List of model versions
        """
        try:
            versions = self.client.get_latest_versions(model_name)
            return versions
        except MlflowException as e:
            logger.error(f"Error getting model versions: {str(e)}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check MLflow server health.
        
        Returns:
            Health status information
        """
        try:
            # Try to get experiments
            experiments = self.client.search_experiments()
            
            return {
                'status': 'healthy',
                'tracking_uri': self.tracking_uri,
                'registry_uri': self.registry_uri,
                'experiment_id': self.experiment_id,
                'experiment_name': self.experiment_name,
                'total_experiments': len(experiments),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'tracking_uri': self.tracking_uri,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Global MLflow client instance
mlflow_client = MLflowClientManager()


# Utility functions for easy access
def start_training_run(
    run_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    description: Optional[str] = None
) -> str:
    """Start a new training run."""
    return mlflow_client.start_run(run_name, tags, description)


def end_training_run(status: str = "FINISHED", run_id: Optional[str] = None):
    """End a training run."""
    mlflow_client.end_run(status, run_id)


def log_training_params(params: Dict[str, Any], run_id: Optional[str] = None):
    """Log training parameters."""
    mlflow_client.log_parameters(params, run_id)


def log_training_metrics(metrics: Dict[str, float], run_id: Optional[str] = None):
    """Log training metrics."""
    mlflow_client.log_metrics(metrics, run_id)


def log_training_model(
    model,
    model_name: str,
    model_type: str = "ensemble",
    run_id: Optional[str] = None
) -> str:
    """Log trained model."""
    return mlflow_client.log_model(model, model_name, model_type, run_id)


def register_trained_model(
    model_uri: str,
    model_name: str,
    description: Optional[str] = None
) -> str:
    """Register trained model."""
    return mlflow_client.register_model(model_uri, model_name, description)


# Export
__all__ = [
    'MLflowClientManager',
    'mlflow_client',
    'start_training_run',
    'end_training_run',
    'log_training_params',
    'log_training_metrics',
    'log_training_model',
    'register_trained_model'
]
