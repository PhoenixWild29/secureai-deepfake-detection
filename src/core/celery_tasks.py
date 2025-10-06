#!/usr/bin/env python3
"""
Celery Tasks for Async Processing
Background tasks for video processing, WebSocket notifications, and system maintenance
"""

import os
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure

from ..config.settings import get_processing_settings, get_upload_settings
from ..schemas.websocket_events import (
    ProcessingInitiatedEvent,
    ProcessingProgressEvent,
    ProcessingCompletedEvent,
    ProcessingFailedEvent,
    create_processing_initiated_event
)
from ..utils.hash_generator import generate_content_hash
from ..errors.api_errors import ProcessingError

# Configure logging
logger = logging.getLogger(__name__)

# Get settings
upload_settings = get_upload_settings()
processing_settings = get_processing_settings()

# Initialize Celery app
celery_app = Celery(
    'secureai_video_processing',
    broker=upload_settings.celery_broker_url or 'redis://localhost:6379/0',
    backend=upload_settings.celery_result_backend or 'redis://localhost:6379/0'
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=processing_settings.job_timeout_minutes * 60,
    task_soft_time_limit=(processing_settings.job_timeout_minutes - 5) * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_routes={
        'src.core.celery_tasks.process_video_async': {'queue': 'video_processing'},
        'src.core.celery_tasks.process_video_batch': {'queue': 'batch_processing'},
        'src.core.celery_tasks.cleanup_expired_sessions': {'queue': 'maintenance'},
        'src.core.celery_tasks.send_websocket_notification': {'queue': 'notifications'},
    }
)


