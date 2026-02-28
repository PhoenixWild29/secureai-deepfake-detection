"""
Analysis Status Models
Pydantic models for analysis status API responses
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ProcessingStageStatus(str, Enum):
    """Processing stage status enumeration"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"

class WorkerStatus(str, Enum):
    """Worker status enumeration"""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class GPUStatus(str, Enum):
    """GPU status enumeration"""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class QueueStatus(str, Enum):
    """Queue status enumeration"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class QueuePriority(str, Enum):
    """Queue priority enumeration"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class ErrorSeverity(str, Enum):
    """Error severity enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryActionType(str, Enum):
    """Recovery action type enumeration"""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL = "manual"

class AnalysisStatus(str, Enum):
    """Analysis status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RecoveryActionResponse(BaseModel):
    """Recovery action response model"""
    id: str = Field(..., description="Action identifier")
    description: str = Field(..., description="Action description")
    type: RecoveryActionType = Field(..., description="Action type")
    requires_confirmation: bool = Field(..., description="Whether action requires user confirmation")

class StageErrorResponse(BaseModel):
    """Stage error response model"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    severity: ErrorSeverity = Field(..., description="Error severity")
    recoverable: bool = Field(..., description="Whether the error is recoverable")
    timestamp: datetime = Field(..., description="Error timestamp")
    recovery_actions: List[RecoveryActionResponse] = Field(default=[], description="Recovery actions")

class ProcessingStageResponse(BaseModel):
    """Processing stage response model"""
    id: str = Field(..., description="Stage identifier")
    name: str = Field(..., description="Stage display name")
    description: str = Field(..., description="Stage description")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    is_active: bool = Field(..., description="Whether this stage is currently active")
    is_completed: bool = Field(..., description="Whether this stage is completed")
    has_error: bool = Field(..., description="Whether this stage has an error")
    is_skipped: bool = Field(..., description="Whether this stage is skipped")
    start_time: Optional[datetime] = Field(None, description="Stage start time")
    end_time: Optional[datetime] = Field(None, description="Stage end time")
    estimated_duration: int = Field(..., description="Estimated duration in milliseconds")
    actual_duration: Optional[int] = Field(None, description="Actual duration in milliseconds")
    error: Optional[StageErrorResponse] = Field(None, description="Error information if any")
    metadata: Dict[str, Any] = Field(default={}, description="Stage-specific metadata")

class WorkerInfoResponse(BaseModel):
    """Worker information response model"""
    id: str = Field(..., description="Worker identifier")
    name: str = Field(..., description="Worker name")
    status: WorkerStatus = Field(..., description="Worker status")
    current_task: Optional[str] = Field(None, description="Current task being processed")
    task_start_time: Optional[datetime] = Field(None, description="Task start time")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_usage: float = Field(..., ge=0, description="Memory usage in MB")
    uptime: int = Field(..., ge=0, description="Worker uptime in seconds")
    tasks_completed: int = Field(..., ge=0, description="Number of tasks completed")
    metadata: Dict[str, Any] = Field(default={}, description="Worker metadata")

class GPUInfoResponse(BaseModel):
    """GPU information response model"""
    id: str = Field(..., description="GPU identifier")
    name: str = Field(..., description="GPU name")
    status: GPUStatus = Field(..., description="GPU status")
    utilization: float = Field(..., ge=0, le=100, description="GPU utilization percentage")
    memory_used: float = Field(..., ge=0, description="Memory used in MB")
    memory_total: float = Field(..., ge=0, description="Total memory in MB")
    memory_usage_percentage: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    temperature: float = Field(..., ge=0, description="Temperature in Celsius")
    power_usage: float = Field(..., ge=0, description="Power usage in Watts")
    current_task: Optional[str] = Field(None, description="Current task being processed")
    task_start_time: Optional[datetime] = Field(None, description="Task start time")
    metadata: Dict[str, Any] = Field(default={}, description="GPU metadata")

class QueueInfoResponse(BaseModel):
    """Queue information response model"""
    id: str = Field(..., description="Queue identifier")
    name: str = Field(..., description="Queue name")
    position: int = Field(..., ge=0, description="Current position in queue")
    total_items: int = Field(..., ge=0, description="Total items in queue")
    estimated_wait_time: int = Field(..., ge=0, description="Estimated wait time in seconds")
    priority: QueuePriority = Field(..., description="Queue priority")
    status: QueueStatus = Field(..., description="Queue status")
    processing_rate: float = Field(..., ge=0, description="Items processed per minute")
    average_processing_time: int = Field(..., ge=0, description="Average processing time per item in seconds")
    metadata: Dict[str, Any] = Field(default={}, description="Queue metadata")

class ResourceMetricsResponse(BaseModel):
    """Resource metrics response model"""
    system_cpu_usage: float = Field(..., ge=0, le=100, description="System CPU usage percentage")
    system_memory_used: float = Field(..., ge=0, description="System memory used in bytes")
    system_memory_total: float = Field(..., ge=0, description="Total system memory in bytes")
    system_memory_usage_percentage: float = Field(..., ge=0, le=100, description="System memory usage percentage")
    disk_usage_percentage: float = Field(..., ge=0, le=100, description="Disk usage percentage")
    network_io: float = Field(..., ge=0, description="Network I/O in MB/s")
    timestamp: datetime = Field(..., description="Metrics collection timestamp")

class AnalysisStatusResponse(BaseModel):
    """Comprehensive analysis status response model"""
    analysis_id: str = Field(..., description="Analysis identifier")
    current_stage: str = Field(..., description="Current processing stage")
    overall_progress: float = Field(..., ge=0, le=100, description="Overall progress percentage")
    start_time: datetime = Field(..., description="Analysis start time")
    last_update: datetime = Field(..., description="Last update time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    stages: List[ProcessingStageResponse] = Field(..., description="Processing stages information")
    workers: List[WorkerInfoResponse] = Field(..., description="Worker allocation information")
    gpus: List[GPUInfoResponse] = Field(..., description="GPU resource information")
    queue: Optional[QueueInfoResponse] = Field(None, description="Queue information")
    resource_metrics: Optional[ResourceMetricsResponse] = Field(None, description="System resource metrics")
    status: AnalysisStatus = Field(..., description="Analysis status")
    error: Optional[StageErrorResponse] = Field(None, description="Error information if any")
    metadata: Dict[str, Any] = Field(default={}, description="Analysis metadata")

class AnalysisHistoryEntry(BaseModel):
    """Analysis history entry model"""
    timestamp: datetime = Field(..., description="Entry timestamp")
    stage: str = Field(..., description="Processing stage")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage")
    status: str = Field(..., description="Status at this point")
    metadata: Dict[str, Any] = Field(default={}, description="Entry metadata")

class AnalysisHistoryResponse(BaseModel):
    """Analysis history response model"""
    analysis_id: str = Field(..., description="Analysis identifier")
    history: List[AnalysisHistoryEntry] = Field(..., description="Historical entries")
    count: int = Field(..., description="Number of entries returned")
    timestamp: datetime = Field(..., description="Response timestamp")

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    service: str = Field(..., description="Service name")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
