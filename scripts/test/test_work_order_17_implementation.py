#!/usr/bin/env python3
"""
Work Order #17 Implementation Test Suite
Comprehensive tests for model training API and automated retraining pipeline
"""

import os
import sys
import pytest
import uuid
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.v1.training.schemas import (
    TrainingRequest, TrainingResponse, TrainingStatusResponse,
    ModelVersionResponse, ModelValidationRequest, ModelDeploymentRequest
)
from database.models.ml_model_version import (
    ModelType, ModelStatus, TrainingStatus, MLModelVersion, TrainingJob
)
from mlflow_integration.client import MLflowClientManager
from mlflow_integration.model_registry import ModelRegistry
from services.s3_data_lake import S3DataLakeClient
from training.ensemble_trainer import EnsembleTrainer
from validation.model_validator import ModelValidator
from automation.retraining_pipeline import RetrainingPipeline
from services.training_service import TrainingService


class TestMLflowIntegration:
    """Test MLflow integration components."""
    
    def test_mlflow_client_initialization(self):
        """Test MLflow client initialization."""
        client = MLflowClientManager(
            tracking_uri="http://localhost:5000",
            experiment_name="test-experiment"
        )
        
        assert client.tracking_uri == "http://localhost:5000"
        assert client.experiment_name == "test-experiment"
        assert client.client is not None
    
    @patch('mlflow.start_run')
    def test_start_run(self, mock_start_run):
        """Test starting MLflow run."""
        mock_run = Mock()
        mock_run.info.run_id = "test-run-id"
        mock_start_run.return_value.__enter__.return_value = mock_run
        
        client = MLflowClientManager()
        run_id = client.start_run("test-run", {"tag": "value"})
        
        assert run_id == "test-run-id"
        mock_start_run.assert_called_once()
    
    @patch('mlflow.log_params')
    def test_log_parameters(self, mock_log_params):
        """Test logging parameters."""
        client = MLflowClientManager()
        params = {"learning_rate": 0.001, "batch_size": 32}
        
        client.log_parameters(params)
        
        mock_log_params.assert_called_once_with(params)
    
    @patch('mlflow.log_metrics')
    def test_log_metrics(self, mock_log_metrics):
        """Test logging metrics."""
        client = MLflowClientManager()
        metrics = {"accuracy": 0.95, "loss": 0.1}
        
        client.log_metrics(metrics)
        
        mock_log_metrics.assert_called_once_with(metrics)


class TestModelRegistry:
    """Test model registry functionality."""
    
    def test_model_registry_initialization(self):
        """Test model registry initialization."""
        mock_client = Mock()
        registry = ModelRegistry(mock_client)
        
        assert registry.client == mock_client
        assert registry.default_model_name == "deepfake-detection-ensemble"
    
    @patch('mlflow.tracking.MlflowClient.create_registered_model')
    def test_create_model(self, mock_create_model):
        """Test creating registered model."""
        mock_client = Mock()
        registry = ModelRegistry(mock_client)
        
        registry.create_model("test-model", "Test model description")
        
        mock_create_model.assert_called_once_with(
            name="test-model",
            description="Test model description",
            tags=None
        )
    
    def test_validate_model(self):
        """Test model validation."""
        mock_client = Mock()
        registry = ModelRegistry(mock_client)
        
        metrics = {"auc_score": 0.97}
        is_valid, result = registry.validate_model(
            "test-model", "1.0", 0.95, metrics
        )
        
        assert is_valid is True
        assert result["auc_score"] == 0.97
        assert result["validation_threshold"] == 0.95


