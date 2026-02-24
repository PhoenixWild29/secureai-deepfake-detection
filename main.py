#!/usr/bin/env python3
"""
Main Application Entry Point
Application entry point for the async video processing pipeline with Celery
"""

import os
import sys
import logging
import argparse
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our modules
from celery_app.tasks import detect_video, health_check, cleanup_expired_results, monitor_gpu_usage
from celery_app.celeryconfig import create_celery_app, validate_configuration
from utils.redis_client import redis_client
from utils.db_client import db_client
from video_processing.frame_extractor import frame_extractor
from video_processing.ml_inference import ensemble_generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('celery_worker.log')
    ]
)
logger = logging.getLogger(__name__)


class VideoProcessingPipeline:
    """
    Main application class for the video processing pipeline.
    Provides interface for triggering video analysis and monitoring system health.
    """
    
    def __init__(self):
        """Initialize the video processing pipeline."""
        self.celery_app = create_celery_app()
        self.startup_time = datetime.now(timezone.utc)
        
        logger.info("Video Processing Pipeline initialized")
    
    def validate_system(self) -> Dict[str, Any]:
        """
        Validate system configuration and dependencies.
        
        Returns:
            Validation results dictionary
        """
        logger.info("Validating system configuration...")
        
        validation_results = {
            'celery_config': validate_configuration(),
            'redis_health': redis_client.health_check(),
            'database_health': db_client.health_check(),
            'frame_extractor': {
                'status': 'healthy',
                'metrics': frame_extractor.get_extraction_metrics()
            },
            'ml_inference': {
                'status': 'healthy',
                'metrics': ensemble_generator.get_inference_metrics()
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Overall validation
        overall_valid = (
            validation_results['celery_config']['overall_valid']['valid'] and
            validation_results['redis_health']['status'] == 'healthy' and
            validation_results['database_health']['status'] == 'healthy'
        )
        
        validation_results['overall_valid'] = overall_valid
        
        if overall_valid:
            logger.info("System validation successful")
        else:
            logger.error("System validation failed")
        
        return validation_results
    
    def start_video_analysis(
        self,
        video_path: str,
        filename: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start video analysis task.
        
        Args:
            video_path: Path to video file
            filename: Video filename (optional)
            config: Analysis configuration (optional)
            
        Returns:
            Task initiation result
        """
        try:
            # Validate video file
            if not frame_extractor.validate_video_file(video_path):
                raise ValueError(f"Invalid video file: {video_path}")
            
            # Get file size
            file_size = os.path.getsize(video_path)
            
            # Generate analysis ID
            analysis_id = str(uuid.uuid4())
            
            # Set default filename if not provided
            if not filename:
                filename = os.path.basename(video_path)
            
            # Create analysis record in database
            from utils.db_client import create_analysis_record
            create_analysis_record(
                analysis_id=analysis_id,
                video_path=video_path,
                filename=filename,
                file_size=file_size,
                status='pending',
                config=config
            )
            
            # Start Celery task
            task_result = detect_video.delay(
                analysis_id=analysis_id,
                video_path=video_path,
                filename=filename,
                file_size=file_size,
                config=config
            )
            
            logger.info(f"Started video analysis task: {analysis_id} (task: {task_result.id})")
            
            return {
                'analysis_id': analysis_id,
                'task_id': task_result.id,
                'status': 'started',
                'video_path': video_path,
                'filename': filename,
                'file_size': file_size,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error starting video analysis: {str(e)}")
            raise
    
    def get_analysis_status(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis status from database.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Analysis status or None if not found
        """
        try:
            from utils.db_client import db_client
            return db_client.get_analysis_record(analysis_id)
        except Exception as e:
            logger.error(f"Error getting analysis status: {str(e)}")
            return None
    
    def get_analysis_results(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete analysis results.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Complete analysis results or None if not found
        """
        try:
            from utils.db_client import db_client
            return db_client.get_complete_analysis_result(analysis_id)
        except Exception as e:
            logger.error(f"Error getting analysis results: {str(e)}")
            return None
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Returns:
            System health information
        """
        try:
            # Get health check from Celery task
            health_task = health_check.delay()
            health_result = health_task.get(timeout=10)
            
            # Add additional system information
            health_result['system_info'] = {
                'uptime': (datetime.now(timezone.utc) - self.startup_time).total_seconds(),
                'python_version': sys.version,
                'working_directory': os.getcwd(),
                'environment_variables': {
                    'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES'),
                    'REDIS_HOST': os.getenv('REDIS_HOST'),
                    'DATABASE_URL': os.getenv('DATABASE_URL', 'Not set')
                }
            }
            
            return health_result
            
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {
                'overall_status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        try:
            return {
                'frame_extraction': frame_extractor.get_extraction_metrics(),
                'ml_inference': ensemble_generator.get_inference_metrics(),
                'redis_health': redis_client.health_check(),
                'database_health': db_client.health_check(),
                'system_uptime': (datetime.now(timezone.utc) - self.startup_time).total_seconds(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {'error': str(e)}
    
    def cleanup_resources(self):
        """Clean up system resources."""
        try:
            logger.info("Cleaning up system resources...")
            
            # Clean up ML resources
            ensemble_generator.cleanup()
            frame_extractor.cleanup()
            
            # Run cleanup task
            cleanup_task = cleanup_expired_results.delay()
            cleanup_result = cleanup_task.get(timeout=30)
            
            logger.info(f"Cleanup completed: {cleanup_result}")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description='Video Processing Pipeline')
    parser.add_argument('--mode', choices=['worker', 'client', 'test'], default='client',
                       help='Application mode')
    parser.add_argument('--video-path', type=str, help='Path to video file for analysis')
    parser.add_argument('--analysis-id', type=str, help='Analysis ID to check status/results')
    parser.add_argument('--action', choices=['analyze', 'status', 'results', 'health', 'metrics'],
                       default='health', help='Action to perform')
    parser.add_argument('--config', type=str, help='JSON configuration string')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = VideoProcessingPipeline()
    
    try:
        if args.mode == 'worker':
            logger.info("Starting Celery worker...")
            # This would typically be run with: celery -A celery_app.tasks worker --loglevel=info
            logger.info("To start worker, run: celery -A celery_app.tasks worker --loglevel=info")
            
        elif args.mode == 'client':
            logger.info("Running in client mode...")
            
            if args.action == 'analyze':
                if not args.video_path:
                    logger.error("Video path required for analysis")
                    return
                
                # Parse config if provided
                config = None
                if args.config:
                    import json
                    config = json.loads(args.config)
                
                result = pipeline.start_video_analysis(args.video_path, config=config)
                print(f"Analysis started: {result}")
                
            elif args.action == 'status':
                if not args.analysis_id:
                    logger.error("Analysis ID required for status check")
                    return
                
                status = pipeline.get_analysis_status(args.analysis_id)
                if status:
                    print(f"Analysis status: {status}")
                else:
                    print("Analysis not found")
                    
            elif args.action == 'results':
                if not args.analysis_id:
                    logger.error("Analysis ID required for results")
                    return
                
                results = pipeline.get_analysis_results(args.analysis_id)
                if results:
                    print(f"Analysis results: {results}")
                else:
                    print("Analysis results not found")
                    
            elif args.action == 'health':
                health = pipeline.get_system_health()
                print(f"System health: {health}")
                
            elif args.action == 'metrics':
                metrics = pipeline.get_performance_metrics()
                print(f"Performance metrics: {metrics}")
        
        elif args.mode == 'test':
            logger.info("Running system tests...")
            
            # Validate system
            validation = pipeline.validate_system()
            print(f"System validation: {validation}")
            
            if validation['overall_valid']:
                logger.info("System validation passed")
            else:
                logger.error("System validation failed")
                return
            
            # Test video analysis if video path provided
            if args.video_path:
                logger.info(f"Testing video analysis with: {args.video_path}")
                result = pipeline.start_video_analysis(args.video_path)
                print(f"Test analysis started: {result}")
    
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise
    finally:
        # Cleanup
        pipeline.cleanup_resources()


if __name__ == '__main__':
    main()
