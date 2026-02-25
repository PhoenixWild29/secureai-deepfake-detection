#!/usr/bin/env python3
"""
Analysis History Service
Business logic service for retrieving, aggregating, and formatting analysis history data.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from app.schemas.detection import (
    AnalysisHistoryRecord,
    ProcessingStageHistory,
    ErrorLogEntry,
    RetryAttemptRecord,
    PerformanceMetricsHistory,
    HistoryFilterOptions,
    HistorySortOptions,
    HistoryPaginationOptions,
    AnalysisHistoryResponse,
    DetectionStatus
)
from app.utils.redis_client import get_progress_tracker_redis

logger = logging.getLogger(__name__)


class AnalysisHistoryService:
    """
    Service for managing analysis history data with Redis caching and business logic.
    Provides comprehensive audit trail and analysis tracking capabilities.
    """
    
    def __init__(self):
        """Initialize the analysis history service"""
        self.redis_client = get_progress_tracker_redis()
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.max_history_records = 1000  # Maximum records to return
    
    async def get_analysis_history(
        self,
        analysis_id: UUID,
        filters: Optional[HistoryFilterOptions] = None,
        sort_options: Optional[HistorySortOptions] = None,
        pagination: Optional[HistoryPaginationOptions] = None
    ) -> AnalysisHistoryResponse:
        """
        Get comprehensive analysis history with filtering, sorting, and pagination.
        
        Args:
            analysis_id: Analysis identifier
            filters: Optional filtering options
            sort_options: Optional sorting options
            pagination: Optional pagination options
            
        Returns:
            AnalysisHistoryResponse: Complete history response with metadata
        """
        start_time = time.time()
        
        try:
            logger.info(f"Retrieving analysis history for {analysis_id}")
            
            # Set default pagination if not provided
            if not pagination:
                pagination = HistoryPaginationOptions(page=1, page_size=50)
            
            # Set default sort options if not provided
            if not sort_options:
                sort_options = HistorySortOptions(sort_field="record_timestamp", sort_order="desc")
            
            # Retrieve history records from Redis
            history_records = await self.redis_client.retrieve_analysis_history(
                analysis_id=analysis_id,
                filters=filters,
                sort_options=sort_options,
                pagination=pagination
            )
            
            # Get total count for pagination
            total_records = await self._get_total_history_count(analysis_id, filters)
            
            # Calculate pagination metadata
            total_pages = (total_records + pagination.page_size - 1) // pagination.page_size
            current_page = pagination.page
            has_next_page = current_page < total_pages
            has_previous_page = current_page > 1
            
            # Get summary metrics
            summary_metrics = await self.redis_client.get_history_summary_metrics(analysis_id)
            
            # Get cache information
            cache_info = await self._get_cache_info(analysis_id)
            
            # Create response
            response = AnalysisHistoryResponse(
                analysis_id=analysis_id,
                total_records=total_records,
                current_page=current_page,
                total_pages=total_pages,
                page_size=pagination.page_size,
                has_next_page=has_next_page,
                has_previous_page=has_previous_page,
                history_records=history_records,
                summary_metrics=summary_metrics,
                cache_info=cache_info,
                generated_at=datetime.now(timezone.utc)
            )
            
            # Log performance
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Analysis history retrieved for {analysis_id} in {processing_time:.2f}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to retrieve analysis history for {analysis_id}: {e}")
            # Return empty response on error
            return AnalysisHistoryResponse(
                analysis_id=analysis_id,
                total_records=0,
                current_page=1,
                total_pages=1,
                page_size=pagination.page_size if pagination else 50,
                has_next_page=False,
                has_previous_page=False,
                history_records=[],
                summary_metrics=None,
                cache_info={"status": "error", "error": str(e)},
                generated_at=datetime.now(timezone.utc)
            )
    
    async def create_sample_history_record(self, analysis_id: UUID) -> AnalysisHistoryRecord:
        """
        Create a sample history record for testing and demonstration purposes.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            AnalysisHistoryRecord: Sample history record
        """
        try:
            # Create sample processing stages
            processing_stages = [
                ProcessingStageHistory(
                    stage_name="uploading",
                    stage_status="completed",
                    stage_start_time=datetime.now(timezone.utc),
                    stage_end_time=datetime.now(timezone.utc),
                    stage_duration_seconds=5.2,
                    stage_completion_percentage=100.0,
                    frames_processed=None,
                    total_frames=None,
                    processing_rate_fps=None,
                    resource_usage={"cpu_percent": 10.5, "memory_mb": 256.0},
                    stage_metadata={"file_size_mb": 15.2, "upload_method": "multipart"}
                ),
                ProcessingStageHistory(
                    stage_name="preprocessing",
                    stage_status="completed",
                    stage_start_time=datetime.now(timezone.utc),
                    stage_end_time=datetime.now(timezone.utc),
                    stage_duration_seconds=12.8,
                    stage_completion_percentage=100.0,
                    frames_processed=300,
                    total_frames=300,
                    processing_rate_fps=23.4,
                    resource_usage={"cpu_percent": 45.2, "memory_mb": 1024.0},
                    stage_metadata={"video_duration_seconds": 12.5, "fps": 24.0}
                ),
                ProcessingStageHistory(
                    stage_name="detection_analysis",
                    stage_status="completed",
                    stage_start_time=datetime.now(timezone.utc),
                    stage_end_time=datetime.now(timezone.utc),
                    stage_duration_seconds=45.6,
                    stage_completion_percentage=100.0,
                    frames_processed=300,
                    total_frames=300,
                    processing_rate_fps=6.6,
                    resource_usage={"cpu_percent": 78.5, "memory_mb": 2048.0, "gpu_percent": 85.2},
                    stage_metadata={"model_version": "v2.1.0", "confidence_threshold": 0.8}
                )
            ]
            
            # Create sample error logs
            error_logs = [
                ErrorLogEntry(
                    error_id="err_001",
                    error_type="validation",
                    error_code="INVALID_VIDEO_FORMAT",
                    error_message="Video format validation failed",
                    error_details={"detected_format": "unknown", "supported_formats": ["mp4", "avi", "mov"]},
                    affected_stage="preprocessing",
                    timestamp=datetime.now(timezone.utc),
                    severity="warning",
                    recovery_action="Attempted format conversion",
                    context={"user_agent": "Mozilla/5.0", "file_extension": ".mkv"}
                )
            ]
            
            # Create sample retry attempts
            retry_attempts = [
                RetryAttemptRecord(
                    retry_attempt_number=1,
                    retry_reason="Network timeout during model loading",
                    retry_timestamp=datetime.now(timezone.utc),
                    retry_duration_seconds=3.2,
                    retry_outcome="success",
                    retry_error=None,
                    retry_metadata={"retry_delay_seconds": 5, "model_cache_hit": False}
                )
            ]
            
            # Create sample performance metrics
            performance_metrics = [
                PerformanceMetricsHistory(
                    timestamp=datetime.now(timezone.utc),
                    total_processing_time_seconds=63.6,
                    stage_processing_times={
                        "uploading": 5.2,
                        "preprocessing": 12.8,
                        "detection_analysis": 45.6
                    },
                    throughput_fps=4.7,
                    cpu_usage_percent=65.8,
                    memory_usage_mb=2048.0,
                    gpu_usage_percent=85.2,
                    disk_io_mb=120.5,
                    network_io_mb=15.2,
                    efficiency_score=0.82
                )
            ]
            
            # Create the complete history record
            history_record = AnalysisHistoryRecord(
                analysis_id=analysis_id,
                record_timestamp=datetime.now(timezone.utc),
                analysis_status=DetectionStatus.COMPLETED,
                processing_stages=processing_stages,
                error_logs=error_logs,
                retry_attempts=retry_attempts,
                performance_metrics=performance_metrics,
                total_processing_time_seconds=63.6,
                total_errors=1,
                total_retries=1,
                success_rate=1.0,
                analysis_metadata={
                    "video_file_size_mb": 15.2,
                    "video_duration_seconds": 12.5,
                    "detection_methods": ["resnet50", "clip"],
                    "blockchain_verified": True,
                    "user_id": "sample_user_123"
                }
            )
            
            logger.debug(f"Created sample history record for analysis {analysis_id}")
            return history_record
            
        except Exception as e:
            logger.error(f"Failed to create sample history record for {analysis_id}: {e}")
            raise
    
    async def store_history_record(self, analysis_id: UUID, history_record: AnalysisHistoryRecord) -> bool:
        """
        Store a history record in Redis.
        
        Args:
            analysis_id: Analysis identifier
            history_record: History record to store
            
        Returns:
            bool: True if successful
        """
        try:
            success = await self.redis_client.store_analysis_history(analysis_id, history_record)
            
            if success:
                logger.info(f"Stored history record for analysis {analysis_id}")
            else:
                logger.error(f"Failed to store history record for analysis {analysis_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing history record for {analysis_id}: {e}")
            return False
    
    async def get_history_statistics(self, analysis_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive statistics for analysis history.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Dict[str, Any]: History statistics
        """
        try:
            # Get summary metrics
            summary_metrics = await self.redis_client.get_history_summary_metrics(analysis_id)
            
            # Get additional statistics
            all_records = await self.redis_client.retrieve_analysis_history(analysis_id)
            
            if not all_records:
                return {"message": "No history records found"}
            
            # Calculate additional statistics
            error_types = {}
            error_type_distribution = {}
            stage_performance = {}
            time_trends = []
            
            for record in all_records:
                # Error type distribution
                for error in record.error_logs:
                    error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
                    error_type_distribution[error.error_type] = error_type_distribution.get(error.error_type, 0) + 1
                
                # Stage performance analysis
                for stage in record.processing_stages:
                    if stage.stage_name not in stage_performance:
                        stage_performance[stage.stage_name] = {
                            "avg_duration": 0,
                            "count": 0,
                            "success_rate": 0
                        }
                    
                    stage_perf = stage_performance[stage.stage_name]
                    stage_perf["count"] += 1
                    if stage.stage_duration_seconds:
                        stage_perf["avg_duration"] = (
                            (stage_perf["avg_duration"] * (stage_perf["count"] - 1) + stage.stage_duration_seconds) 
                            / stage_perf["count"]
                        )
                    
                    if stage.stage_status == "completed":
                        stage_perf["success_rate"] = (
                            (stage_perf["success_rate"] * (stage_perf["count"] - 1) + 1) 
                            / stage_perf["count"]
                        )
                
                # Time trends
                time_trends.append({
                    "timestamp": record.record_timestamp,
                    "processing_time": record.total_processing_time_seconds,
                    "errors": record.total_errors,
                    "status": record.analysis_status.value
                })
            
            statistics = {
                "summary": summary_metrics,
                "error_type_distribution": error_type_distribution,
                "stage_performance": stage_performance,
                "time_trends": time_trends[-10:],  # Last 10 records for trends
                "total_history_records": len(all_records),
                "analysis_id": str(analysis_id),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug(f"Generated history statistics for analysis {analysis_id}")
            return statistics
            
        except Exception as e:
            logger.error(f"Failed to generate history statistics for {analysis_id}: {e}")
            return {"error": str(e)}
    
    async def _get_total_history_count(self, analysis_id: UUID, filters: Optional[HistoryFilterOptions] = None) -> int:
        """
        Get total count of history records for pagination.
        
        Args:
            analysis_id: Analysis identifier
            filters: Optional filtering options
            
        Returns:
            int: Total number of records
        """
        try:
            # Get all records and count them
            all_records = await self.redis_client.retrieve_analysis_history(analysis_id)
            
            # Apply filters if provided
            if filters:
                filtered_records = self.redis_client._apply_history_filters(all_records, filters)
                return len(filtered_records)
            
            return len(all_records)
            
        except Exception as e:
            logger.error(f"Failed to get total history count for {analysis_id}: {e}")
            return 0
    
    async def _get_cache_info(self, analysis_id: UUID) -> Dict[str, Any]:
        """
        Get Redis cache information for the analysis.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Dict[str, Any]: Cache information
        """
        try:
            # Get Redis health info
            redis_health = await self.redis_client.get_redis_health()
            
            cache_info = {
                "redis_status": redis_health.get("status", "unknown"),
                "response_time_ms": redis_health.get("response_time_ms"),
                "cache_ttl_seconds": self.cache_ttl,
                "analysis_id": str(analysis_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return cache_info
            
        except Exception as e:
            logger.error(f"Failed to get cache info for {analysis_id}: {e}")
            return {
                "redis_status": "error",
                "error": str(e),
                "analysis_id": str(analysis_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Factory function
def get_analysis_history_service() -> AnalysisHistoryService:
    """
    Factory function to create AnalysisHistoryService instance.
    
    Returns:
        AnalysisHistoryService instance
    """
    return AnalysisHistoryService()
