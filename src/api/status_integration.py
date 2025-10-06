#!/usr/bin/env python3
"""
Status API Integration Implementation
Work Order #31 - WebSocket Status API Integration

This module integrates the status tracking models with the WebSocket API
and provides database integration for real-time status updates.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from enum import Enum

from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

# Import existing models
from src.core_models.models import Analysis, AnalysisStatusEnum

class StatusTrackingResponse(BaseModel):
    """Status tracking response model"""
    analysis_id: UUID
    status: str
    progress_percentage: float
    current_stage: str
    estimated_completion: Optional[datetime] = None
    processing_time_elapsed: int
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    stage_history: List[Dict[str, Any]]
    processing_metadata: Dict[str, Any] = {}
    last_updated: datetime

class StatusHistoryResponse(BaseModel):
    """Status history response model"""
    analysis_id: UUID
    status_timeline: List[Dict[str, Any]]
    processing_stages: List[Dict[str, Any]]
    error_logs: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    retry_history: List[Dict[str, Any]]
    total_processing_time_ms: int
    final_status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

class ProcessingStageEnum(str, Enum):
    """Processing stage enumeration"""
    UPLOAD = "upload"
    PREPROCESSING = "preprocessing"
    FRAME_EXTRACTION = "frame_extraction"
    FEATURE_ANALYSIS = "feature_analysis"
    DEEPFAKE_DETECTION = "deepfake_detection"
    POSTPROCESSING = "postprocessing"
    BLOCKCHAIN_VERIFICATION = "blockchain_verification"
    FINALIZATION = "finalization"

class StatusTransitionValidator:
    """Status transition validator"""
    
    def is_valid_transition(self, from_status: str, to_status: str) -> bool:
        """Check if status transition is valid"""
        valid_transitions = {
            "queued": ["processing", "failed"],
            "processing": ["completed", "failed"],
            "completed": [],
            "failed": ["queued", "processing"]
        }
        return to_status in valid_transitions.get(from_status, [])
from src.services.redis_pubsub_service import get_redis_pubsub_service
from src.services.status_broadcast_service import StatusBroadcastService
from src.database.connection import get_db_session
from src.utils.auth import validate_jwt_token

# Configure logging
logger = logging.getLogger(__name__)

class StatusAPIIntegration:
    """Status API Integration service"""
    
    def __init__(self):
        self.redis_pubsub = get_redis_pubsub_service()
        self.broadcast_service = StatusBroadcastService()
        self.status_validator = StatusTransitionValidator()
    
    async def get_analysis_status(self, analysis_id: UUID) -> Optional[StatusTrackingResponse]:
        """
        Get current status for an analysis
        
        Args:
            analysis_id: UUID of the analysis
            
        Returns:
            StatusTrackingResponse or None if not found
        """
        try:
            with get_db_session() as session:
                # Query analysis with related data
                statement = select(Analysis).where(Analysis.id == analysis_id)
                analysis = session.exec(statement).first()
                
                if not analysis:
                    logger.warning(f"Analysis not found: {analysis_id}")
                    return None
                
                # Convert to StatusTrackingResponse
                status_response = StatusTrackingResponse(
                    analysis_id=analysis.id,
                    status=analysis.status.value if analysis.status else "unknown",
                    progress_percentage=self._calculate_progress_percentage(analysis),
                    current_stage=self._get_current_stage(analysis),
                    estimated_completion=self._estimate_completion(analysis),
                    processing_time_elapsed=self._calculate_processing_time(analysis),
                    error_details=self._get_error_details(analysis),
                    retry_count=analysis.retry_count or 0,
                    stage_history=self._get_stage_history(analysis),
                    processing_metadata=self._get_processing_metadata(analysis),
                    last_updated=analysis.updated_at or analysis.created_at
                )
                
                return status_response
                
        except Exception as e:
            logger.error(f"Error getting analysis status for {analysis_id}: {e}")
            return None
    
    async def update_analysis_status(
        self, 
        analysis_id: UUID, 
        status: str, 
        progress_percentage: float = None,
        current_stage: str = None,
        error_details: Dict[str, Any] = None
    ) -> bool:
        """
        Update analysis status and broadcast changes
        
        Args:
            analysis_id: UUID of the analysis
            status: New status
            progress_percentage: Progress percentage (optional)
            current_stage: Current processing stage (optional)
            error_details: Error details if status is failed (optional)
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            with get_db_session() as session:
                # Get current analysis
                statement = select(Analysis).where(Analysis.id == analysis_id)
                analysis = session.exec(statement).first()
                
                if not analysis:
                    logger.warning(f"Analysis not found for status update: {analysis_id}")
                    return False
                
                # Validate status transition
                current_status = analysis.status.value if analysis.status else "queued"
                if not self.status_validator.is_valid_transition(current_status, status):
                    logger.error(f"Invalid status transition: {current_status} -> {status}")
                    return False
                
                # Update analysis fields
                analysis.status = AnalysisStatusEnum(status)
                if progress_percentage is not None:
                    analysis.progress_percentage = progress_percentage
                if current_stage is not None:
                    analysis.current_stage = current_stage
                if error_details is not None:
                    analysis.error_details = error_details
                
                analysis.updated_at = datetime.now(timezone.utc)
                
                # Save changes
                session.add(analysis)
                session.commit()
                session.refresh(analysis)
                
                # Get updated status response
                status_response = await self.get_analysis_status(analysis_id)
                if status_response:
                    # Broadcast status update
                    await self.publish_status_update(analysis_id, status_response)
                
                logger.info(f"Successfully updated analysis {analysis_id} status to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating analysis status for {analysis_id}: {e}")
            return False
    
    async def get_status_history(self, analysis_id: UUID) -> Optional[StatusHistoryResponse]:
        """
        Get comprehensive status history for an analysis
        
        Args:
            analysis_id: UUID of the analysis
            
        Returns:
            StatusHistoryResponse or None if not found
        """
        try:
            with get_db_session() as session:
                # Query analysis with related data
                statement = select(Analysis).where(Analysis.id == analysis_id)
                analysis = session.exec(statement).first()
                
                if not analysis:
                    logger.warning(f"Analysis not found for history: {analysis_id}")
                    return None
                
                # Build status timeline
                status_timeline = []
                if analysis.created_at:
                    status_timeline.append({
                        "status": "created",
                        "timestamp": analysis.created_at.isoformat(),
                        "progress": 0.0
                    })
                
                if analysis.updated_at:
                    status_timeline.append({
                        "status": analysis.status.value if analysis.status else "unknown",
                        "timestamp": analysis.updated_at.isoformat(),
                        "progress": analysis.progress_percentage or 0.0
                    })
                
                # Build processing stages
                processing_stages = []
                if hasattr(analysis, 'stage_history') and analysis.stage_history:
                    processing_stages = analysis.stage_history
                
                # Build error logs
                error_logs = []
                if analysis.error_details:
                    error_logs.append({
                        "timestamp": analysis.updated_at.isoformat() if analysis.updated_at else None,
                        "error": analysis.error_details,
                        "stage": analysis.current_stage
                    })
                
                # Build performance metrics
                performance_metrics = {
                    "total_processing_time_ms": self._calculate_processing_time(analysis),
                    "average_stage_duration_ms": self._calculate_average_stage_duration(analysis),
                    "retry_count": analysis.retry_count or 0,
                    "final_status": analysis.status.value if analysis.status else "unknown"
                }
                
                # Build retry history
                retry_history = []
                if analysis.retry_count and analysis.retry_count > 0:
                    retry_history.append({
                        "attempt": analysis.retry_count,
                        "timestamp": analysis.updated_at.isoformat() if analysis.updated_at else None,
                        "reason": analysis.error_details.get("reason") if analysis.error_details else None
                    })
                
                history_response = StatusHistoryResponse(
                    analysis_id=analysis.id,
                    status_timeline=status_timeline,
                    processing_stages=processing_stages,
                    error_logs=error_logs,
                    performance_metrics=performance_metrics,
                    retry_history=retry_history,
                    total_processing_time_ms=self._calculate_processing_time(analysis),
                    final_status=analysis.status.value if analysis.status else "unknown",
                    created_at=analysis.created_at,
                    completed_at=analysis.completed_at
                )
                
                return history_response
                
        except Exception as e:
            logger.error(f"Error getting status history for {analysis_id}: {e}")
            return None
    
    async def publish_status_update(self, analysis_id: UUID, status_response: StatusTrackingResponse):
        """Publish status update to Redis and broadcast to WebSocket clients"""
        try:
            # Publish to Redis
            await self.redis_pubsub.publish_analysis_event(
                analysis_id=str(analysis_id),
                event_type="status_update",
                event_data=status_response.dict()
            )
            
            # Broadcast to WebSocket clients
            await self.broadcast_service.broadcast_analysis_status(
                str(analysis_id), 
                status_response
            )
            
            logger.debug(f"Published status update for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error publishing status update for {analysis_id}: {e}")
    
    async def handle_status_transition(
        self, 
        analysis_id: UUID, 
        from_status: str, 
        to_status: str,
        transition_data: Dict[str, Any] = None
    ) -> bool:
        """
        Handle status transition with validation and logging
        
        Args:
            analysis_id: UUID of the analysis
            from_status: Current status
            to_status: Target status
            transition_data: Additional transition data
            
        Returns:
            True if transition successful, False otherwise
        """
        try:
            # Validate transition
            if not self.status_validator.is_valid_transition(from_status, to_status):
                logger.error(f"Invalid status transition: {from_status} -> {to_status}")
                return False
            
            # Update status
            success = await self.update_analysis_status(
                analysis_id=analysis_id,
                status=to_status,
                progress_percentage=transition_data.get('progress_percentage'),
                current_stage=transition_data.get('current_stage'),
                error_details=transition_data.get('error_details')
            )
            
            if success:
                logger.info(f"Successfully transitioned analysis {analysis_id} from {from_status} to {to_status}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling status transition for {analysis_id}: {e}")
            return False
    
    def _calculate_progress_percentage(self, analysis: Analysis) -> float:
        """Calculate progress percentage based on analysis state"""
        if analysis.progress_percentage is not None:
            return float(analysis.progress_percentage)
        
        # Default progress based on status
        status_progress_map = {
            AnalysisStatusEnum.QUEUED: 5.0,
            AnalysisStatusEnum.PROCESSING: 50.0,
            AnalysisStatusEnum.COMPLETED: 100.0,
            AnalysisStatusEnum.FAILED: 0.0
        }
        
        return status_progress_map.get(analysis.status, 0.0)
    
    def _get_current_stage(self, analysis: Analysis) -> str:
        """Get current processing stage"""
        if analysis.current_stage:
            return analysis.current_stage
        
        # Default stage based on status
        status_stage_map = {
            AnalysisStatusEnum.QUEUED: "queued",
            AnalysisStatusEnum.PROCESSING: "processing",
            AnalysisStatusEnum.COMPLETED: "completed",
            AnalysisStatusEnum.FAILED: "failed"
        }
        
        return status_stage_map.get(analysis.status, "unknown")
    
    def _estimate_completion(self, analysis: Analysis) -> Optional[datetime]:
        """Estimate completion time"""
        if analysis.status == AnalysisStatusEnum.COMPLETED:
            return analysis.completed_at
        
        if analysis.status == AnalysisStatusEnum.PROCESSING:
            # Simple estimation based on current progress
            progress = self._calculate_progress_percentage(analysis)
            if progress > 0:
                elapsed_time = self._calculate_processing_time(analysis)
                estimated_remaining = (elapsed_time / progress) * (100 - progress)
                return datetime.now(timezone.utc) + timedelta(milliseconds=estimated_remaining)
        
        return None
    
    def _calculate_processing_time(self, analysis: Analysis) -> int:
        """Calculate total processing time in milliseconds"""
        if analysis.completed_at and analysis.created_at:
            duration = analysis.completed_at - analysis.created_at
            return int(duration.total_seconds() * 1000)
        elif analysis.created_at:
            duration = datetime.now(timezone.utc) - analysis.created_at
            return int(duration.total_seconds() * 1000)
        
        return 0
    
    def _get_error_details(self, analysis: Analysis) -> Optional[Dict[str, Any]]:
        """Get error details if analysis failed"""
        if analysis.status == AnalysisStatusEnum.FAILED and analysis.error_details:
            return analysis.error_details
        return None
    
    def _get_stage_history(self, analysis: Analysis) -> List[Dict[str, Any]]:
        """Get processing stage history"""
        if hasattr(analysis, 'stage_history') and analysis.stage_history:
            return analysis.stage_history
        
        # Default stage history based on current state
        history = []
        if analysis.created_at:
            history.append({
                "stage": "upload",
                "timestamp": analysis.created_at.isoformat(),
                "status": "completed"
            })
        
        if analysis.status == AnalysisStatusEnum.PROCESSING:
            history.append({
                "stage": "processing",
                "timestamp": analysis.updated_at.isoformat() if analysis.updated_at else datetime.now(timezone.utc).isoformat(),
                "status": "in_progress"
            })
        elif analysis.status == AnalysisStatusEnum.COMPLETED:
            history.append({
                "stage": "completed",
                "timestamp": analysis.completed_at.isoformat() if analysis.completed_at else datetime.now(timezone.utc).isoformat(),
                "status": "completed"
            })
        
        return history
    
    def _get_processing_metadata(self, analysis: Analysis) -> Dict[str, Any]:
        """Get processing metadata"""
        metadata = {
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
            "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
            "retry_count": analysis.retry_count or 0
        }
        
        if analysis.completed_at:
            metadata["completed_at"] = analysis.completed_at.isoformat()
        
        return metadata
    
    def _calculate_average_stage_duration(self, analysis: Analysis) -> float:
        """Calculate average stage duration in milliseconds"""
        stage_history = self._get_stage_history(analysis)
        if len(stage_history) < 2:
            return 0.0
        
        total_duration = self._calculate_processing_time(analysis)
        return total_duration / len(stage_history) if stage_history else 0.0

# Global instance
status_api_integration = StatusAPIIntegration()
