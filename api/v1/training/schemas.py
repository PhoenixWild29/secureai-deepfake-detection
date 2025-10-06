#!/usr/bin/env python3
"""
Training API Schemas
Pydantic models for training API requests and responses
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, validator
from enum import Enum

from database.models.ml_model_version import (
    ModelType, ModelStatus, TrainingStatus,
    TrainingRequest as BaseTrainingRequest,
    TrainingResponse as BaseTrainingResponse,
    TrainingStatusResponse as BaseTrainingStatusResponse,
    ModelVersionResponse as BaseModelVersionResponse,
    ModelMetricsResponse as BaseModelMetricsResponse
)


class TrainingRequest(BaseTrainingRequest):
    """
    Enhanced training request model with validation.
    """
    
    @validator('dataset_path')
    def validate_dataset_path(cls, v):
        """Validate dataset path format."""
        if not v.startswith('s3://'):
            raise ValueError('Dataset path must be a valid S3 URI (s3://bucket/path)')
        return v
    
    @validator('hyperparameters')
    def validate_hyperparameters(cls, v):
        """Validate hyperparameters structure."""
        if v is not None:
            # Check for required hyperparameters based on model type
            required_params = {
                'ensemble': ['learning_rate', 'batch_size', 'epochs'],
                'resnet50': ['learning_rate', 'batch_size', 'epochs', 'optimizer'],
                'clip': ['learning_rate', 'batch_size', 'epochs', 'temperature'],
                'custom': ['learning_rate', 'batch_size', 'epochs']
            }
            
            # This would be validated based on model_type in the endpoint
            # For now, just ensure it's a dictionary
            if not isinstance(v, dict):
                raise ValueError('Hyperparameters must be a dictionary')
        
        return v
    
    @validator('validation_threshold')
    def validate_threshold(cls, v):
        """Validate validation threshold."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Validation threshold must be between 0.0 and 1.0')
        return v


class TrainingResponse(BaseTrainingResponse):
    """
    Enhanced training response model.
    """
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Applied hyperparameters")
    validation_threshold: float = Field(..., description="Validation threshold")


class TrainingStatusResponse(BaseTrainingStatusResponse):
    """
    Enhanced training status response model.
    """
    model_type: ModelType = Field(..., description="Model type being trained")
    dataset_path: str = Field(..., description="Training dataset path")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Training hyperparameters")
    validation_threshold: float = Field(..., description="Validation threshold")
    mlflow_run_id: Optional[str] = Field(None, description="MLflow run ID")
    created_at: datetime = Field(..., description="Job creation timestamp")


class ModelVersionResponse(BaseModelVersionResponse):
    """
    Enhanced model version response model.
    """
    training_job_id: Optional[uuid.UUID] = Field(None, description="Training job ID")
    training_data_s3_path: str = Field(..., description="Training data S3 path")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Training hyperparameters")
    validation_threshold: Optional[float] = Field(None, description="Validation threshold")
    description: Optional[str] = Field(None, description="Model description")
    tags: Optional[Dict[str, str]] = Field(None, description="Model tags")


class ModelMetricsResponse(BaseModelMetricsResponse):
    """
    Enhanced model metrics response model.
    """
    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    model_type: ModelType = Field(..., description="Model type")
    dataset_split: Optional[str] = Field(None, description="Dataset split evaluated")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metric metadata")


class ModelListResponse(BaseModel):
    """Response model for model list API."""
    models: List[ModelVersionResponse] = Field(..., description="List of model versions")
    total_count: int = Field(..., description="Total number of models")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")


class TrainingJobListResponse(BaseModel):
    """Response model for training job list API."""
    jobs: List[TrainingStatusResponse] = Field(..., description="List of training jobs")
    total_count: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")


class ModelDeploymentRequest(BaseModel):
    """Request model for model deployment API."""
    model_name: str = Field(..., description="Name of the model to deploy")
    version: Optional[str] = Field(None, description="Specific version to deploy (if None, deploys latest)")
    stage: str = Field(default="Production", description="Deployment stage")
    description: Optional[str] = Field(None, description="Deployment description")
    force_deploy: bool = Field(default=False, description="Force deployment even if validation fails")


class ModelDeploymentResponse(BaseModel):
    """Response model for model deployment API."""
    model_name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    stage: str = Field(..., description="Deployment stage")
    deployment_status: str = Field(..., description="Deployment status")
    message: str = Field(..., description="Deployment message")
    deployed_at: datetime = Field(..., description="Deployment timestamp")