class TestS3DataLake:
    """Test S3 data lake integration."""
    
    def test_s3_client_initialization(self):
        """Test S3 client initialization."""
        client = S3DataLakeClient(
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            region_name="us-east-1"
        )
        
        assert client.aws_access_key_id == "test-key"
        assert client.aws_secret_access_key == "test-secret"
        assert client.region_name == "us-east-1"
    
    def test_parse_s3_path(self):
        """Test S3 path parsing."""
        client = S3DataLakeClient()
        
        bucket, key = client.parse_s3_path("s3://test-bucket/path/to/file.csv")
        
        assert bucket == "test-bucket"
        assert key == "path/to/file.csv"
    
    def test_parse_s3_path_invalid(self):
        """Test invalid S3 path parsing."""
        client = S3DataLakeClient()
        
        with pytest.raises(ValueError):
            client.parse_s3_path("invalid-path")
    
    @patch('boto3.client')
    def test_validate_dataset_path(self, mock_boto_client):
        """Test dataset path validation."""
        mock_s3_client = Mock()
        mock_s3_client.head_object.return_value = {"ContentLength": 1000}
        mock_boto_client.return_value = mock_s3_client
        
        client = S3DataLakeClient()
        is_valid = client.validate_dataset_path("s3://test-bucket/test-file.csv")
        
        assert is_valid is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test-file.csv"
        )


class TestEnsembleTrainer:
    """Test ensemble model training."""
    
    def test_trainer_initialization(self):
        """Test trainer initialization."""
        trainer = EnsembleTrainer(
            learning_rate=0.001,
            batch_size=32,
            num_epochs=10
        )
        
        assert trainer.learning_rate == 0.001
        assert trainer.batch_size == 32
        assert trainer.num_epochs == 10
        assert trainer.model is not None
    
    def test_prepare_data(self):
        """Test data preparation."""
        trainer = EnsembleTrainer()
        
        # Create sample data
        data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'labels': np.random.randint(0, 2, 100)
        })
        
        train_loader, val_loader = trainer.prepare_data(
            data, ['feature1', 'feature2'], 'labels'
        )
        
        assert train_loader is not None
        assert val_loader is not None
        assert len(train_loader.dataset) + len(val_loader.dataset) == 100


