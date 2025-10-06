#!/usr/bin/env python3
"""
ML Model Version Database Model
SQLModel for tracking ML model versions, training jobs, and performance metrics
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from pydantic import BaseModel, Field as PydanticField
import json


class ModelType(str, Enum):
    """ML model types."""
    ENSEMBLE = "ensemble"
    RESNET50 = "resnet50"
    CLIP = "clip"
    CUSTOM = "custom"


class ModelStatus(str, Enum):
    """Model status."""
    TRAINING = "training"
    TRAINED = "trained"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ARCHIVED = "archived"


class TrainingStatus(str, Enum):
    """Training job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MLModelVersion(SQLModel, table=True):
    """
    ML Model Version database model.
    Tracks model versions, training metadata, and performance metrics.
    """
    __tablename__ = "ml_model_versions"
    
    # Primary key
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Model identification
    model_name: str = Field(index=True, description="Name of the model")
    version: str = Field(index=True, description="Model version")
    model_type: ModelType = Field(description="Type of ML model")
    
    # MLflow integration
    mlflow_run_id: Optional[str] = Field(index=True, description="MLflow run ID")
    mlflow_model_uri: Optional[str] = Field(description="MLflow model URI")
    artifact_uri: Optional[str] = Field(description="Model artifact URI")
    
    # Training metadata
    training_data_s3_path: str = Field(description="S3 path to training data")
    training_job_id: Optional[uuid.UUID] = Field(foreign_key="training_jobs.id", description="Training job ID")
    hyperparameters: Optional[str] = Field(description="Training hyperparameters as JSON")
    
    # Performance metrics
    auc_score: Optional[float] = Field(description="AUC score")
    accuracy: Optional[float] = Field(description="Accuracy score")
    precision: Optional[float] = Field(description="Precision score")
    recall: Optional[float] = Field(description="Recall score")
    f1_score: Optional[float] = Field(description="F1 score")
    validation_threshold: Optional[float] = Field(description="Validation threshold used")
    
    # Model status and deployment
    status: ModelStatus = Field(default=ModelStatus.TRAINING, description="Model status")
    is_deployed: bool = Field(default=False, description="Whether model is deployed")
    deployment_stage: Optional[str] = Field(description="Deployment stage (Staging, Production)")
    
    # Metadata
    description: Optional[str] = Field(description="Model description")
    tags: Optional[str] = Field(description="Model tags as JSON")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    # Relationships
    training_job: Optional["TrainingJob"] = Relationship(back_populates="model_versions")
    
    def get_hyperparameters(self) -> Dict[str, Any]:
        """Get hyperparameters as dictionary."""
        if self.hyperparameters:
            try:
                return json.loads(self.hyperparameters)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_hyperparameters(self, hyperparams: Dict[str, Any]):
        """Set hyperparameters from dictionary."""
        self.hyperparameters = json.dumps(hyperparams)
    
    def get_tags(self) -> Dict[str, str]:
        """Get tags as dictionary."""
        if self.tags:
            try:
                return json.loads(self.tags)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_tags(self, tags: Dict[str, str]):
        """Set tags from dictionary."""
        self.tags = json.dumps(tags)
    
    def get_metrics(self) -> Dict[str, float]:
        """Get all performance metrics as dictionary."""
        metrics = {}
        if self.auc_score is not None:
            metrics['auc_score'] = self.auc_score
        if self.accuracy is not None:
            metrics['accuracy'] = self.accuracy
        if self.precision is not None:
            metrics['precision'] = self.precision
        if self.recall is not None:
            metrics['recall'] = self.recall
        if self.f1_score is not None:
            metrics['f1_score'] = self.f1_score
        return metrics


class TrainingJob(SQLModel, table=True):
    """
    Training Job database model.
    Tracks training job execution, status, and metadata.
    """
    __tablename__ = "training_jobs"
    
    # Primary key
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Job identification
    job_name: str = Field(index=True, description="Training job name")
    celery_task_id: Optional[str] = Field(index=True, description="Celery task ID")
    
    # Training configuration
    model_type: ModelType = Field(description="Type of model to train")
    dataset_path: str = Field(description="Path to training dataset")
    hyperparameters: Optional[str] = Field(description="Training hyperparameters as JSON")
    validation_threshold: float = Field(default=0.95, description="Validation threshold")
    
    # Job status and progress
    status: TrainingStatus = Field(default=TrainingStatus.PENDING, description="Job status")
    progress_percentage: Optional[float] = Field(description="Training progress percentage")
    current_stage: Optional[str] = Field(description="Current training stage")
    
    # Execution metadata
    started_at: Optional[datetime] = Field(description="Job start timestamp")
    completed_at: Optional[datetime] = Field(description="Job completion timestamp")
    duration_seconds: Optional[float] = Field(description="Total job duration in seconds")
    
    # Error handling
    error_message: Optional[str] = Field(description="Error message if job failed")
    error_traceback: Optional[str] = Field(description="Error traceback if job failed")
    
    # Resource usage
    cpu_usage_percent: Optional[float] = Field(description="Average CPU usage percentage")
    memory_usage_mb: Optional[float] = Field(description="Peak memory usage in MB")
    gpu_usage_percent: Optional[float] = Field(description="Average GPU usage percentage")
    gpu_memory_usage_mb: Optional[float] = Field(description="Peak GPU memory usage in MB")
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    
    # Relationships
    model_versions: List[MLModelVersion] = Relationship(back_populates="training_job")
    
    def get_hyperparameters(self) -> Dict[str, Any]:
        """Get hyperparameters as dictionary."""
        if self.hyperparameters:
            try:
                return json.loads(self.hyperparameters)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_hyperparameters(self, hyperparams: Dict[str, Any]):
        """Set hyperparameters from dictionary."""
        self.hyperparameters = json.dumps(hyperparams)
    
    def get_resource_usage(self) -> Dict[str, float]:
        """Get resource usage metrics as dictionary."""
        usage = {}
        if self.cpu_usage_percent is not None:
            usage['cpu_usage_percent'] = self.cpu_usage_percent
        if self.memory_usage_mb is not None:
            usage['memory_usage_mb'] = self.memory_usage_mb
        if self.gpu_usage_percent is not None:
            usage['gpu_usage_percent'] = self.gpu_usage_percent
        if self.gpu_memory_usage_mb is not None:
            usage['gpu_memory_usage_mb'] = self.gpu_memory_usage_mb
        return usage


