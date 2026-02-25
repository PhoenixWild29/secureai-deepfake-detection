#!/usr/bin/env python3
"""
Redis Client Utilities for Detailed Progress Tracking
Utility functions for storing and retrieving detailed analysis progress data in Redis.
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID
import redis.asyncio as redis
from redis.asyncio import Redis

from app.schemas.detection import (
    ProcessingStageDetails,
    FrameProgressInfo,
    ErrorRecoveryStatus,
    ProcessingMetrics,
    DetailedDetectionStatusResponse,
    AnalysisHistoryRecord,
    ProcessingStageHistory,
    ErrorLogEntry,
    RetryAttemptRecord,
    PerformanceMetricsHistory,
    HistoryFilterOptions,
    HistorySortOptions,
    HistoryPaginationOptions,
    AnalysisHistoryResponse
)

logger = logging.getLogger(__name__)


class ProgressTrackerRedis:
    """
    Redis client for storing and retrieving detailed progress tracking data.
    Provides efficient key structure and caching for sub-100ms response times.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis_client = redis_client or self._create_redis_client()
        self.default_ttl = 3600  # 1 hour default TTL
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.key_prefix = "detection_progress"
    
    def _create_redis_client(self) -> Redis:
        """Create Redis client with appropriate configuration"""
        try:
            return redis.from_url(
                "redis://localhost:6379/0",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            raise
    
    def _get_main_key(self, analysis_id: UUID) -> str:
        """Get main Redis key for analysis progress"""
        return f"{self.key_prefix}:analysis:{analysis_id}"
    
    def _get_locks_key(self, analysis_id: UUID) -> str:
        """Get Redis key for progress update locks"""
        return f"{self.key_prefix}:lock:{analysis_id}"
    
    def _get_history_key(self, analysis_id: UUID) -> str:
        """Get Redis key for progress history"""
        return f"{self.key_prefix}:history:{analysis_id}"
    
    async def store_detailed_progress(
        self,
        analysis_id: UUID,
        stage_details: Optional[ProcessingStageDetails] = None,
        frame_progress: Optional[FrameProgressInfo] = None,
        error_recovery: Optional[ErrorRecoveryStatus] = None,
        processing_metrics: Optional[ProcessingMetrics] = None,
        progress_history_entry: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store detailed progress data for an analysis in Redis.
        
        Args:
            analysis_id: Analysis ID
            stage_details: Processing stage details
            frame_progress: Frame progress information
            error_recovery: Error recovery status
            processing_metrics: Processing performance metrics
            progress_history_entry: Historical progress data entry
            
        Returns:
            True if successful, False otherwise
        """
        try:
            main_key = self._get_main_key(analysis_id)
            
            # Prepare data structure
            progress_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "updated_at": time.time()
            }
            
            # Add optional data sections
            if stage_details:
                progress_data["stage_details"] = stage_details.model_dump()
            
            if frame_progress:
                progress_data["frame_progress"] = frame_progress.model_dump()
                # Calculate derived metrics
                progress_data["derived_metrics"] = self._calculate_derived_metrics(frame_progress)
            
            if error_recovery:
                progress_data["error_recovery"] = error_recovery.model_dump()
            
            if processing_metrics:
                progress_data["processing_metrics"] = processing_metrics.model_dump()
            
            # Convert to JSON string
            json_data = json.dumps(progress_data)
            
            # Store in Redis with TTL
            pipe = self.redis_client.pipeline()
            pipe.hset(main_key, mapping={
                "latest_data": json_data,
                "last_update": str(time.time()),
                "analysis_id": str(analysis_id)
            })
            pipe.expire(main_key, self.default_ttl)
            
            await pipe.execute()
            
            # Store progress history if provided
            if progress_history_entry:
                await self._store_progress_history(analysis_id, progress_history_entry)
            
            logger.debug(f"Stored detailed progress for analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store progress for analysis {analysis_id}: {e}")
            return False
    
    async def retrieve_detailed_progress(self, analysis_id: UUID) -> Optional[DetailedDetectionStatusResponse]:
        """
        Retrieve detailed progress data for an analysis from Redis.
        Optimized for sub-100ms response times.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            DetailedDetectionStatusResponse or None if not found
        """
        try:
            main_key = self._get_main_key(analysis_id)
            
            # Retrieve all progress data
            progress_data_raw = await self.redis_client.hgetall(main_key)
            
            if not progress_data_raw:
                logger.debug(f"No progress data found for analysis {analysis_id}")
                return None
            
            # Parse JSON data
            json_data = progress_data_raw.get("latest_data")
            if not json_data:
                return None
            
            progress_data = json.loads(json_data)
            
            # Build DetailedDetectionStatusResponse
            detailed_response = await self._build_detailed_response(analysis_id, progress_data, progress_data_raw)
            
            logger.debug(f"Retrieved detailed progress for analysis {analysis_id} in {time.time() - float(progress_data_raw.get('last_update', time.time())):.3f}s")
            return detailed_response
            
        except Exception as e:
            logger.error(f"Failed to retrieve progress for analysis {analysis_id}: {e}")
            return None
    
    async def store_frame_progress(
        self,
        analysis_id: UUID,
        current_frame: int,
        total_frames: int,
        processing_rate: Optional[float] = None,
        stage_name: Optional[str] = None
    ) -> bool:
        """
        Store frame-level progress quickly for frequent updates.
        
        Args:
            analysis_id: Analysis ID
            current_frame: Current frame number
            total_frames: Total frames to process
            processing_rate: Frames per second
            stage_name: Current stage name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            frame_progress = FrameProgressInfo(
                current_frame_number=current_frame,
                total_frames=total_frames,
                frames_processed=current_frame,
                frame_processing_rate=processing_rate,
                estimated_remaining_frames=total_frames - current_frame,
                progress_trend="accelerating" if processing_rate and processing_rate > 10 else "stable"
            )
            
            if stage_name:
                stage_details = ProcessingStageDetails(
                    stage_name=stage_name,
                    stage_status="active",
                    stage_completion_percentage=(current_frame / total_frames) * 100,
                    stage_frames_processed=current_frame,
                    stage_total_frames=total_frames
                )
            else:
                stage_details = None
            
            # Store with minimal data for fast updates
            return await self.store_detailed_progress(
                analysis_id=analysis_id,
                frame_progress=frame_progress,
                stage_details=stage_details
            )
            
        except Exception as e:
            logger.error(f"Failed to store frame progress for analysis {analysis_id}: {e}")
            return False
    
    async def store_error_recovery(
        self,
        analysis_id: UUID,
        error_type: str,
        error_message: str,
        retry_count: int,
        recovery_action: Optional[str] = None,
        is_recoving: bool = False
    ) -> bool:
        """
        Store error recovery status for an analysis.
        
        Args:
            analysis_id: Analysis ID
            error_type: Type of error encountered
            error_message: Error message
            retry_count: Current retry attempt number
            recovery_action: Action taken for recovery
            is_recovering: Whether currently in recovery mode
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing error recovery data
            existing_data = await self.redis_client.hget(self._get_main_key(analysis_id), "error_recovery")
            existing_recovery = None
            
            if existing_data:
                try:
                    error_data = json.loads(existing_data)
                    existing_recovery = ErrorRecoveryStatus(**error_data)
                except Exception:
                    existing_recovery = None
            
            # Build updated error recovery status
            if existing_recovery:
                error_recovery = ErrorRecoveryStatus(
                    has_errors=True,
                    error_count=existing_recovery.error_count + 1,
                    retry_attempts=retry_count,
                    max_retries=existing_recovery.max_retries,
                    last_error_type=error_type,
                    last_error_message=error_message,
                    last_error_timestamp=datetime.now(timezone.utc),
                    recovery_actions_taken=existing_recovery.recovery_actions_taken + ([recovery_action] if recovery_action else []),
                    is_recovering=is_recovering
                )
            else:
                error_recovery = ErrorRecoveryStatus(
                    has_errors=True,
                    error_count=1,
                    retry_attempts=retry_count,
                    max_retries=3,
                    last_error_type=error_type,
                    last_error_message=error_message,
                    last_error_timestamp=datetime.now(timezone.utc),
                    recovery_actions_taken=[recovery_action] if recovery_action else [],
                    is_recovering=is_recovering
                )
            
            return await self.store_detailed_progress(
                analysis_id=analysis_id,
                error_recovery=error_recovery
            )
            
        except Exception as e:
            logger.error(f"Failed to store error recovery for analysis {analysis_id}: {e}")
            return False
    
    async def store_processing_metrics(
        self,
        analysis_id: UUID,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        worker_id: Optional[str] = None,
        queue_wait_time: Optional[float] = None,
        efficiency_score: Optional[float] = None
    ) -> bool:
        """
        Store processing performance metrics.
        
        Args:
            analysis_id: Analysis ID
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage in MB
            worker_id: Worker ID processing the analysis
            queue_wait_time: Time spent waiting in queue
            efficiency_score: Processing efficiency score
            
        Returns:
            True if successful, False otherwise
        """
        try:
            processing_metrics = ProcessingMetrics(
                cpu_usage_percent=cpu_usage,
                memory_usage_mb=memory_usage,
                worker_id=worker_id,
                queue_wait_time_seconds=queue_wait_time,
                processing_efficiency=efficiency_score
            )
            
            return await self.store_detailed_progress(
                analysis_id=analysis_id,
                processing_metrics=processing_metrics
            )
            
        except Exception as e:
            logger.error(f"Failed to store processing metrics for analysis {analysis_id}: {e}")
            return False
    
    async def _store_progress_history(self, analysis_id: UUID, history_entry: Dict[str, Any]) -> bool:
        """Store progress history entry"""
        try:
            history_key = self._get_history_key(analysis_id)
            
            # Add timestamp if not present
            if "timestamp" not in history_entry:
                history_entry["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Store in Redis list (keep last 100 entries)
            await self.redis_client.lpush(history_key, json.dumps(history_entry))
            await self.redis_client.ltrim(history_key, 0, 99)  # Keep last 100 entries
            await self.redis_client.expire(history_key, self.default_ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store progress history for analysis {analysis_id}: {e}")
            return False
    
    async def _build_detailed_response(
        self, 
        analysis_id: UUID, 
        progress_data: Dict[str, Any], 
        raw_data: Dict[str, str]
    ) -> DetailedDetectionStatusResponse:
        """Build DetailedDetectionStatusResponse from Redis data"""
        
        # Parse structured data
        stage_details = None
        if "stage_details" in progress_data:
            stage_details = ProcessingStageDetails(**progress_data["stage_details"])
        
        frame_progress = None
        if "frame_progress" in progress_data:
            frame_progress = FrameProgressInfo(**progress_data["frame_progress"])
        
        error_recovery = None
        if "error_recovery" in progress_data:
            error_recovery = ErrorRecoveryStatus(**progress_data["error_recovery"])
        
        processing_metrics = None
        if "processing_metrics" in progress_data:
            processing_metrics = ProcessingMetrics(**progress_data["processing_metrics"])
        
        # Get progress history
        progress_history = await self._get_progress_history(analysis_id)
        
        # Calculate overall progress percentage
        progress_percentage = self._calculate_overall_progress(frame_progress)
        
        # Determine current stage
        current_stage = self._determine_current_stage(stage_details, frame_progress)
        
        # Get processing time
        processing_time = self._calculate_processing_time(raw_data.get("last_update"))
        
        # Build response
        response = DetailedDetectionStatusResponse(
            analysis_id=analysis_id,
            status=self._determine_status(stage_details, frame_progress, error_recovery),
            progress_percentage=progress_percentage,
            current_stage=current_stage,
            estimated_completion=self._estimate_completion(frame_progress),
            processing_time_seconds=processing_time,
            frames_processed=frame_progress.frames_processed if frame_progress else 0,
            total_frames=frame_progress.total_frames if frame_progress else None,
            error_message=error_recovery.last_error_message if error_recovery and error_recovery.has_errors else None,
            last_updated=datetime.fromisoformat(progress_data["timestamp"]),
            processing_stage_details=stage_details,
            frame_progress_info=frame_progress,
            error_recovery_status=error_recovery,
            processing_metrics=processing_metrics,
            progress_history=progress_history
        )
        
        return response
    
    def _calculate_derived_metrics(self, frame_progress: FrameProgressInfo) -> Dict[str, Any]:
        """Calculate derived metrics from frame progress"""
        return {
            "completion_percentage": (frame_progress.frames_processed / frame_progress.total_frames) * 100,
            "estimated_completion_time": self._estimate_completion(frame_progress),
            "processing_efficiency": self._calculate_process_efficiency(frame_progress),
            "progress_trend": frame_progress.progress_trend
        }
    
    def _calculate_overall_progress(self, frame_progress: Optional[FrameProgressInfo]) -> float:
        """Calculate overall progress percentage"""
        if not frame_progress:
            return 0.0
        return (frame_progress.frames_processed / frame_progress.total_frames) * 100
    
    def _determine_current_stage(self, stage_details: Optional[ProcessingStageDetails], frame_progress: Optional[FrameProgressInfo]) -> str:
        """Determine current processing stage"""
        if stage_details:
            return stage_details.stage_name
        elif frame_progress and frame_progress.frames_processed == 0:
            return "initialization"
        elif frame_progress and frame_progress.frames_processed < frame_progress.total_frames:
            return "processing"
        elif frame_progress and frame_progress.frames_processed >= frame_progress.total_frames:
            return "finalization"
        return "unknown"
    
    def _determine_status(self, stage_details, frame_progress, error_recovery) -> str:
        """Determine overall status"""
        if error_recovery and error_recovery.has_errors:
            return "failed" if error_recovery.retry_attempts >= error_recovery.max_retries else "processing"
        elif frame_progress and frame_progress.frames_processed < frame_progress.total_frames:
            return "processing"
        elif frame_progress and frame_progress.frames_processed >= frame_progress.total_frames:
            return "completed"
        return "pending"
    
    def _calculate_processing_time(self, last_update: Optional[str]) -> Optional[float]:
        """Calculate processing time"""
        if not last_update:
            return None
        return time.time() - float(last_update)
    
    def _estimate_completion(self, frame_progress: Optional[FrameProgressInfo]) -> Optional[datetime]:
        """Estimate completion time"""
        if not frame_progress or not frame_progress.frame_processing_rate:
            return None
        
        remaining_frames = frame_progress.total_frames - frame_progress.frames_processed
        if remaining_frames <= 0:
            return datetime.now(timezone.utc)
        
        time_to_completion = remaining_frames / frame_progress.frame_processing_rate
        return datetime.now(timezone.utc) + timedelta(seconds=time_to_completion)
    
    def _calculate_process_efficiency(self, frame_progress: FrameProgressInfo) -> float:
        """Calculate processing efficiency score"""
        base_efficiency = 0.5
        
        # Increase efficiency with higher processing rate
        if frame_progress.frame_processing_rate:
            if frame_progress.frame_processing_rate > 20:
                base_efficiency += 0.3
            elif frame_progress.frame_processing_rate > 10:
                base_efficiency += 0.2
            elif frame_progress.frame_processing_rate > 5:
                base_efficiency += 0.1
        
        # Adjust based on progress trend
        if frame_progress.progress_trend == "accelerating":
            base_efficiency += 0.1
        elif frame_progress.progress_trend == "decelerating":
            base_efficiency -= 0.1
        
        return max(0.0, min(1.0, base_efficiency))
    
    async def _get_progress_history(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get progress history for analysis"""
        try:
            history_key = self._get_history_key(analysis_id)
            history_data = await self.redis_client.lrange(history_key, 0, 99)
            
            history = []
            for entry in history_data:
                try:
                    history.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to retrieve progress history for analysis {analysis_id}: {e}")
            return []
    
    async def clear_progress_data(self, analysis_id: UUID) -> bool:
        """Clear all progress data for an analysis"""
        try:
            main_key = self._get_main_key(analysis_id)
            history_key = self._get_history_key(analysis_id)
            
            pipe = self.redis_client.pipeline()
            pipe.delete(main_key)
            pipe.delete(history_key)
            
            await pipe.execute()
            
            logger.info(f"Cleared all progress data for analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear progress data for analysis {analysis_id}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Redis connection"""
        try:
            start_time = time.time()
            await self.redis_client.ping()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "redis_version": await self.redis_client.info("server").get("redis_version", "unknown")
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": None
            }
    
    # History-specific methods for audit trail and analysis tracking
    async def store_analysis_history(self, analysis_id: UUID, history_record: AnalysisHistoryRecord) -> bool:
        """
        Store analysis history record in Redis with automatic cleanup.
        
        Args:
            analysis_id: Analysis identifier
            history_record: Complete history record to store
            
        Returns:
            bool: True if successful
        """
        try:
            history_key = self._get_history_record_key(analysis_id, history_record.record_timestamp)
            
            # Store the history record
            await self.redis_client.setex(
                history_key,
                self.default_ttl * 24,  # 24 hours for history records
                json.dumps(history_record.dict(), default=str)
            )
            
            # Add to sorted set for time-based queries
            history_index_key = self._get_history_index_key(analysis_id)
            await self.redis_client.zadd(
                history_index_key,
                {history_key: history_record.record_timestamp.timestamp()}
            )
            await self.redis_client.expire(history_index_key, self.default_ttl * 24)
            
            logger.debug(f"Stored analysis history record for {analysis_id} at {history_record.record_timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store analysis history for {analysis_id}: {e}")
            return False
    
    async def retrieve_analysis_history(
        self, 
        analysis_id: UUID,
        filters: Optional[HistoryFilterOptions] = None,
        sort_options: Optional[HistorySortOptions] = None,
        pagination: Optional[HistoryPaginationOptions] = None
    ) -> List[AnalysisHistoryRecord]:
        """
        Retrieve analysis history records with filtering, sorting, and pagination.
        
        Args:
            analysis_id: Analysis identifier
            filters: Optional filtering options
            sort_options: Optional sorting options
            pagination: Optional pagination options
            
        Returns:
            List[AnalysisHistoryRecord]: Filtered and paginated history records
        """
        try:
            history_index_key = self._get_history_index_key(analysis_id)
            
            # Get all history record keys for this analysis
            record_keys = await self.redis_client.zrevrange(history_index_key, 0, -1)
            
            if not record_keys:
                return []
            
            # Retrieve history records
            history_records = []
            for key in record_keys:
                try:
                    record_data = await self.redis_client.get(key)
                    if record_data:
                        record_dict = json.loads(record_data)
                        history_records.append(AnalysisHistoryRecord(**record_dict))
                except Exception as e:
                    logger.warning(f"Failed to parse history record {key}: {e}")
                    continue
            
            # Apply filters
            if filters:
                history_records = self._apply_history_filters(history_records, filters)
            
            # Apply sorting
            if sort_options:
                history_records = self._apply_history_sorting(history_records, sort_options)
            
            # Apply pagination
            if pagination:
                start_idx = (pagination.page - 1) * pagination.page_size
                end_idx = start_idx + pagination.page_size
                history_records = history_records[start_idx:end_idx]
            
            logger.debug(f"Retrieved {len(history_records)} history records for analysis {analysis_id}")
            return history_records
            
        except Exception as e:
            logger.error(f"Failed to retrieve analysis history for {analysis_id}: {e}")
            return []
    
    async def get_history_summary_metrics(self, analysis_id: UUID) -> Dict[str, Any]:
        """
        Get summary metrics for analysis history.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Dict[str, Any]: Summary metrics
        """
        try:
            history_records = await self.retrieve_analysis_history(analysis_id)
            
            if not history_records:
                return {}
            
            # Calculate summary metrics
            total_records = len(history_records)
            total_errors = sum(record.total_errors for record in history_records)
            total_retries = sum(record.total_retries for record in history_records)
            
            # Processing time statistics
            processing_times = [
                record.total_processing_time_seconds 
                for record in history_records 
                if record.total_processing_time_seconds
            ]
            
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            min_processing_time = min(processing_times) if processing_times else 0
            max_processing_time = max(processing_times) if processing_times else 0
            
            # Success rate calculation
            successful_analyses = len([r for r in history_records if r.analysis_status.value == "completed"])
            success_rate = successful_analyses / total_records if total_records > 0 else 0
            
            summary = {
                "total_records": total_records,
                "total_errors": total_errors,
                "total_retries": total_retries,
                "success_rate": success_rate,
                "avg_processing_time_seconds": avg_processing_time,
                "min_processing_time_seconds": min_processing_time,
                "max_processing_time_seconds": max_processing_time
            }
            
            logger.debug(f"Generated history summary metrics for analysis {analysis_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate history summary metrics for {analysis_id}: {e}")
            return {}
    
    def _get_history_record_key(self, analysis_id: UUID, timestamp: datetime) -> str:
        """Generate Redis key for history record"""
        return f"{self.key_prefix}:history:record:{analysis_id}:{timestamp.isoformat()}"
    
    def _get_history_index_key(self, analysis_id: UUID) -> str:
        """Generate Redis key for history index"""
        return f"{self.key_prefix}:history:index:{analysis_id}"
    
    def _apply_history_filters(self, records: List[AnalysisHistoryRecord], filters: HistoryFilterOptions) -> List[AnalysisHistoryRecord]:
        """Apply filters to history records"""
        filtered_records = records
        
        # Date filters
        if filters.start_date:
            filtered_records = [
                r for r in filtered_records 
                if r.record_timestamp >= filters.start_date
            ]
        
        if filters.end_date:
            filtered_records = [
                r for r in filtered_records 
                if r.record_timestamp <= filters.end_date
            ]
        
        # Status filter
        if filters.status_filter:
            filtered_records = [
                r for r in filtered_records 
                if r.analysis_status in filters.status_filter
            ]
        
        return filtered_records
    
    def _apply_history_sorting(self, records: List[AnalysisHistoryRecord], sort_options: HistorySortOptions) -> List[AnalysisHistoryRecord]:
        """Apply sorting to history records"""
        reverse = sort_options.sort_order.lower() == "desc"
        
        if sort_options.sort_field == "record_timestamp":
            return sorted(records, key=lambda r: r.record_timestamp, reverse=reverse)
        elif sort_options.sort_field == "total_processing_time_seconds":
            return sorted(records, key=lambda r: r.total_processing_time_seconds or 0, reverse=reverse)
        elif sort_options.sort_field == "total_errors":
            return sorted(records, key=lambda r: r.total_errors, reverse=reverse)
        else:
            # Default to timestamp sorting
            return sorted(records, key=lambda r: r.record_timestamp, reverse=reverse)


# Factory function
def get_progress_tracker_redis(redis_client: Optional[Redis] = None) -> ProgressTrackerRedis:
    """
    Factory function to create ProgressTrackerRedis instance.
    
    Args:
        redis_client: Optional Redis client instance
        
    Returns:
        ProgressTrackerRedis instance
    """
    return ProgressTrackerRedis(redis_client)