class TestModelValidator:
    """Test model validation."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = ModelValidator(validation_threshold=0.95)
        
        assert validator.validation_threshold == 0.95
        assert validator.test_size == 0.2
        assert validator.random_state == 42
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        validator = ModelValidator()
        
        y_true = np.array([0, 1, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1, 0])
        y_prob = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
        
        metrics = validator._calculate_metrics(y_true, y_pred, y_prob)
        
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'auc_score' in metrics
        assert metrics['accuracy'] >= 0.0
        assert metrics['accuracy'] <= 1.0


class TestRetrainingPipeline:
    """Test retraining pipeline."""
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = RetrainingPipeline(
            data_freshness_threshold_days=7,
            performance_degradation_threshold=0.05,
            auto_deploy=True
        )
        
        assert pipeline.data_freshness_threshold_days == 7
        assert pipeline.performance_degradation_threshold == 0.05
        assert pipeline.auto_deploy is True
    
    def test_check_data_freshness_fresh(self):
        """Test data freshness check with fresh data."""
        pipeline = RetrainingPipeline()
        
        # Mock fresh data (1 day old)
        with patch('services.s3_data_lake.s3_data_lake.get_dataset_info') as mock_info:
            mock_info.return_value = {
                'last_modified': (datetime.now(timezone.utc) - 
                                pd.Timedelta(days=1)).isoformat()
            }
            
            result = pipeline.check_data_freshness("s3://test-bucket/data")
            
            assert result['is_fresh'] is True
            assert result['days_since_update'] == 1
    
    def test_check_data_freshness_stale(self):
        """Test data freshness check with stale data."""
        pipeline = RetrainingPipeline()
        
        # Mock stale data (10 days old)
        with patch('services.s3_data_lake.s3_data_lake.get_dataset_info') as mock_info:
            mock_info.return_value = {
                'last_modified': (datetime.now(timezone.utc) - 
                                pd.Timedelta(days=10)).isoformat()
            }
            
            result = pipeline.check_data_freshness("s3://test-bucket/data")
            
            assert result['is_fresh'] is False
            assert result['days_since_update'] == 10
    
    def test_check_performance_degradation(self):
        """Test performance degradation check."""
        pipeline = RetrainingPipeline()
        
        current_metrics = {"auc_score": 0.90}
        baseline_metrics = {"auc_score": 0.95}
        
        result = pipeline.check_performance_degradation(
            "test-model", current_metrics, baseline_metrics
        )
        
        assert result['has_degraded'] is True
        assert result['degradation'] == 0.05
        assert result['current_auc'] == 0.90
        assert result['baseline_auc'] == 0.95


class TestTrainingService:
    """Test training service orchestration."""
    
    def test_service_initialization(self):
        """Test service initialization."""
        service = TrainingService(
            validation_threshold=0.95,
            auto_deploy=True,
            enable_retraining=True
        )
        
        assert service.validation_threshold == 0.95
        assert service.auto_deploy is True
        assert service.enable_retraining is True
        assert service.validator is not None
        assert service.retraining_pipeline is not None
    
    @pytest.mark.asyncio
    async def test_load_and_validate_data(self):
        """Test data loading and validation."""
        service = TrainingService()
        
        # Mock S3 data lake
        with patch('services.s3_data_lake.s3_data_lake.validate_dataset_path') as mock_validate, \
             patch('services.s3_data_lake.s3_data_lake.load_training_data') as mock_load, \
             patch('services.s3_data_lake.s3_data_lake.validate_training_data') as mock_data_validate:
            
            mock_validate.return_value = True
            mock_load.return_value = {
                'data': pd.DataFrame({'feature1': [1, 2, 3], 'labels': [0, 1, 0]}),
                'rows': 3,
                'columns': ['feature1', 'labels'],
                'format': 'csv',
                'memory_usage_mb': 0.1
            }
            mock_data_validate.return_value = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            result = await service._load_and_validate_data("s3://test-bucket/data")
            
            assert result['success'] is True
            assert 'data' in result
            assert 'data_info' in result


class TestTrainingSchemas:
    """Test training API schemas."""
    
    def test_training_request_validation(self):
        """Test training request validation."""
        request = TrainingRequest(
            dataset_path="s3://test-bucket/data.csv",
            model_type=ModelType.ENSEMBLE,
            hyperparameters={"learning_rate": 0.001, "batch_size": 32},
            validation_threshold=0.95
        )
        
        assert request.dataset_path == "s3://test-bucket/data.csv"
        assert request.model_type == ModelType.ENSEMBLE
        assert request.hyperparameters["learning_rate"] == 0.001
        assert request.validation_threshold == 0.95
    
    def test_training_request_invalid_dataset_path(self):
        """Test training request with invalid dataset path."""
        with pytest.raises(ValueError):
            TrainingRequest(
                dataset_path="invalid-path",
                model_type=ModelType.ENSEMBLE
            )
    
    def test_training_request_invalid_threshold(self):
        """Test training request with invalid validation threshold."""
        with pytest.raises(ValueError):
            TrainingRequest(
                dataset_path="s3://test-bucket/data.csv",
                model_type=ModelType.ENSEMBLE,
                validation_threshold=1.5  # Invalid threshold
            )
    
    def test_training_response(self):
        """Test training response."""
        response = TrainingResponse(
            job_id=uuid.uuid4(),
            task_id="test-task-id",
            status=TrainingStatus.RUNNING,
            message="Training started",
            created_at=datetime.now(timezone.utc),
            validation_threshold=0.95
        )
        
        assert response.status == TrainingStatus.RUNNING
        assert response.message == "Training started"
        assert response.validation_threshold == 0.95


class TestDatabaseModels:
    """Test database models."""
    
    def test_ml_model_version_creation(self):
        """Test ML model version creation."""
        model_version = MLModelVersion(
            model_name="test-model",
            version="1.0.0",
            model_type=ModelType.ENSEMBLE,
            training_data_s3_path="s3://test-bucket/data",
            auc_score=0.95,
            status=ModelStatus.VALIDATED
        )
        
        assert model_version.model_name == "test-model"
        assert model_version.version == "1.0.0"
        assert model_version.model_type == ModelType.ENSEMBLE
        assert model_version.auc_score == 0.95
        assert model_version.status == ModelStatus.VALIDATED
    
    def test_training_job_creation(self):
        """Test training job creation."""
        job = TrainingJob(
            job_name="test-job",
            model_type=ModelType.ENSEMBLE,
            dataset_path="s3://test-bucket/data",
            status=TrainingStatus.PENDING
        )
        
        assert job.job_name == "test-job"
        assert job.model_type == ModelType.ENSEMBLE
        assert job.dataset_path == "s3://test-bucket/data"
        assert job.status == TrainingStatus.PENDING
    
    def test_hyperparameters_serialization(self):
        """Test hyperparameters serialization."""
        model_version = MLModelVersion(
            model_name="test-model",
            version="1.0.0",
            model_type=ModelType.ENSEMBLE,
            training_data_s3_path="s3://test-bucket/data"
        )
        
        hyperparams = {"learning_rate": 0.001, "batch_size": 32}
        model_version.set_hyperparameters(hyperparams)
        
        retrieved_hyperparams = model_version.get_hyperparameters()
        
        assert retrieved_hyperparams == hyperparams


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_training_workflow(self):
        """Test full training workflow."""
        service = TrainingService()
        
        # Mock all external dependencies
        with patch('services.s3_data_lake.s3_data_lake.validate_dataset_path') as mock_validate, \
             patch('services.s3_data_lake.s3_data_lake.load_training_data') as mock_load, \
             patch('services.s3_data_lake.s3_data_lake.validate_training_data') as mock_data_validate, \
             patch('training.ensemble_trainer.train_ensemble_model') as mock_train, \
             patch('validation.model_validator.ModelValidator.validate_model_performance') as mock_validate_model, \
             patch('mlflow_integration.model_registry.model_registry.register_model_version') as mock_register:
            
            # Setup mocks
            mock_validate.return_value = True
            mock_load.return_value = {
                'data': pd.DataFrame({'feature1': [1, 2, 3], 'labels': [0, 1, 0]}),
                'rows': 3,
                'columns': ['feature1', 'labels'],
                'format': 'csv',
                'memory_usage_mb': 0.1
            }
            mock_data_validate.return_value = {'is_valid': True, 'errors': []}
            
            mock_trainer = Mock()
            mock_trainer.model = Mock()
            mock_train.return_value = (mock_trainer, {'best_val_accuracy': 0.95})
            
            mock_validate_model.return_value = {
                'is_valid': True,
                'metrics': {'auc_score': 0.97, 'accuracy': 0.95}
            }
            
            mock_register.return_value = "1.0.0"
            
            # Run training workflow
            result = await service.train_model(
                dataset_path="s3://test-bucket/data.csv",
                model_type="ensemble",
                hyperparameters={"learning_rate": 0.001}
            )
            
            assert result['status'] == 'completed'
            assert 'workflow_id' in result
            assert 'job_id' in result
            assert 'stages' in result
    
    def test_retraining_decision_logic(self):
        """Test retraining decision logic."""
        pipeline = RetrainingPipeline()
        
        # Test case: Fresh data, good performance
        with patch.object(pipeline, 'check_data_freshness') as mock_freshness, \
             patch.object(pipeline, 'check_performance_degradation') as mock_degradation:
            
            mock_freshness.return_value = {'is_fresh': True}
            mock_degradation.return_value = {'has_degraded': False}
            
            result = pipeline.should_retrain("test-model", "s3://test-bucket/data")
            
            assert result['should_retrain'] is False
            assert 'No retraining needed' in result['recommendation']
        
        # Test case: Stale data, degraded performance
        with patch.object(pipeline, 'check_data_freshness') as mock_freshness, \
             patch.object(pipeline, 'check_performance_degradation') as mock_degradation:
            
            mock_freshness.return_value = {'is_fresh': False}
            mock_degradation.return_value = {'has_degraded': True}
            
            result = pipeline.should_retrain("test-model", "s3://test-bucket/data")
            
            assert result['should_retrain'] is True
            assert 'Retraining recommended' in result['recommendation']
            assert len(result['reasons']) == 2


# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