class ModelValidationRequest(BaseModel):
    """Request model for model validation API."""
    model_name: str = Field(..., description="Name of the model to validate")
    version: Optional[str] = Field(None, description="Specific version to validate (if None, validates latest)")
    validation_threshold: Optional[float] = Field(None, description="Custom validation threshold")
    test_dataset_path: Optional[str] = Field(None, description="Custom test dataset path")


class ModelValidationResponse(BaseModel):
    """Response model for model validation API."""
    model_name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    validation_status: str = Field(..., description="Validation status")
    auc_score: float = Field(..., description="AUC score")
    validation_threshold: float = Field(..., description="Validation threshold used")
    is_valid: bool = Field(..., description="Whether model meets validation threshold")
    metrics: Dict[str, float] = Field(..., description="All performance metrics")
    validation_timestamp: datetime = Field(..., description="Validation timestamp")


class RetrainingConfigRequest(BaseModel):
    """Request model for retraining configuration API."""
    model_name: str = Field(..., description="Name of the model to configure retraining for")
    retraining_schedule: str = Field(..., description="Cron expression for retraining schedule")
    data_freshness_threshold_days: int = Field(default=7, description="Data freshness threshold in days")
    performance_degradation_threshold: float = Field(default=0.05, description="Performance degradation threshold")
    auto_deploy: bool = Field(default=False, description="Whether to auto-deploy validated models")
    enabled: bool = Field(default=True, description="Whether retraining is enabled")


class RetrainingConfigResponse(BaseModel):
    """Response model for retraining configuration API."""
    model_name: str = Field(..., description="Model name")
    retraining_schedule: str = Field(..., description="Retraining schedule")
    data_freshness_threshold_days: int = Field(..., description="Data freshness threshold")
    performance_degradation_threshold: float = Field(..., description="Performance degradation threshold")
    auto_deploy: bool = Field(..., description="Auto-deployment setting")
    enabled: bool = Field(..., description="Retraining enabled status")
    next_retraining: Optional[datetime] = Field(None, description="Next scheduled retraining")
    created_at: datetime = Field(..., description="Configuration creation timestamp")
    updated_at: datetime = Field(..., description="Configuration last update timestamp")


class HyperparameterOptimizationRequest(BaseModel):
    """Request model for hyperparameter optimization API."""
    model_type: ModelType = Field(..., description="Type of model to optimize")
    dataset_path: str = Field(..., description="S3 path to training dataset")
    optimization_method: str = Field(default="random_search", description="Optimization method")
    max_trials: int = Field(default=10, ge=1, le=100, description="Maximum number of trials")
    validation_threshold: float = Field(default=0.95, ge=0.0, le=1.0, description="Validation threshold")
    hyperparameter_space: Dict[str, Any] = Field(..., description="Hyperparameter search space")


class HyperparameterOptimizationResponse(BaseModel):
    """Response model for hyperparameter optimization API."""
    optimization_id: uuid.UUID = Field(..., description="Optimization job ID")
    model_type: ModelType = Field(..., description="Model type")
    optimization_method: str = Field(..., description="Optimization method")
    max_trials: int = Field(..., description="Maximum trials")
    status: str = Field(..., description="Optimization status")
    best_hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Best hyperparameters found")
    best_score: Optional[float] = Field(None, description="Best validation score")
    created_at: datetime = Field(..., description="Optimization creation timestamp")


class TrainingMetricsRequest(BaseModel):
    """Request model for training metrics API."""
    job_id: Optional[uuid.UUID] = Field(None, description="Specific training job ID")
    model_name: Optional[str] = Field(None, description="Model name filter")
    model_type: Optional[ModelType] = Field(None, description="Model type filter")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")


class TrainingMetricsResponse(BaseModel):
    """Response model for training metrics API."""
    metrics: List[Dict[str, Any]] = Field(..., description="Training metrics data")
    total_count: int = Field(..., description="Total number of metrics")
    aggregation: Dict[str, Any] = Field(..., description="Aggregated metrics")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Error timestamp")


# Export
__all__ = [
    'TrainingRequest',
    'TrainingResponse',
    'TrainingStatusResponse',
    'ModelVersionResponse',
    'ModelMetricsResponse',
    'ModelListResponse',
    'TrainingJobListResponse',
    'ModelDeploymentRequest',
    'ModelDeploymentResponse',
    'ModelValidationRequest',
    'ModelValidationResponse',
    'RetrainingConfigRequest',
    'RetrainingConfigResponse',
    'HyperparameterOptimizationRequest',
    'HyperparameterOptimizationResponse',
    'TrainingMetricsRequest',
    'TrainingMetricsResponse',
    'ErrorResponse'
]
