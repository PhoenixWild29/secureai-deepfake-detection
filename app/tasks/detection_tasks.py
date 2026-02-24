#!/usr/bin/env python3
"""
Enhanced Celery Tasks for Detailed Progress Tracking
Celery tasks for detection processing with comprehensive progress reporting to Redis.
"""

import os
import time
import logging
import psutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from celery import Celery, Task
import cv2
import numpy as np

from app.utils.redis_client import get_progress_tracker_redis
from app.schemas.detection import (
    ProcessingStageDetails,
    FrameProgressInfo,
    ErrorRecoveryStatus,
    ProcessingMetrics,
    DetectionStatus
)

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery('detection_tasks')
celery_app.config_from_object('celery_app.celeryconfig')

# Initialize progress tracker
progress_tracker = get_progress_tracker_redis()


class ProgressReportingTask(Task):
    """
    Base Celery task class with automatic progress reporting.
    Provides methods for reporting detailed progress to Redis.
    """
    
    def __init__(self):
        self.aws_processing_metrics = None
        self.start_time = None
        self.analysis_id = None
    
    def before_start(self, task_id, args, kwargs):
        """Called before the task starts"""
        super().before_start(task_id, args, kwargs)
        self.start_time = time.time()
        
        # Extract analysis_id if provided
        if kwargs.get('analysis_id'):
            self.analysis_id = UUID(kwargs['analysis_id'])
    
    async def report_stage_progress(
        self,
        stage_name: str,
        stage_progress: float,
        stage_status: str = "active",
        stage_frames: Optional[int] = None,
        stage_total_frames: Optional[int] = None
    ):
        """Report processing stage progress"""
        if not self.analysis_id:
            return
        
        try:
            stage_details = ProcessingStageDetails(
                stage_name=stage_name,
                stage_status=stage_status,
                stage_completion_percentage=stage_progress,
                stage_start_time=datetime.now(timezone.utc),
                stage_frames_processed=stage_frames,
                stage_total_frames=stage_total_frames
            )
            
            await progress_tracker.store_detailed_progress(
                analysis_id=self.analysis_id,
                stage_details=stage_details
            )
            
            logger.debug(f"Reported stage progress: {stage_name} - {stage_progress}%")
            
        except Exception as e:
            logger.error(f"Failed to report stage progress: {e}")
    
    async def report_frame_progress(
        self,
        current_frame: int,
        total_frames: int,
        processing_rate: Optional[float] = None
    ):
        """Report frame-level progress"""
        if not self.analysis_id:
            return
        
        try:
            await progress_tracker.store_frame_progress(
                analysis_id=self.analysis_id,
                current_frame=current_frame,
                total_frames=total_frames,
                processing_rate=processing_rate
            )
            
            logger.debug(f"Reported frame progress: {current_frame}/{total_frames}")
            
        except Exception as e:
            logger.error(f"Failed to report frame progress: {e}")
    
    async def report_error_recovery(
        self,
        error_type: str,
        error_message: str,
        retry_count: int,
        recovery_action: Optional[str] = None,
        is_recovering: bool = False
    ):
        """Report error recovery status"""
        if not self.analysis_id:
            return
        
        try:
            await progress_tracker.store_error_recovery(
                analysis_id=self.analysis_id,
                error_type=error_type,
                error_message=error_message,
                retry_count=retry_count,
                recovery_action=recovery_action,
                is_recovering=is_recovering
            )
            
            logger.debug(f"Reported error recovery: {error_type} - {recovery_action}")
            
        except Exception as e:
            logger.error(f"Failed to report error recovery: {e}")
    
    async def report_processing_metrics(self):
        """Report processing performance metrics"""
        if not self.analysis_id:
            return
        
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            memory_usage_mb = memory_info.used / (1024 * 1024)
            
            # Calculate processing efficiency
            elapsed_time = time.time() - self.start_time if self.start_time else 1
            memory_efficiency = max(0, 1 - (memory_info.percent / 100))  # 1.0 if low memory usage
            cpu_efficiency = min(1.0, cpu_percent / 80.0)  # Optimal around 80% CPU
            processing_efficiency = (memory_efficiency + cpu_efficiency) / 2
            
            processing_metrics = ProcessingMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_usage_mb,
                worker_id=getattr(self.request, 'id', None),
                queue_wait_time_seconds=0,  # Could be calculated from task start delay
                processing_efficiency=processing_efficiency
            )
            
            await progress_tracker.store_detailed_progress(
                analysis_id=self.analysis_id,
                processing_metrics=processing_metrics
            )
            
        except Exception as e:
            logger.error(f"Failed to report processing metrics: {e}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        super().on_failure(exc, task_id, args, kwargs, einfo)
        
        if self.analysis_id:
            error_type = type(exc).__name__
            error_message = str(exc)
            retry_count = self.request.retries if hasattr(self.request, 'retries') else 0
            
            # Report the failure
            try:
                import asyncio
                asyncio.create_task(self.report_error_recovery(
                    error_type=error_type,
                    error_message=error_message,
                    retry_count=retry_count,
                    recovery_action="task_failure_handled",
                    is_recovering=False
                ))
            except Exception as e:
                logger.error(f"Failed to report task failure: {e}")


@celery_app.task(bind=True, base=ProgressReportingTask)
def analyze_video_detailed(
    self,
    video_path: str,
    analysis_id: str,
    frames_per_second: int = 1,
    enable_blockchain: bool = True
):
    """
    Enhanced video analysis task with detailed progress tracking.
    
    Args:
        video_path: Path to video file
        analysis_id: Analysis ID for progress tracking
        frames_per_second: Frame sampling rate
        enable_blockchain: Whether to enable blockchain verification
        
    Returns:
        Analysis result dictionary
    """
    try:
        self.analysis_id = UUID(analysis_id)
        
        # Report analysis started
        import asyncio
        asyncio.create_task(self.report_stage_progress(
            stage_name="initialization",
            stage_progress=5.0,
            stage_status="active"
        ))
        
        # Load video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        logger.info(f"Starting detailed analysis for {total_frames} frames")
        
        # Report video loaded
        asyncio.create_task(self.report_stage_progress(
            stage_name="video_loaded",
            stage_progress=10.0,
            stage_status="completed"
        ))
        
        # Initialize analysis variables
        frames_processed = 0
        fake_frames = []
        confidence_scores = []
        frame_times = []
        
        # Calculate frame sampling
        processing_interval = max(1, int(fps / frames_per_second)) if fps > 0 else 1
        
        # Process frames
        start_time = time.time()
        
        while True:
            frame_start_time = time.time()
            
            # Read frame
            ret, frame = cap.read()
            if not ret:
                break
            
            # Skip frames based on sampling rate
            frame_number = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if frame_number % processing_interval != 0:
                continue
            
            try:
                # Simulate frame analysis (replace with actual analysis)
                fake_probability = await asyncio.create_task(_analyze_frame(frame))
                confidence_scores.append(fake_probability)
                
                if fake_probability > 0.5:
                    fake_frames.append(frame_number)
                
                frames_processed += 1
                
                # Report frame progress every 50 frames
                if frames_processed % 50 == 0:
                    elapsed_time = time.time() - start_time
                    processing_rate = frames_processed / elapsed_time if elapsed_time > 0 else 0
                    
                    asyncio.create_task(self.report_frame_progress(
                        current_frame=frame_number,
                        total_frames=total_frames,
                        processing_rate=processing_rate
                    ))
                    
                    # Report processing stage progress
                    progress_percentage = (frame_number / total_frames) * 100
                    stage_progress = 10 + (progress_percentage * 0.8)  # 10%-90% for processing stage
                    
                    asyncio.create_task(self.report_stage_progress(
                        stage_name="frame_analysis",
                        stage_progress=stage_progress,
                        stage_status="active",
                        stage_frames=frames_processed,
                        stage_total_frames=int(total_frames / processing_interval)
                    ))
                    
                    # Report metrics
                    asyncio.create_task(self.report_processing_metrics())
                
                frame_time = time.time() - frame_start_time
                frame_times.append(frame_time)
                
            except Exception as frame_error:
                logger.error(f"Error processing frame {frame_number}: {frame_error}")
                
                # Report frame processing error
                asyncio.create_task(self.report_error_recovery(
                    error_type="frame_processing_error",
                    error_message=str(frame_error),
                    retry_count=0,
                    recovery_action="skip_frame_and_continue",
                    is_recovering=True
                ))
                
                # Continue with next frame
                continue
        
        cap.release()
        
        # Report analysis completed
        asyncio.create_task(self.report_stage_progress(
            stage_name="analysis_completed",
            stage_progress=95.0,
            stage_status="completed"
        ))
        
        # Calculate results
        overall_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
        suspicious_frame_ratio = len(fake_frames) / frames_processed if frames_processed > 0 else 0
        
        # Report final processing
        asyncio.create_task(self.report_stage_progress(
            stage_name="result_generation",
            stage_progress=98.0,
            stage_status="active"
        ))
        
        # Generate result
        result = {
            'analysis_id': analysis_id,
            'overall_confidence': float(overall_confidence),
            'suspicious_frame_count': len(fake_frames),
            'total_frames_analyzed': frames_processed,
            'total_video_frames': total_frames,
            'suspicious_frame_ratio': float(suspicious_frame_ratio),
            'processing_time_seconds': time.time() - start_time,
            'average_frame_time_ms': np.mean(frame_times) * 1000 if frame_times else 0,
            'fps_original': fps,
            'fps_analyzed': frames_per_second,
            'video_duration': duration,
            'fake_frames': fake_frames,
            'confidence_scores': confidence_scores,
            'blockchain_enabled': enable_blockchain,
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Blockchain verification if enabled
        if enable_blockchain:
            asyncio.create_task(self.report_stage_progress(
                stage_name="blockchain_verification",
                stage_progress=99.0,
                stage_status="active"
            ))
            
            try:
                blockchain_hash = await asyncio.create_task(_submit_to_blockchain(result))
                result['backend_hash'] = blockchain_hash
                
                asyncio.create_task(self.report_stage_progress(
                    stage_name="blockchain_verification",
                    stage_progress=100.0,
                    stage_status="completed"
                ))
            except Exception as blockchain_error:
                logger.error(f"Blockchain verification failed: {blockchain_error}")
                asyncio.create_task(self.report_error_recovery(
                    error_type="blockchain_error",
                    error_message=str(blockchain_error),
                    retry_count=0,
                    recovery_action="continue_without_blockchain",
                    is_recovering=False
                ))
        
        # Final stage completion
        asyncio.create_task(self.report_stage_progress(
            stage_name="analysis_complete",
            stage_progress=100.0,
            stage_status="completed"
        ))
        
        # Final frame progress report
        asyncio.create_task(self.report_frame_progress(
            current_frame=total_frames,
            total_frames=total_frames,
            processing_rate=frames_processed / (time.time() - start_time)
        ))
        
        logger.info(f"Completed detailed analysis for {analysis_id}")
        return result
        
    except Exception as e:
        logger.error(f"Analysis task failed for {analysis_id}: {e}")
        
        # Report final error
        try:
            import asyncio
            asyncio.create_task(self.report_error_recovery(
                error_type="analysis_failure",
                error_message=str(e),
                retry_count=self.request.retries if hasattr(self.request, 'retries') else 0,
                recovery_action="task_failed",
                is_recovering=False
            ))
        except Exception as report_error:
            logger.error(f"Failed to report analysis failure: {report_error}")
        
        raise


@celery_app.task(bind=True, base=ProgressReportingTask)
def batch_analyze_videos_detailed(
    self,
    video_paths: list,
    analysis_id: str,
    frames_per_second: int = 1
):
    """
    Enhanced batch video analysis task with detailed progress tracking.
    
    Args:
        video_paths: List of video file paths
        analysis_id: Analysis ID for progress tracking
        frames_per_second: Frame sampling rate
        
    Returns:
        Batch analysis results
    """
    try:
        self.analysis_id = UUID(analysis_id)
        total_videos = len(video_paths)
        
        import asyncio
        
        # Report batch started
        asyncio.create_task(self.report_stage_progress(
            stage_name="batch_initialization",
            stage_progress=5.0,
            stage_status="active"
        ))
        
        results = []
        videos_processed = 0
        
        for i, video_path in enumerate(video_paths):
            try:
                # Report current video progress
                video_progress = 10 + ((videos_processed / total_videos) * 80)
                
                asyncio.create_task(self.report_stage_progress(
                    stage_name=f"processing_video_{i+1}",
                    stage_progress=video_progress,
                    stage_status="active",
                    stage_frames=videos_processed,
                    stage_total_frames=total_videos
                ))
                
                # Analyze video (simplified - would call actual analysis)
                result = {
                    'video_path': video_path,
                    'status': 'completed',
                    'confidence_score': np.random.uniform(0, 1),  # Mock result
                    'processed_at': datetime.now(timezone.utc).isoformat()
                }
                
                results.append(result)
                videos_processed += 1
                
                # Report metrics periodically
                if videos_processed % 5 == 0:
                    asyncio.create_task(self.report_processing_metrics())
                
            except Exception as video_error:
                logger.error(f"Error processing video {video_path}: {video_error}")
                
                asyncio.create_task(self.report_error_recovery(
                    error_type="video_processing_error",
                    error_message=str(video_error),
                    retry_count=0,
                    recovery_action="skip_video_and_continue",
                    is_recovering=False
                ))
                
                results.append({
                    'video_path': video_path,
                    'status': 'failed',
                    'error': str(video_error),
                    'processed_at': datetime.now(timezone.utc).isoformat()
                })
        
        # Report batch completed
        asyncio.create_task(self.report_stage_progress(
            stage_name="batch_completed",
            stage_progress=100.0,
            stage_status="completed"
        ))
        
        batch_result = {
            'analysis_id': analysis_id,
            'total_videos': total_videos,
            'videos_processed': videos_processed,
            'successful_analyses': len([r for r in results if r['status'] == 'completed']),
            'failed_analyses': len([r for r in results if r['status'] == 'failed']),
            'results': results,
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Completed batch analysis for {analysis_id}")
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch analysis task failed for {analysis_id}: {e}")
        
        try:
            import asyncio
            asyncio.create_task(self.report_error_recovery(
                error_type="batch_failure",
                error_message=str(e),
                retry_count=self.request.retries if hasattr(self.request, 'retries') else 0,
                recovery_action="batch_task_failed",
                is_recovering=False
            ))
        except Exception as report_error:
            logger.error(f"Failed to report batch failure: {report_error}")
        
        raise


# Helper functions

async def _analyze_frame(frame: np.ndarray) -> float:
    """
    Simulate frame analysis (replace with actual deepfake detection).
    Returns fake probability (0-1).
    """
    import asyncio
    # This would be replaced with actual deepfake detection model
    await asyncio.sleep(0.01)  # Simulate processing time
    return np.random.uniform(0, 1)


async def _submit_to_blockchain(result: Dict[str, Any]) -> str:
    """
    Submit result to blockchain (simplified).
    Returns blockchain transaction hash.
    """
    import asyncio
    # This would integrate with actual blockchain service
    await asyncio.sleep(0.1)  # Simulate blockchain submission
    return f"blockchain_hash_{int(time.time())}"