class ModelMetrics(SQLModel, table=True):
    """
    Model Metrics database model.
    Tracks detailed performance metrics for model evaluation.
    """
    __tablename__ = "model_metrics"
    
    # Primary key
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # Model reference
    model_version_id: uuid.UUID = Field(foreign_key="ml_model_versions.id", index=True, description="Model version ID")
    
    # Metric identification
    metric_name: str = Field(index=True, description="Name of the metric")
    metric_value: float = Field(description="Metric value")
    metric_type: str = Field(description="Type of metric (accuracy, precision, recall, etc.)")
    
    # Evaluation context
    dataset_split: Optional[str] = Field(description="Dataset split (train, validation, test)")
    evaluation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Evaluation timestamp")
    
    # Additional metadata
    metadata: Optional[str] = Field(description="Additional metric metadata as JSON")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata from dictionary."""
        self.metadata = json.dumps(metadata)


# Pydantic models for API requests/responses

class TrainingRequest(BaseModel):
    """Request model for training API."""
    dataset_path: str = PydanticField(..., description="S3 path to training dataset")
    model_type: ModelType = PydanticField(..., description="Type of model to train")
    hyperparameters: Optional[Dict[str, Any]] = PydanticField(None, description="Training hyperparameters")
    validation_threshold: float = PydanticField(default=0.95, ge=0.0, le=1.0, description="Validation threshold")
    job_name: Optional[str] = PydanticField(None, description="Custom job name")
    description: Optional[str] = PydanticField(None, description="Training job description")


class TrainingResponse(BaseModel):
    """Response model for training API."""
    job_id: uuid.UUID = PydanticField(..., description="Training job ID")
    task_id: Optional[str] = PydanticField(None, description="Celery task ID")
    status: TrainingStatus = PydanticField(..., description="Job status")
    message: str = PydanticField(..., description="Status message")
    created_at: datetime = PydanticField(..., description="Creation timestamp")


class TrainingStatusResponse(BaseModel):
    """Response model for training status API."""
    job_id: uuid.UUID = PydanticField(..., description="Training job ID")
    status: TrainingStatus = PydanticField(..., description="Job status")
    progress_percentage: Optional[float] = PydanticField(None, description="Progress percentage")
    current_stage: Optional[str] = PydanticField(None, description="Current training stage")
    started_at: Optional[datetime] = PydanticField(None, description="Start timestamp")
    completed_at: Optional[datetime] = PydanticField(None, description="Completion timestamp")
    duration_seconds: Optional[float] = PydanticField(None, description="Duration in seconds")
    error_message: Optional[str] = PydanticField(None, description="Error message if failed")
    resource_usage: Optional[Dict[str, float]] = PydanticField(None, description="Resource usage metrics")


class ModelVersionResponse(BaseModel):
    """Response model for model version API."""
    id: uuid.UUID = PydanticField(..., description="Model version ID")
    model_name: str = PydanticField(..., description="Model name")
    version: str = PydanticField(..., description="Model version")
    model_type: ModelType = PydanticField(..., description="Model type")
    status: ModelStatus = PydanticField(..., description="Model status")
    auc_score: Optional[float] = PydanticField(None, description="AUC score")
    accuracy: Optional[float] = PydanticField(None, description="Accuracy score")
    precision: Optional[float] = PydanticField(None, description="Precision score")
    recall: Optional[float] = PydanticField(None, description="Recall score")
    f1_score: Optional[float] = PydanticField(None, description="F1 score")
    is_deployed: bool = PydanticField(..., description="Deployment status")
    deployment_stage: Optional[str] = PydanticField(None, description="Deployment stage")
    mlflow_run_id: Optional[str] = PydanticField(None, description="MLflow run ID")
    artifact_uri: Optional[str] = PydanticField(None, description="Model artifact URI")
    created_at: datetime = PydanticField(..., description="Creation timestamp")
    updated_at: datetime = PydanticField(..., description="Last update timestamp")


class ModelMetricsResponse(BaseModel):
    """Response model for model metrics API."""
    model_version_id: uuid.UUID = PydanticField(..., description="Model version ID")
    metrics: Dict[str, float] = PydanticField(..., description="Performance metrics")
    validation_threshold: Optional[float] = PydanticField(None, description="Validation threshold")
    is_validated: bool = PydanticField(..., description="Whether model meets validation threshold")
    evaluation_timestamp: datetime = PydanticField(..., description="Evaluation timestamp")


# Export
__all__ = [
    'ModelType',
    'ModelStatus',
    'TrainingStatus',
    'MLModelVersion',
    'TrainingJob',
    'ModelMetrics',
    'TrainingRequest',
    'TrainingResponse',
    'TrainingStatusResponse',
    'ModelVersionResponse',
    'ModelMetricsResponse'
]
