#!/usr/bin/env python3
"""
Detection Engine Integration Service
Service for integrating with Core Detection Engine API for video analysis
"""

import os
import uuid
import logging
import tempfile
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

# Import existing detection modules
try:
    from ai_model.detect import detect_fake, get_available_models
    from ai_model.enhanced_detector import detect_fake_enhanced
    from ai_model.deepfake_classifier import DeepfakeClassifier, ResNetDeepfakeClassifier
except ImportError:
    # Fallback for when called from different directory
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from ai_model.detect import detect_fake, get_available_models
    from ai_model.enhanced_detector import detect_fake_enhanced
    from ai_model.deepfake_classifier import DeepfakeClassifier, ResNetDeepfakeClassifier

from src.schemas.video_upload_schema import VideoAnalysisRequest, VideoAnalysisResponse

logger = logging.getLogger(__name__)


class DetectionEngineService:
    """
    Service for integrating with Core Detection Engine.
    Provides analysis initiation, result handling, and error management.
    """
    
    def __init__(self):
        """Initialize detection engine service"""
        self.available_models = get_available_models()
        self.default_model = "resnet"
        self.max_retries = 3
        self.timeout_seconds = 300  # 5 minutes
    
    def initiate_video_analysis(
        self,
        video_id: UUID,
        s3_key: str,
        s3_bucket: str,
        model_type: str = "resnet",
        analysis_config: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> VideoAnalysisResponse:
        """
        Initiate video analysis using Core Detection Engine.
        
        Args:
            video_id: Video ID for tracking
            s3_key: S3 object key for the video file
            s3_bucket: S3 bucket name
            model_type: Detection model type to use
            analysis_config: Optional analysis configuration
            priority: Analysis priority
            
        Returns:
            VideoAnalysisResponse with analysis results
            
        Raises:
            DetectionEngineError: If analysis fails
        """
        analysis_id = uuid.uuid4()
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Initiating analysis for video {video_id} with model {model_type}")
            
            # Download video from S3 to temporary file
            temp_file_path = self._download_video_from_s3(s3_key, s3_bucket)
            
            try:
                # Run detection analysis
                detection_result = self._run_detection_analysis(
                    temp_file_path,
                    model_type,
                    analysis_config
                )
                
                # Process results
                analysis_response = self._process_analysis_results(
                    analysis_id=analysis_id,
                    video_id=video_id,
                    detection_result=detection_result,
                    model_type=model_type,
                    start_time=start_time
                )
                
                logger.info(f"Analysis completed for video {video_id}: {analysis_response.is_fake}")
                return analysis_response
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Analysis failed for video {video_id}: {str(e)}")
            
            # Return error response
            return VideoAnalysisResponse(
                analysis_id=analysis_id,
                video_id=video_id,
                status="failed",
                detection_result={"error": str(e)},
                confidence_score=0.0,
                is_fake=False,
                processing_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
                model_used=model_type,
                created_at=start_time,
                error_message=str(e)
            )
    
    def _download_video_from_s3(self, s3_key: str, s3_bucket: str) -> str:
        """
        Download video from S3 to temporary file.
        
        Args:
            s3_key: S3 object key
            s3_bucket: S3 bucket name
            
        Returns:
            Path to temporary file
            
        Raises:
            DetectionEngineError: If download fails
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Initialize S3 client
            s3_client = boto3.client('s3')
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Download from S3
            s3_client.download_file(s3_bucket, s3_key, temp_file_path)
            
            logger.info(f"Downloaded video from S3: {s3_key}")
            return temp_file_path
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise DetectionEngineError(f"S3 download failed ({error_code}): {error_message}")
        except Exception as e:
            raise DetectionEngineError(f"S3 download failed: {str(e)}")
    
    def _run_detection_analysis(
        self,
        video_path: str,
        model_type: str,
        analysis_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run detection analysis on video file.
        
        Args:
            video_path: Path to video file
            model_type: Detection model type
            analysis_config: Optional analysis configuration
            
        Returns:
            Dictionary with detection results
            
        Raises:
            DetectionEngineError: If analysis fails
        """
        try:
            # Validate model type
            if model_type not in self.available_models:
                raise DetectionEngineError(f"Unsupported model type: {model_type}")
            
            # Run detection based on model type
            if model_type == "enhanced":
                result = detect_fake_enhanced(video_path)
            elif model_type == "resnet":
                result = detect_fake(video_path, model_type="resnet")
            elif model_type == "cnn":
                result = detect_fake(video_path, model_type="cnn")
            elif model_type == "ensemble":
                result = detect_fake(video_path, model_type="ensemble")
            else:
                result = detect_fake(video_path, model_type=model_type)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise DetectionEngineError("Invalid detection result format")
            
            # Ensure required fields are present
            if 'is_fake' not in result:
                result['is_fake'] = result.get('confidence', 0.5) > 0.5
            
            if 'confidence' not in result:
                result['confidence'] = 0.5
            
            if 'authenticity_score' not in result:
                result['authenticity_score'] = 1 - result['confidence']
            
            # Add analysis metadata
            result['model_type'] = model_type
            result['analysis_config'] = analysis_config or {}
            result['timestamp'] = datetime.now(timezone.utc).isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Detection analysis failed: {str(e)}")
            raise DetectionEngineError(f"Analysis failed: {str(e)}")
    
    def _process_analysis_results(
        self,
        analysis_id: UUID,
        video_id: UUID,
        detection_result: Dict[str, Any],
        model_type: str,
        start_time: datetime
    ) -> VideoAnalysisResponse:
        """
        Process detection results into analysis response.
        
        Args:
            analysis_id: Analysis ID
            video_id: Video ID
            detection_result: Raw detection results
            model_type: Model type used
            start_time: Analysis start time
            
        Returns:
            VideoAnalysisResponse with processed results
        """
        end_time = datetime.now(timezone.utc)
        processing_time = (end_time - start_time).total_seconds()
        
        # Extract key metrics
        confidence_score = detection_result.get('confidence', 0.0)
        is_fake = detection_result.get('is_fake', False)
        
        # Determine status
        status = "completed" if 'error' not in detection_result else "failed"
        
        return VideoAnalysisResponse(
            analysis_id=analysis_id,
            video_id=video_id,
            status=status,
            detection_result=detection_result,
            confidence_score=confidence_score,
            is_fake=is_fake,
            processing_time=processing_time,
            model_used=model_type,
            created_at=start_time,
            completed_at=end_time if status == "completed" else None,
            error_message=detection_result.get('error')
        )
    
    def get_analysis_status(self, analysis_id: UUID) -> Dict[str, Any]:
        """
        Get analysis status by analysis ID.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Dictionary with analysis status
        """
        # This would typically query a database or cache
        # For now, return a placeholder response
        return {
            'analysis_id': str(analysis_id),
            'status': 'completed',
            'message': 'Analysis status retrieval not implemented'
        }
    
    def cancel_analysis(self, analysis_id: UUID) -> bool:
        """
        Cancel a running analysis.
        
        Args:
            analysis_id: Analysis ID to cancel
            
        Returns:
            True if cancellation successful, False otherwise
        """
        # This would typically interact with a job queue or process manager
        # For now, return a placeholder response
        logger.info(f"Cancelling analysis {analysis_id}")
        return True
    
    def get_available_models(self) -> Dict[str, str]:
        """
        Get available detection models.
        
        Returns:
            Dictionary mapping model names to descriptions
        """
        return self.available_models
    
    def estimate_processing_time(
        self,
        file_size: int,
        model_type: str = "resnet"
    ) -> int:
        """
        Estimate processing time for video analysis.
        
        Args:
            file_size: File size in bytes
            model_type: Detection model type
            
        Returns:
            Estimated processing time in seconds
        """
        # Base processing time estimates (in seconds)
        base_times = {
            "resnet": 30,
            "cnn": 45,
            "enhanced": 60,
            "ensemble": 90
        }
        
        base_time = base_times.get(model_type, 30)
        
        # Adjust based on file size (rough estimate)
        size_mb = file_size / (1024 * 1024)
        if size_mb > 100:
            base_time *= 1.5
        elif size_mb > 50:
            base_time *= 1.2
        
        return int(base_time)


class DetectionEngineError(Exception):
    """Custom exception for detection engine errors"""
    pass


# Global service instance
_detection_engine_service: Optional[DetectionEngineService] = None


def get_detection_engine_service() -> DetectionEngineService:
    """
    Get or create the global detection engine service instance.
    
    Returns:
        DetectionEngineService instance
    """
    global _detection_engine_service
    
    if _detection_engine_service is None:
        _detection_engine_service = DetectionEngineService()
    
    return _detection_engine_service


def initiate_video_analysis(
    video_id: UUID,
    s3_key: str,
    s3_bucket: str,
    model_type: str = "resnet",
    analysis_config: Optional[Dict[str, Any]] = None,
    priority: int = 0
) -> VideoAnalysisResponse:
    """
    Convenience function to initiate video analysis.
    
    Args:
        video_id: Video ID for tracking
        s3_key: S3 object key for the video file
        s3_bucket: S3 bucket name
        model_type: Detection model type to use
        analysis_config: Optional analysis configuration
        priority: Analysis priority
        
    Returns:
        VideoAnalysisResponse with analysis results
    """
    service = get_detection_engine_service()
    return service.initiate_video_analysis(
        video_id=video_id,
        s3_key=s3_key,
        s3_bucket=s3_bucket,
        model_type=model_type,
        analysis_config=analysis_config,
        priority=priority
    )


def estimate_processing_time(
    file_size: int,
    model_type: str = "resnet"
) -> int:
    """
    Convenience function to estimate processing time.
    
    Args:
        file_size: File size in bytes
        model_type: Detection model type
        
    Returns:
        Estimated processing time in seconds
    """
    service = get_detection_engine_service()
    return service.estimate_processing_time(file_size, model_type)


# Export main service class and convenience functions
__all__ = [
    'DetectionEngineService',
    'DetectionEngineError',
    'get_detection_engine_service',
    'initiate_video_analysis',
    'estimate_processing_time'
]
