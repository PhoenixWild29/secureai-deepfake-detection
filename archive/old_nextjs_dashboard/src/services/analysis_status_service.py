"""
Analysis Status Service
Service for aggregating analysis processing status and resource monitoring data
"""

import asyncio
import psutil
import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import json
import subprocess
import os

from ..models.analysis_status import (
    AnalysisStatusResponse,
    ProcessingStageResponse,
    WorkerInfoResponse,
    GPUInfoResponse,
    QueueInfoResponse,
    ResourceMetricsResponse,
    StageErrorResponse,
    RecoveryActionResponse
)
from ..utils.redis_cache import DashboardCacheManager
from ..config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

class AnalysisStatusService:
    """Service for aggregating analysis status and resource monitoring data"""
    
    def __init__(self):
        self.cache_manager = DashboardCacheManager()
        self.celery_app = None  # Will be initialized when needed
        self._initialize_celery()
    
    def _initialize_celery(self):
        """Initialize Celery app for worker inspection"""
        try:
            # Import Celery app - adjust import path as needed
            from ..celery_app import celery_app
            self.celery_app = celery_app
            logger.info("Celery app initialized successfully")
        except ImportError:
            logger.warning("Celery app not available, worker inspection will be limited")
    
    async def get_analysis_status(
        self,
        analysis_id: str,
        include_workers: bool = True,
        include_gpu: bool = True,
        include_queue: bool = True,
        include_resources: bool = True
    ) -> Optional[AnalysisStatusResponse]:
        """
        Get comprehensive analysis status including processing stages, worker allocation,
        GPU utilization, queue status, and system resource metrics.
        """
        try:
            logger.info(
                "Getting analysis status",
                analysis_id=analysis_id,
                include_workers=include_workers,
                include_gpu=include_gpu,
                include_queue=include_queue,
                include_resources=include_resources
            )

            # Get analysis data from cache or database
            analysis_data = await self._get_analysis_data(analysis_id)
            if not analysis_data:
                return None

            # Get processing stages
            stages = await self.get_analysis_stages(analysis_id)
            
            # Get worker information if requested
            workers = []
            if include_workers:
                workers = await self.get_workers_status()
            
            # Get GPU information if requested
            gpus = []
            if include_gpu:
                gpus = await self.get_gpu_status()
            
            # Get queue information if requested
            queue_info = None
            if include_queue:
                queue_info = await self.get_queue_status()
            
            # Get system resource metrics if requested
            resource_metrics = None
            if include_resources:
                resource_metrics = await self.get_system_metrics()

            # Calculate overall progress
            overall_progress = self._calculate_overall_progress(stages)
            
            # Determine current stage
            current_stage = self._get_current_stage(stages)
            
            # Estimate completion time
            estimated_completion = self._estimate_completion_time(analysis_data, stages)

            status_response = AnalysisStatusResponse(
                analysis_id=analysis_id,
                current_stage=current_stage,
                overall_progress=overall_progress,
                start_time=analysis_data.get('start_time', datetime.now(timezone.utc)),
                last_update=datetime.now(timezone.utc),
                estimated_completion=estimated_completion,
                stages=stages,
                workers=workers,
                gpus=gpus,
                queue=queue_info,
                resource_metrics=resource_metrics,
                status=analysis_data.get('status', 'pending'),
                error=self._get_analysis_error(analysis_data),
                metadata=analysis_data.get('metadata', {})
            )

            logger.info(
                "Analysis status retrieved successfully",
                analysis_id=analysis_id,
                current_stage=current_stage,
                overall_progress=overall_progress,
                status=status_response.status
            )

            return status_response

        except Exception as e:
            logger.error(
                "Error getting analysis status",
                analysis_id=analysis_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_analysis_stages(self, analysis_id: str) -> List[ProcessingStageResponse]:
        """Get detailed processing stages information for a specific analysis"""
        try:
            logger.info("Getting analysis stages", analysis_id=analysis_id)

            # Get stage data from cache or database
            stage_data = await self._get_stage_data(analysis_id)
            
            stages = []
            stage_configs = self._get_stage_configs()
            
            for stage_id, config in stage_configs.items():
                stage_info = stage_data.get(stage_id, {})
                
                stage_response = ProcessingStageResponse(
                    id=stage_id,
                    name=config['name'],
                    description=config['description'],
                    progress=stage_info.get('progress', 0),
                    is_active=stage_info.get('is_active', False),
                    is_completed=stage_info.get('is_completed', False),
                    has_error=stage_info.get('has_error', False),
                    is_skipped=stage_info.get('is_skipped', False),
                    start_time=stage_info.get('start_time'),
                    end_time=stage_info.get('end_time'),
                    estimated_duration=config['estimated_duration'],
                    actual_duration=stage_info.get('actual_duration'),
                    error=self._get_stage_error(stage_info),
                    metadata=stage_info.get('metadata', {})
                )
                
                stages.append(stage_response)

            logger.info(
                "Analysis stages retrieved successfully",
                analysis_id=analysis_id,
                stages_count=len(stages)
            )

            return stages

        except Exception as e:
            logger.error(
                "Error getting analysis stages",
                analysis_id=analysis_id,
                error=str(e),
                exc_info=True
            )
            raise

    async def get_workers_status(self) -> List[WorkerInfoResponse]:
        """Get current status of all Celery workers"""
        try:
            logger.info("Getting workers status")

            workers = []
            
            if self.celery_app:
                # Get worker information from Celery inspection
                inspect = self.celery_app.control.inspect()
                
                # Get active workers
                active_workers = inspect.active()
                stats = inspect.stats()
                registered = inspect.registered()
                
                if active_workers:
                    for worker_name, tasks in active_workers.items():
                        worker_stats = stats.get(worker_name, {})
                        worker_registered = registered.get(worker_name, [])
                        
                        # Get current task
                        current_task = None
                        task_start_time = None
                        if tasks:
                            current_task = tasks[0].get('name', 'Unknown')
                            task_start_time = datetime.fromtimestamp(
                                tasks[0].get('time_start', 0), 
                                tz=timezone.utc
                            )
                        
                        worker_response = WorkerInfoResponse(
                            id=worker_name,
                            name=worker_name,
                            status='busy' if tasks else 'idle',
                            current_task=current_task,
                            task_start_time=task_start_time,
                            cpu_usage=self._get_worker_cpu_usage(worker_name),
                            memory_usage=self._get_worker_memory_usage(worker_name),
                            uptime=worker_stats.get('uptime', 0),
                            tasks_completed=worker_stats.get('total', {}).get('tasks.succeeded', 0),
                            metadata={
                                'registered_tasks': worker_registered,
                                'stats': worker_stats
                            }
                        )
                        
                        workers.append(worker_response)
            else:
                # Fallback: create mock worker data
                workers = self._get_mock_workers()

            logger.info(
                "Workers status retrieved successfully",
                workers_count=len(workers)
            )

            return workers

        except Exception as e:
            logger.error(
                "Error getting workers status",
                error=str(e),
                exc_info=True
            )
            # Return mock data on error
            return self._get_mock_workers()

    async def get_gpu_status(self) -> List[GPUInfoResponse]:
        """Get current GPU utilization and status information"""
        try:
            logger.info("Getting GPU status")

            gpus = []
            
            # Try to get GPU information using nvidia-smi
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw', '--format=csv,noheader,nounits'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = [part.strip() for part in line.split(',')]
                            if len(parts) >= 7:
                                gpu_id = parts[0]
                                gpu_name = parts[1]
                                utilization = float(parts[2]) if parts[2] != 'N/A' else 0
                                memory_used = float(parts[3]) if parts[3] != 'N/A' else 0
                                memory_total = float(parts[4]) if parts[4] != 'N/A' else 0
                                temperature = float(parts[5]) if parts[5] != 'N/A' else 0
                                power_usage = float(parts[6]) if parts[6] != 'N/A' else 0
                                
                                memory_usage_percentage = (memory_used / memory_total * 100) if memory_total > 0 else 0
                                
                                gpu_response = GPUInfoResponse(
                                    id=f"gpu_{gpu_id}",
                                    name=gpu_name,
                                    status='active' if utilization > 0 else 'idle',
                                    utilization=utilization,
                                    memory_used=memory_used,
                                    memory_total=memory_total,
                                    memory_usage_percentage=memory_usage_percentage,
                                    temperature=temperature,
                                    power_usage=power_usage,
                                    current_task=None,  # Would need additional query
                                    task_start_time=None,
                                    metadata={
                                        'gpu_index': gpu_id,
                                        'driver_version': self._get_nvidia_driver_version()
                                    }
                                )
                                
                                gpus.append(gpu_response)
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
                logger.warning("nvidia-smi not available, using mock GPU data")
                gpus = self._get_mock_gpus()

            if not gpus:
                gpus = self._get_mock_gpus()

            logger.info(
                "GPU status retrieved successfully",
                gpus_count=len(gpus)
            )

            return gpus

        except Exception as e:
            logger.error(
                "Error getting GPU status",
                error=str(e),
                exc_info=True
            )
            return self._get_mock_gpus()

    async def get_queue_status(self, queue_id: Optional[str] = None) -> Optional[QueueInfoResponse]:
        """Get processing queue status and metrics"""
        try:
            logger.info("Getting queue status", queue_id=queue_id)

            # Get queue information from Redis or Celery
            queue_data = await self._get_queue_data(queue_id)
            
            if not queue_data:
                return None

            queue_response = QueueInfoResponse(
                id=queue_data.get('id', 'default'),
                name=queue_data.get('name', 'Processing Queue'),
                position=queue_data.get('position', 0),
                total_items=queue_data.get('total_items', 0),
                estimated_wait_time=queue_data.get('estimated_wait_time', 0),
                priority=queue_data.get('priority', 'normal'),
                status=queue_data.get('status', 'active'),
                processing_rate=queue_data.get('processing_rate', 0),
                average_processing_time=queue_data.get('average_processing_time', 0),
                metadata=queue_data.get('metadata', {})
            )

            logger.info(
                "Queue status retrieved successfully",
                queue_id=queue_response.id,
                position=queue_response.position,
                total_items=queue_response.total_items
            )

            return queue_response

        except Exception as e:
            logger.error(
                "Error getting queue status",
                queue_id=queue_id,
                error=str(e),
                exc_info=True
            )
            return None

    async def get_system_metrics(self) -> Optional[ResourceMetricsResponse]:
        """Get current system resource metrics"""
        try:
            logger.info("Getting system metrics")

            # Get CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_used = memory.used
            memory_total = memory.total
            memory_usage_percentage = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percentage = (disk.used / disk.total) * 100
            
            # Get network I/O
            network = psutil.net_io_counters()
            network_io = (network.bytes_sent + network.bytes_recv) / (1024 * 1024)  # Convert to MB

            metrics_response = ResourceMetricsResponse(
                system_cpu_usage=cpu_usage,
                system_memory_used=memory_used,
                system_memory_total=memory_total,
                system_memory_usage_percentage=memory_usage_percentage,
                disk_usage_percentage=disk_usage_percentage,
                network_io=network_io,
                timestamp=datetime.now(timezone.utc)
            )

            logger.info(
                "System metrics retrieved successfully",
                cpu_usage=cpu_usage,
                memory_usage=memory_usage_percentage,
                disk_usage=disk_usage_percentage
            )

            return metrics_response

        except Exception as e:
            logger.error(
                "Error getting system metrics",
                error=str(e),
                exc_info=True
            )
            return None

    async def get_analysis_history(
        self,
        analysis_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical status updates for a specific analysis"""
        try:
            logger.info("Getting analysis history", analysis_id=analysis_id, limit=limit)

            # Get history from cache or database
            history_data = await self._get_history_data(analysis_id, limit)
            
            logger.info(
                "Analysis history retrieved successfully",
                analysis_id=analysis_id,
                history_count=len(history_data)
            )

            return history_data

        except Exception as e:
            logger.error(
                "Error getting analysis history",
                analysis_id=analysis_id,
                error=str(e),
                exc_info=True
            )
            return []

    async def health_check(self) -> bool:
        """Check if the analysis status service is healthy"""
        try:
            # Check if we can get system metrics
            metrics = await self.get_system_metrics()
            return metrics is not None
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False

    # Helper methods

    def _get_stage_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get stage configuration definitions"""
        return {
            'upload': {
                'name': 'Upload',
                'description': 'Uploading video file to server',
                'estimated_duration': 5000
            },
            'frame_extraction': {
                'name': 'Frame Extraction',
                'description': 'Extracting frames from video',
                'estimated_duration': 10000
            },
            'feature_extraction': {
                'name': 'Feature Extraction',
                'description': 'Extracting AI features from frames',
                'estimated_duration': 15000
            },
            'ensemble_inference': {
                'name': 'AI Analysis',
                'description': 'Running ensemble deepfake detection',
                'estimated_duration': 30000
            },
            'result_aggregation': {
                'name': 'Result Processing',
                'description': 'Aggregating analysis results',
                'estimated_duration': 5000
            },
            'blockchain_verification': {
                'name': 'Blockchain Verification',
                'description': 'Verifying results on blockchain',
                'estimated_duration': 15000
            },
            'completed': {
                'name': 'Completed',
                'description': 'Analysis completed successfully',
                'estimated_duration': 0
            },
            'error': {
                'name': 'Error',
                'description': 'An error occurred during processing',
                'estimated_duration': 0
            }
        }

    async def _get_analysis_data(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get analysis data from cache or database"""
        # Try cache first
        cache_key = f"analysis:{analysis_id}"
        cached_data = await self.cache_manager.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Fallback to database or mock data
        return self._get_mock_analysis_data(analysis_id)

    async def _get_stage_data(self, analysis_id: str) -> Dict[str, Any]:
        """Get stage data for analysis"""
        cache_key = f"analysis_stages:{analysis_id}"
        cached_data = await self.cache_manager.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Return mock stage data
        return self._get_mock_stage_data()

    async def _get_queue_data(self, queue_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Get queue data"""
        cache_key = f"queue:{queue_id or 'default'}"
        cached_data = await self.cache_manager.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Return mock queue data
        return self._get_mock_queue_data()

    async def _get_history_data(self, analysis_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get analysis history data"""
        cache_key = f"analysis_history:{analysis_id}:{limit}"
        cached_data = await self.cache_manager.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # Return mock history data
        return self._get_mock_history_data(analysis_id, limit)

    def _calculate_overall_progress(self, stages: List[ProcessingStageResponse]) -> float:
        """Calculate overall progress from stages"""
        if not stages:
            return 0.0
        
        total_weight = len(stages)
        weighted_progress = sum(stage.progress for stage in stages)
        
        return weighted_progress / total_weight

    def _get_current_stage(self, stages: List[ProcessingStageResponse]) -> str:
        """Get current active stage"""
        for stage in stages:
            if stage.is_active:
                return stage.id
        
        # Find the last completed stage
        completed_stages = [stage for stage in stages if stage.is_completed]
        if completed_stages:
            return completed_stages[-1].id
        
        return 'upload'

    def _estimate_completion_time(self, analysis_data: Dict[str, Any], stages: List[ProcessingStageResponse]) -> Optional[datetime]:
        """Estimate completion time based on current progress"""
        start_time = analysis_data.get('start_time')
        if not start_time:
            return None
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        # Calculate total estimated duration
        total_duration = sum(stage.estimated_duration for stage in stages)
        
        # Calculate current progress
        overall_progress = self._calculate_overall_progress(stages)
        
        if overall_progress > 0:
            # Estimate remaining time
            elapsed = datetime.now(timezone.utc) - start_time
            estimated_total = elapsed / (overall_progress / 100)
            remaining = estimated_total - elapsed
            
            return datetime.now(timezone.utc) + remaining
        
        return None

    def _get_analysis_error(self, analysis_data: Dict[str, Any]) -> Optional[StageErrorResponse]:
        """Get analysis error if any"""
        error_data = analysis_data.get('error')
        if not error_data:
            return None
        
        return StageErrorResponse(
            code=error_data.get('code', 'UNKNOWN_ERROR'),
            message=error_data.get('message', 'An unknown error occurred'),
            severity=error_data.get('severity', 'medium'),
            recoverable=error_data.get('recoverable', False),
            timestamp=datetime.fromisoformat(error_data.get('timestamp', datetime.now(timezone.utc).isoformat())),
            recovery_actions=[
                RecoveryActionResponse(
                    id=action.get('id', ''),
                    description=action.get('description', ''),
                    type=action.get('type', 'manual'),
                    requires_confirmation=action.get('requires_confirmation', False)
                )
                for action in error_data.get('recovery_actions', [])
            ]
        )

    def _get_stage_error(self, stage_info: Dict[str, Any]) -> Optional[StageErrorResponse]:
        """Get stage error if any"""
        error_data = stage_info.get('error')
        if not error_data:
            return None
        
        return StageErrorResponse(
            code=error_data.get('code', 'STAGE_ERROR'),
            message=error_data.get('message', 'Stage processing error'),
            severity=error_data.get('severity', 'medium'),
            recoverable=error_data.get('recoverable', False),
            timestamp=datetime.fromisoformat(error_data.get('timestamp', datetime.now(timezone.utc).isoformat())),
            recovery_actions=[
                RecoveryActionResponse(
                    id=action.get('id', ''),
                    description=action.get('description', ''),
                    type=action.get('type', 'manual'),
                    requires_confirmation=action.get('requires_confirmation', False)
                )
                for action in error_data.get('recovery_actions', [])
            ]
        )

    def _get_worker_cpu_usage(self, worker_name: str) -> float:
        """Get CPU usage for a specific worker"""
        # This would require additional system monitoring
        return 0.0

    def _get_worker_memory_usage(self, worker_name: str) -> float:
        """Get memory usage for a specific worker"""
        # This would require additional system monitoring
        return 0.0

    def _get_nvidia_driver_version(self) -> Optional[str]:
        """Get NVIDIA driver version"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    # Mock data methods for development/testing

    def _get_mock_analysis_data(self, analysis_id: str) -> Dict[str, Any]:
        """Get mock analysis data for development"""
        return {
            'id': analysis_id,
            'status': 'processing',
            'start_time': datetime.now(timezone.utc) - timedelta(minutes=5),
            'metadata': {
                'video_file': 'sample_video.mp4',
                'file_size': '125MB',
                'duration': '2:30'
            }
        }

    def _get_mock_stage_data(self) -> Dict[str, Any]:
        """Get mock stage data for development"""
        return {
            'upload': {
                'progress': 100,
                'is_completed': True,
                'is_active': False,
                'start_time': datetime.now(timezone.utc) - timedelta(minutes=5),
                'end_time': datetime.now(timezone.utc) - timedelta(minutes=4, seconds=30)
            },
            'frame_extraction': {
                'progress': 75,
                'is_completed': False,
                'is_active': True,
                'start_time': datetime.now(timezone.utc) - timedelta(minutes=4, seconds=30)
            },
            'feature_extraction': {
                'progress': 0,
                'is_completed': False,
                'is_active': False
            },
            'ensemble_inference': {
                'progress': 0,
                'is_completed': False,
                'is_active': False
            },
            'result_aggregation': {
                'progress': 0,
                'is_completed': False,
                'is_active': False
            },
            'blockchain_verification': {
                'progress': 0,
                'is_completed': False,
                'is_active': False
            }
        }

    def _get_mock_workers(self) -> List[WorkerInfoResponse]:
        """Get mock worker data for development"""
        return [
            WorkerInfoResponse(
                id='worker-1',
                name='worker-1@hostname',
                status='busy',
                current_task='extract_frames',
                task_start_time=datetime.now(timezone.utc) - timedelta(minutes=2),
                cpu_usage=45.2,
                memory_usage=1024,
                uptime=3600,
                tasks_completed=150,
                metadata={'hostname': 'hostname', 'pid': 1234}
            ),
            WorkerInfoResponse(
                id='worker-2',
                name='worker-2@hostname',
                status='idle',
                current_task=None,
                task_start_time=None,
                cpu_usage=12.1,
                memory_usage=512,
                uptime=3600,
                tasks_completed=98,
                metadata={'hostname': 'hostname', 'pid': 1235}
            )
        ]

    def _get_mock_gpus(self) -> List[GPUInfoResponse]:
        """Get mock GPU data for development"""
        return [
            GPUInfoResponse(
                id='gpu_0',
                name='NVIDIA GeForce RTX 4090',
                status='busy',
                utilization=85.5,
                memory_used=8192,
                memory_total=24576,
                memory_usage_percentage=33.3,
                temperature=72,
                power_usage=350,
                current_task='ensemble_inference',
                task_start_time=datetime.now(timezone.utc) - timedelta(minutes=1),
                metadata={'driver_version': '525.60.13', 'cuda_version': '12.0'}
            ),
            GPUInfoResponse(
                id='gpu_1',
                name='NVIDIA GeForce RTX 4090',
                status='idle',
                utilization=5.2,
                memory_used=1024,
                memory_total=24576,
                memory_usage_percentage=4.2,
                temperature=45,
                power_usage=50,
                current_task=None,
                task_start_time=None,
                metadata={'driver_version': '525.60.13', 'cuda_version': '12.0'}
            )
        ]

    def _get_mock_queue_data(self) -> Dict[str, Any]:
        """Get mock queue data for development"""
        return {
            'id': 'default',
            'name': 'Processing Queue',
            'position': 3,
            'total_items': 15,
            'estimated_wait_time': 300,
            'priority': 'normal',
            'status': 'active',
            'processing_rate': 2.5,
            'average_processing_time': 120,
            'metadata': {
                'queue_type': 'celery',
                'broker': 'redis'
            }
        }

    def _get_mock_history_data(self, analysis_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get mock history data for development"""
        history = []
        base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        for i in range(min(limit, 10)):
            history.append({
                'timestamp': (base_time + timedelta(minutes=i)).isoformat(),
                'stage': ['upload', 'frame_extraction', 'feature_extraction'][i % 3],
                'progress': (i + 1) * 10,
                'status': 'processing' if i < 9 else 'completed',
                'metadata': {
                    'worker': f'worker-{(i % 2) + 1}',
                    'gpu': f'gpu_{i % 2}'
                }
            })
        
        return history