@celery_app.task(bind=True, name='src.core.celery_tasks.process_video_async')
def process_video_async(
    self,
    file_path: str,
    upload_id: str,
    upload_options: Dict[str, Any],
    priority: int = 5,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a single video file asynchronously.
    
    Args:
        file_path: Path to the video file
        upload_id: Upload ID
        upload_options: Upload options and configuration
        priority: Processing priority (1-10)
        user_id: User ID (optional)
        
    Returns:
        Dictionary with processing results
    """
    try:
        # Generate unique identifiers
        analysis_id = str(self.request.id)
        processing_job_id = self.request.id
        
        logger.info(f"Starting video processing: {file_path} (job: {processing_job_id})")
        
        # Send processing initiated notification
        try:
            send_websocket_notification.delay(
                event_type='processing_initiated',
                upload_id=upload_id,
                analysis_id=analysis_id,
                processing_job_id=processing_job_id,
                file_path=file_path,
                upload_options=upload_options,
                priority=priority,
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to send processing initiated notification: {e}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise ProcessingError(
                message=f"Video file not found: {file_path}",
                details={'file_path': file_path, 'upload_id': upload_id}
            )
        
        # Get file information
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        # Generate file hash for deduplication
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            file_hash = generate_content_hash(file_content)
        except Exception as e:
            logger.warning(f"Failed to generate file hash: {e}")
            file_hash = "unknown"
        
        # Check for deduplication (if enabled)
        if upload_settings.enable_deduplication and upload_settings.embedding_cache_url:
            duplicate_result = _check_duplicate(file_hash)
            if duplicate_result['is_duplicate']:
                logger.info(f"Duplicate file detected: {filename} (hash: {file_hash[:8]}...)")
                
                # Send duplicate detected notification
                try:
                    send_websocket_notification.delay(
                        event_type='duplicate_detected',
                        upload_id=upload_id,
                        analysis_id=analysis_id,
                        processing_job_id=processing_job_id,
                        filename=filename,
                        file_hash=file_hash,
                        duplicate_result=duplicate_result,
                        user_id=user_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to send duplicate detected notification: {e}")
                
                return {
                    'success': True,
                    'duplicate': True,
                    'analysis_id': analysis_id,
                    'processing_job_id': processing_job_id,
                    'file_hash': file_hash,
                    'result': duplicate_result['result'],
                    'processing_time_ms': duplicate_result.get('processing_time_ms', 0),
                    'message': 'File already analyzed - returning cached result'
                }
        
        # Send progress update (started)
        try:
            send_websocket_notification.delay(
                event_type='processing_progress',
                upload_id=upload_id,
                analysis_id=analysis_id,
                processing_job_id=processing_job_id,
                progress_percentage=0.0,
                current_stage='initializing',
                stage_message='Starting video analysis',
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to send progress notification: {e}")
        
        # Start processing
        start_time = time.time()
        
        # Import detection function (avoid circular imports)
        try:
            from ai_model.detect import detect_fake
        except ImportError:
            logger.error("Failed to import detect_fake function")
            raise ProcessingError(
                message="Video detection module not available",
                details={'file_path': file_path}
            )
        
        # Send progress update (analyzing)
        try:
            send_websocket_notification.delay(
                event_type='processing_progress',
                upload_id=upload_id,
                analysis_id=analysis_id,
                processing_job_id=processing_job_id,
                progress_percentage=25.0,
                current_stage='analyzing',
                stage_message='Analyzing video frames',
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to send progress notification: {e}")
        
        # Run video analysis
        try:
            model_type = upload_options.get('model_type', processing_settings.default_model_type)
            result = detect_fake(file_path, model_type=model_type)
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            raise ProcessingError(
                message=f"Video analysis failed: {str(e)}",
                details={'file_path': file_path, 'error': str(e)}
            )
        
        # Send progress update (finalizing)
        try:
            send_websocket_notification.delay(
                event_type='processing_progress',
                upload_id=upload_id,
                analysis_id=analysis_id,
                processing_job_id=processing_job_id,
                progress_percentage=75.0,
                current_stage='finalizing',
                stage_message='Generating final results',
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to send progress notification: {e}")
        
        # Perform additional analysis if requested
        try:
            # Import security analysis (if available)
            try:
                from ai_model.morpheus_security import analyze_video_security
                security_analysis = analyze_video_security(file_path, result)
                result['security_analysis'] = security_analysis
            except ImportError:
                logger.debug("Security analysis module not available")
                security_analysis = None
            
            # Import blockchain integration (if available)
            try:
                from integration.integrate import submit_to_solana
                blockchain_hash = submit_to_solana(file_hash, result.get('authenticity_score', 0.5))
                result['blockchain_hash'] = blockchain_hash
            except ImportError:
                logger.debug("Blockchain integration module not available")
                blockchain_hash = None
            
        except Exception as e:
            logger.warning(f"Additional analysis failed: {e}")
            # Continue with basic result
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare final result
        final_result = {
            'success': True,
            'duplicate': False,
            'analysis_id': analysis_id,
            'processing_job_id': processing_job_id,
            'upload_id': upload_id,
            'filename': filename,
            'file_path': file_path,
            'file_size': file_size,
            'file_hash': file_hash,
            'result': result,
            'processing_time_seconds': round(processing_time, 2),
            'processing_time_ms': int(processing_time * 1000),
            'model_type': model_type,
            'confidence_score': result.get('authenticity_score', 0.5),
            'is_fake': result.get('is_fake', False),
            'blockchain_hash': result.get('blockchain_hash'),
            'security_analysis': result.get('security_analysis'),
            'user_id': user_id,
            'processing_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Send completion notification
        try:
            send_websocket_notification.delay(
                event_type='processing_completed',
                upload_id=upload_id,
                analysis_id=analysis_id,
                processing_job_id=processing_job_id,
                filename=filename,
                file_hash=file_hash,
                processing_duration_seconds=processing_time,
                result=final_result,
                confidence_score=final_result['confidence_score'],
                is_fake=final_result['is_fake'],
                blockchain_hash=final_result['blockchain_hash'],
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Failed to send completion notification: {e}")
        
        logger.info(f"Video processing completed: {filename} in {processing_time:.2f}s")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        
        # Send failure notification
        try:
            send_websocket_notification.delay(
                event_type='processing_failed',
                upload_id=upload_id,
                analysis_id=getattr(self.request, 'id', 'unknown'),
                processing_job_id=getattr(self.request, 'id', 'unknown'),
                filename=os.path.basename(file_path) if file_path else 'unknown',
                error_code='PROCESSING_ERROR',
                error_message=str(e),
                error_details={'file_path': file_path, 'upload_id': upload_id},
                user_id=user_id
            )
        except Exception as notification_error:
            logger.error(f"Failed to send failure notification: {notification_error}")
        
        raise


@celery_app.task(bind=True, name='src.core.celery_tasks.process_video_batch')
def process_video_batch(
    self,
    file_paths: List[str],
    batch_id: str,
    upload_options: Dict[str, Any],
    priority: int = 5,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process multiple video files in a batch.
    
    Args:
        file_paths: List of file paths to process
        batch_id: Batch identifier
        upload_options: Upload options and configuration
        priority: Processing priority (1-10)
        user_id: User ID (optional)
        
    Returns:
        Dictionary with batch processing results
    """
    try:
        logger.info(f"Starting batch processing: {batch_id} with {len(file_paths)} files")
        
        results = []
        failed_files = []
        
        for i, file_path in enumerate(file_paths):
            try:
                # Update progress
                progress = (i / len(file_paths)) * 100
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1,
                        'total': len(file_paths),
                        'progress': progress,
                        'current_file': os.path.basename(file_path)
                    }
                )
                
                # Process individual file
                result = process_video_async.delay(
                    file_path=file_path,
                    upload_id=f"{batch_id}_{i}",
                    upload_options=upload_options,
                    priority=priority,
                    user_id=user_id
                ).get()
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")
                failed_files.append({
                    'file_path': file_path,
                    'error': str(e)
                })
        
        # Final progress update
        self.update_state(
            state='SUCCESS',
            meta={
                'current': len(file_paths),
                'total': len(file_paths),
                'progress': 100.0,
                'completed': True
            }
        )
        
        batch_result = {
            'success': True,
            'batch_id': batch_id,
            'total_files': len(file_paths),
            'successful_files': len(results),
            'failed_files': len(failed_files),
            'results': results,
            'failed_files': failed_files,
            'processing_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Batch processing completed: {batch_id}")
        
        return batch_result
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise


@celery_app.task(name='src.core.celery_tasks.cleanup_expired_sessions')
def cleanup_expired_sessions() -> Dict[str, Any]:
    """
    Clean up expired upload sessions and temporary files.
    
    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info("Starting cleanup of expired upload sessions")
        
        # TODO: Implement actual cleanup logic
        # This would involve:
        # 1. Query database for expired sessions
        # 2. Remove temporary chunk files
        # 3. Update session status
        # 4. Clean up old progress logs
        
        cleanup_result = {
            'success': True,
            'sessions_cleaned': 0,
            'files_removed': 0,
            'storage_freed_mb': 0,
            'cleanup_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Upload session cleanup completed")
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise


@celery_app.task(name='src.core.celery_tasks.send_websocket_notification')
def send_websocket_notification(
    event_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Send WebSocket notification to connected clients.
    
    Args:
        event_type: Type of event to send
        **kwargs: Event-specific data
        
    Returns:
        Dictionary with notification results
    """
    try:
        # TODO: Implement actual WebSocket notification logic
        # This would involve:
        # 1. Creating appropriate event object based on event_type
        # 2. Broadcasting to relevant WebSocket connections
        # 3. Handling user-specific vs. global notifications
        
        logger.debug(f"WebSocket notification sent: {event_type}")
        
        return {
            'success': True,
            'event_type': event_type,
            'notification_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"WebSocket notification failed: {e}")
        raise


def _check_duplicate(file_hash: str) -> Dict[str, Any]:
    """
    Check if file hash already exists in the system.
    
    Args:
        file_hash: File content hash
        
    Returns:
        Dictionary with duplicate information
    """
    try:
        # TODO: Implement actual deduplication check using EmbeddingCache
        # This would involve:
        # 1. Query EmbeddingCache for existing hash
        # 2. Return cached result if found
        # 3. Return empty result if not found
        
        return {
            'is_duplicate': False,
            'upload_id': None,
            'analysis_id': None,
            'result': None
        }
        
    except Exception as e:
        logger.error(f"Duplicate check failed: {e}")
        return {'is_duplicate': False}


# Celery signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task pre-run events."""
    logger.info(f"Task starting: {task.name} (ID: {task_id})")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Handle task post-run events."""
    logger.info(f"Task completed: {task.name} (ID: {task_id}, State: {state})")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure events."""
    logger.error(f"Task failed: {sender.name} (ID: {task_id}): {exception}")


# Export main components
__all__ = [
    'celery_app',
    'process_video_async',
    'process_video_batch',
    'cleanup_expired_sessions',
    'send_websocket_notification'
]
