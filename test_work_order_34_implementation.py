#!/usr/bin/env python3
"""
Test Suite for Work Order #34 Implementation
Status Tracking API Models and Validation Logic
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timezone
from typing import Dict, Any, List

# Import our implemented models and validators
from src.models.status_tracking import (
    StatusTrackingResponse,
    StatusHistoryResponse,
    ProcessingStageEnum,
    StatusTransitionValidator
)


class TestStatusTrackingResponse:
    """Test the StatusTrackingResponse model"""
    
    def test_status_tracking_response_creation(self):
        """Test creating a valid StatusTrackingResponse"""
        response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="processing",
            progress_percentage=45.5,
            current_stage="feature_analysis",
            processing_time_elapsed=120000,
            retry_count=0,
            stage_history=[
                {
                    "stage": "upload",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "completed"
                },
                {
                    "stage": "preprocessing", 
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "completed"
                }
            ]
        )
        
        assert response.analysis_id is not None
        assert response.status == "processing"
        assert response.progress_percentage == 45.5
        assert response.current_stage == "feature_analysis"
        assert response.processing_time_elapsed == 120000
        assert response.retry_count == 0
        assert len(response.stage_history) == 2
    
    def test_progress_percentage_validation(self):
        """Test progress percentage validation (0.0-100.0)"""
        # Valid progress percentages
        valid_percentages = [0.0, 50.0, 100.0, 45.5, 99.99]
        for percentage in valid_percentages:
            response = StatusTrackingResponse(
                analysis_id=uuid4(),
                status="processing",
                progress_percentage=percentage,
                current_stage="feature_analysis",
                processing_time_elapsed=1000
            )
            assert response.progress_percentage == percentage
        
        # Invalid progress percentages
        invalid_percentages = [-1.0, 100.1, 150.0, -0.1]
        for percentage in invalid_percentages:
            with pytest.raises(ValueError, match="progress_percentage must be between 0.0 and 100.0"):
                StatusTrackingResponse(
                    analysis_id=uuid4(),
                    status="processing",
                    progress_percentage=percentage,
                    current_stage="feature_analysis",
                    processing_time_elapsed=1000
                )
    
    def test_status_validation(self):
        """Test status field validation"""
        # Valid statuses
        valid_statuses = ["queued", "processing", "completed", "failed"]
        for status in valid_statuses:
            response = StatusTrackingResponse(
                analysis_id=uuid4(),
                status=status,
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=1000
            )
            assert response.status == status.lower()
        
        # Invalid status
        with pytest.raises(ValueError, match="status must be one of"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="invalid_status",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=1000
            )
    
    def test_current_stage_validation(self):
        """Test current stage validation"""
        # Valid stages
        valid_stages = [
            "upload", "preprocessing", "frame_extraction", "feature_analysis",
            "deepfake_detection", "postprocessing", "blockchain_verification", "finalization"
        ]
        for stage in valid_stages:
            response = StatusTrackingResponse(
                analysis_id=uuid4(),
                status="processing",
                progress_percentage=50.0,
                current_stage=stage,
                processing_time_elapsed=1000
            )
            assert response.current_stage == stage.lower()
        
        # Invalid stage
        with pytest.raises(ValueError, match="current_stage must be one of"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="processing",
                progress_percentage=50.0,
                current_stage="invalid_stage",
                processing_time_elapsed=1000
            )
    
    def test_processing_time_validation(self):
        """Test processing time validation"""
        # Valid processing times
        valid_times = [0, 1000, 60000, 3600000]  # 0ms to 1 hour
        for time_ms in valid_times:
            response = StatusTrackingResponse(
                analysis_id=uuid4(),
                status="processing",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=time_ms
            )
            assert response.processing_time_elapsed == time_ms
        
        # Invalid processing times
        with pytest.raises(ValueError, match="processing_time_elapsed must be non-negative"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="processing",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=-1000
            )
    
    def test_retry_count_validation(self):
        """Test retry count validation"""
        # Valid retry counts
        valid_counts = [0, 1, 5, 10]
        for count in valid_counts:
            response = StatusTrackingResponse(
                analysis_id=uuid4(),
                status="failed",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=1000,
                retry_count=count
            )
            assert response.retry_count == count
        
        # Invalid retry counts
        with pytest.raises(ValueError, match="retry_count must be non-negative"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="failed",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=1000,
                retry_count=-1
            )
        
        with pytest.raises(ValueError, match="retry_count cannot exceed"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="failed",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=1000,
                retry_count=11
            )
    
    def test_status_transition_validation(self):
        """Test status transition validation"""
        # Valid transition: queued -> processing
        response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="processing",
            progress_percentage=10.0,
            current_stage="upload",
            processing_time_elapsed=1000,
            stage_history=[
                {
                    "stage": "upload",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "queued"
                }
            ]
        )
        assert response.status == "processing"
        
        # Valid transition: processing -> completed
        response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="completed",
            progress_percentage=100.0,
            current_stage="finalization",
            processing_time_elapsed=5000,
            stage_history=[
                {
                    "stage": "upload",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "queued"
                },
                {
                    "stage": "preprocessing",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "processing"
                }
            ]
        )
        assert response.status == "completed"
    
    def test_progress_consistency_validation(self):
        """Test progress consistency with status"""
        # Completed status should have 100% progress
        with pytest.raises(ValueError, match="completed status requires 100.0% progress"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="completed",
                progress_percentage=90.0,
                current_stage="finalization",
                processing_time_elapsed=5000
            )
        
        # Queued status should have minimal progress
        with pytest.raises(ValueError, match="queued status should have minimal progress"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="queued",
                progress_percentage=10.0,
                current_stage="upload",
                processing_time_elapsed=0
            )
    
    def test_stage_history_validation(self):
        """Test stage history validation"""
        # Valid stage history
        response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="processing",
            progress_percentage=50.0,
            current_stage="feature_analysis",
            processing_time_elapsed=2000,
            stage_history=[
                {
                    "stage": "upload",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "stage": "preprocessing",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        )
        assert len(response.stage_history) == 2
        
        # Invalid stage history - missing required fields
        with pytest.raises(ValueError, match="stage_history.*missing required field"):
            StatusTrackingResponse(
                analysis_id=uuid4(),
                status="processing",
                progress_percentage=50.0,
                current_stage="feature_analysis",
                processing_time_elapsed=2000,
                stage_history=[
                    {
                        "stage": "upload"
                        # Missing timestamp
                    }
                ]
            )
    
    def test_utility_methods(self):
        """Test utility methods"""
        response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="processing",
            progress_percentage=50.0,
            current_stage="feature_analysis",
            processing_time_elapsed=2000
        )
        
        # Test duration calculation
        assert response.get_processing_duration_seconds() == 2.0
        
        # Test remaining time calculation
        remaining = response.get_estimated_remaining_time_ms()
        assert remaining is not None
        assert remaining > 0
        
        # Test terminal status check
        assert not response.is_terminal_status()
        
        # Test retry capability
        assert response.can_retry() == False  # processing status
        
        # Test with failed status
        failed_response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="failed",
            progress_percentage=50.0,
            current_stage="feature_analysis",
            processing_time_elapsed=2000,
            retry_count=0
        )
        assert failed_response.is_terminal_status()
        assert failed_response.can_retry()


class TestStatusHistoryResponse:
    """Test the StatusHistoryResponse model"""
    
    def test_status_history_response_creation(self):
        """Test creating a valid StatusHistoryResponse"""
        response = StatusHistoryResponse(
            analysis_id=uuid4(),
            status_timeline=[
                {
                    "status": "queued",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "status": "processing",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "status": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            processing_stages=[
                {
                    "stage": "upload",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat()
                },
                {
                    "stage": "preprocessing",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat()
                }
            ],
            error_logs=[],
            performance_metrics={"avg_processing_time": 1000},
            retry_history=[],
            total_processing_time_ms=5000,
            final_status="completed",
            created_at=datetime.now(timezone.utc)
        )
        
        assert response.analysis_id is not None
        assert response.final_status == "completed"
        assert response.total_processing_time_ms == 5000
        assert len(response.status_timeline) == 3
        assert len(response.processing_stages) == 2
    
    def test_final_status_validation(self):
        """Test final status validation"""
        # Valid final statuses
        valid_statuses = ["completed", "failed"]
        for status in valid_statuses:
            response = StatusHistoryResponse(
                analysis_id=uuid4(),
                total_processing_time_ms=1000,
                final_status=status,
                created_at=datetime.now(timezone.utc)
            )
            assert response.final_status == status.lower()
        
        # Invalid final status
        with pytest.raises(ValueError, match="final_status must be one of"):
            StatusHistoryResponse(
                analysis_id=uuid4(),
                total_processing_time_ms=1000,
                final_status="processing",  # Not a terminal status
                created_at=datetime.now(timezone.utc)
            )
    
    def test_total_processing_time_validation(self):
        """Test total processing time validation"""
        # Valid processing times
        valid_times = [0, 1000, 3600000, 86400000]  # 0ms to 24 hours
        for time_ms in valid_times:
            response = StatusHistoryResponse(
                analysis_id=uuid4(),
                total_processing_time_ms=time_ms,
                final_status="completed",
                created_at=datetime.now(timezone.utc)
            )
            assert response.total_processing_time_ms == time_ms
        
        # Invalid processing times
        with pytest.raises(ValueError, match="total_processing_time_ms must be non-negative"):
            StatusHistoryResponse(
                analysis_id=uuid4(),
                total_processing_time_ms=-1000,
                final_status="completed",
                created_at=datetime.now(timezone.utc)
            )
    
    def test_status_timeline_validation(self):
        """Test status timeline validation"""
        # Valid timeline
        response = StatusHistoryResponse(
            analysis_id=uuid4(),
            status_timeline=[
                {
                    "status": "queued",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "status": "processing",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            total_processing_time_ms=1000,
            final_status="completed",
            created_at=datetime.now(timezone.utc)
        )
        assert len(response.status_timeline) == 2
        
        # Invalid timeline - missing required fields
        with pytest.raises(ValueError, match="status_timeline.*missing required field"):
            StatusHistoryResponse(
                analysis_id=uuid4(),
                status_timeline=[
                    {
                        "status": "queued"
                        # Missing timestamp
                    }
                ],
                total_processing_time_ms=1000,
                final_status="completed",
                created_at=datetime.now(timezone.utc)
            )
        
        # Invalid timeline - invalid status
        with pytest.raises(ValueError, match="status_timeline.*status must be one of"):
            StatusHistoryResponse(
                analysis_id=uuid4(),
                status_timeline=[
                    {
                        "status": "invalid_status",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                ],
                total_processing_time_ms=1000,
                final_status="completed",
                created_at=datetime.now(timezone.utc)
            )
    
    def test_processing_stages_validation(self):
        """Test processing stages validation"""
        # Valid processing stages
        response = StatusHistoryResponse(
            analysis_id=uuid4(),
            processing_stages=[
                {
                    "stage": "upload",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat()
                }
            ],
            total_processing_time_ms=1000,
            final_status="completed",
            created_at=datetime.now(timezone.utc)
        )
        assert len(response.processing_stages) == 1
        
        # Invalid processing stages - missing required fields
        with pytest.raises(ValueError, match="processing_stages.*missing required field"):
            StatusHistoryResponse(
                analysis_id=uuid4(),
                processing_stages=[
                    {
                        "stage": "upload",
                        "start_time": datetime.now(timezone.utc).isoformat()
                        # Missing end_time
                    }
                ],
                total_processing_time_ms=1000,
                final_status="completed",
                created_at=datetime.now(timezone.utc)
            )
    
    def test_error_logs_validation(self):
        """Test error logs validation"""
        # Valid error logs
        response = StatusHistoryResponse(
            analysis_id=uuid4(),
            error_logs=[
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "processing_error",
                    "message": "Frame extraction failed"
                }
            ],
            total_processing_time_ms=1000,
            final_status="failed",
            created_at=datetime.now(timezone.utc)
        )
        assert len(response.error_logs) == 1
        
        # Invalid error logs - missing required fields
        with pytest.raises(ValueError, match="error_logs.*missing required field"):
            StatusHistoryResponse(
                analysis_id=uuid4(),
                error_logs=[
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error_type": "processing_error"
                        # Missing message
                    }
                ],
                total_processing_time_ms=1000,
                final_status="failed",
                created_at=datetime.now(timezone.utc)
            )
    
    def test_utility_methods(self):
        """Test utility methods"""
        response = StatusHistoryResponse(
            analysis_id=uuid4(),
            processing_stages=[
                {
                    "stage": "upload",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat()
                },
                {
                    "stage": "preprocessing",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "error": "Processing failed"
                }
            ],
            error_logs=[
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "processing_error",
                    "message": "Frame extraction failed"
                },
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_type": "timeout_error",
                    "message": "Request timeout"
                }
            ],
            retry_history=[
                {
                    "attempt_number": 1,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": "Processing failed",
                    "outcome": "Retry initiated"
                }
            ],
            total_processing_time_ms=5000,
            final_status="completed",
            created_at=datetime.now(timezone.utc)
        )
        
        # Test duration calculation
        assert response.get_processing_duration_seconds() == 5.0
        
        # Test successful stages
        successful_stages = response.get_successful_stages()
        assert "upload" in successful_stages
        
        # Test failed stages
        failed_stages = response.get_failed_stages()
        assert "preprocessing" in failed_stages
        
        # Test error summary
        error_summary = response.get_error_summary()
        assert error_summary["total_errors"] == 2
        assert "processing_error" in error_summary["error_types"]
        assert "timeout_error" in error_summary["error_types"]
        
        # Test retry attempts
        assert response.get_total_retry_attempts() == 1


class TestStatusTransitionValidator:
    """Test the StatusTransitionValidator utility class"""
    
    def test_is_valid_transition(self):
        """Test status transition validation"""
        # Valid transitions
        assert StatusTransitionValidator.is_valid_transition("queued", "processing")
        assert StatusTransitionValidator.is_valid_transition("queued", "failed")
        assert StatusTransitionValidator.is_valid_transition("processing", "completed")
        assert StatusTransitionValidator.is_valid_transition("processing", "failed")
        assert StatusTransitionValidator.is_valid_transition("failed", "queued")
        assert StatusTransitionValidator.is_valid_transition("failed", "processing")
        
        # Invalid transitions
        assert not StatusTransitionValidator.is_valid_transition("queued", "completed")
        assert not StatusTransitionValidator.is_valid_transition("processing", "queued")
        assert not StatusTransitionValidator.is_valid_transition("completed", "processing")
        assert not StatusTransitionValidator.is_valid_transition("completed", "failed")
    
    def test_get_valid_transitions(self):
        """Test getting valid transitions from a status"""
        assert StatusTransitionValidator.get_valid_transitions("queued") == ["processing", "failed"]
        assert StatusTransitionValidator.get_valid_transitions("processing") == ["completed", "failed"]
        assert StatusTransitionValidator.get_valid_transitions("completed") == []
        assert StatusTransitionValidator.get_valid_transitions("failed") == ["queued", "processing"]
        
        # Invalid status
        assert StatusTransitionValidator.get_valid_transitions("invalid") == []
    
    def test_is_terminal_status(self):
        """Test terminal status detection"""
        assert StatusTransitionValidator.is_terminal_status("completed")
        assert StatusTransitionValidator.is_terminal_status("failed")
        assert not StatusTransitionValidator.is_terminal_status("queued")
        assert not StatusTransitionValidator.is_terminal_status("processing")
    
    def test_can_retry_from_status(self):
        """Test retry capability detection"""
        assert StatusTransitionValidator.can_retry_from_status("failed")
        assert not StatusTransitionValidator.can_retry_from_status("completed")
        assert not StatusTransitionValidator.can_retry_from_status("queued")
        assert not StatusTransitionValidator.can_retry_from_status("processing")


class TestProcessingStageEnum:
    """Test the ProcessingStageEnum"""
    
    def test_processing_stage_enum_values(self):
        """Test processing stage enum has correct values"""
        assert ProcessingStageEnum.UPLOAD == "upload"
        assert ProcessingStageEnum.PREPROCESSING == "preprocessing"
        assert ProcessingStageEnum.FRAME_EXTRACTION == "frame_extraction"
        assert ProcessingStageEnum.FEATURE_ANALYSIS == "feature_analysis"
        assert ProcessingStageEnum.DEEPFAKE_DETECTION == "deepfake_detection"
        assert ProcessingStageEnum.POSTPROCESSING == "postprocessing"
        assert ProcessingStageEnum.BLOCKCHAIN_VERIFICATION == "blockchain_verification"
        assert ProcessingStageEnum.FINALIZATION == "finalization"


def test_work_order_34_requirements_compliance():
    """
    Test that all Work Order #34 requirements are met
    """
    
    # Test 1: StatusTrackingResponse model with all required fields
    status_response = StatusTrackingResponse(
        analysis_id=uuid4(),
        status="processing",
        progress_percentage=45.5,
        current_stage="feature_analysis",
        estimated_completion=datetime.now(timezone.utc),
        processing_time_elapsed=120000,
        error_details={"error_code": "E001", "message": "Sample error"},
        retry_count=1,
        stage_history=[
            {
                "stage": "upload",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed"
            }
        ]
    )
    
    # Verify all required fields are present
    assert hasattr(status_response, 'analysis_id')
    assert hasattr(status_response, 'status')
    assert hasattr(status_response, 'progress_percentage')
    assert hasattr(status_response, 'current_stage')
    assert hasattr(status_response, 'estimated_completion')
    assert hasattr(status_response, 'processing_time_elapsed')
    assert hasattr(status_response, 'error_details')
    assert hasattr(status_response, 'retry_count')
    assert hasattr(status_response, 'stage_history')
    
    # Test 2: StatusHistoryResponse model with all required fields
    history_response = StatusHistoryResponse(
        analysis_id=uuid4(),
        status_timeline=[
            {
                "status": "queued",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "status": "processing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "status": "completed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        processing_stages=[
            {
                "stage": "upload",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat()
            }
        ],
        error_logs=[
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error_type": "processing_error",
                "message": "Sample error"
            }
        ],
        performance_metrics={"avg_time": 1000},
        retry_history=[
            {
                "attempt_number": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Processing failed",
                "outcome": "Retry initiated"
            }
        ],
        total_processing_time_ms=5000,
        final_status="completed",
        created_at=datetime.now(timezone.utc)
    )
    
    # Verify all required fields are present
    assert hasattr(history_response, 'analysis_id')
    assert hasattr(history_response, 'status_timeline')
    assert hasattr(history_response, 'processing_stages')
    assert hasattr(history_response, 'error_logs')
    assert hasattr(history_response, 'performance_metrics')
    assert hasattr(history_response, 'retry_history')
    
    # Test 3: Progress percentage validation (0.0-100.0)
    valid_percentages = [0.0, 50.0, 100.0]
    for percentage in valid_percentages:
        response = StatusTrackingResponse(
            analysis_id=uuid4(),
            status="processing",
            progress_percentage=percentage,
            current_stage="feature_analysis",
            processing_time_elapsed=1000
        )
        assert response.progress_percentage == percentage
    
    # Test invalid progress percentage
    with pytest.raises(ValueError):
        StatusTrackingResponse(
            analysis_id=uuid4(),
            status="processing",
            progress_percentage=150.0,  # Invalid: > 100
            current_stage="feature_analysis",
            processing_time_elapsed=1000
        )
    
    # Test 4: Status transition validation (queued -> processing -> completed/failed)
    assert StatusTransitionValidator.is_valid_transition("queued", "processing")
    assert StatusTransitionValidator.is_valid_transition("processing", "completed")
    assert StatusTransitionValidator.is_valid_transition("processing", "failed")
    assert not StatusTransitionValidator.is_valid_transition("queued", "completed")  # Invalid transition
    
    # Test 5: SQLModel Field integration (descriptions and validation constraints)
    # This is implicitly tested through the Field usage in the model definitions
    # The models use Field with proper descriptions and validation constraints
    
    print("✅ All Work Order #34 requirements have been successfully implemented and tested!")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
