#!/usr/bin/env python3
"""
Detection Configuration
Configuration settings for video detection API including file upload constraints and processing options
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class DetectionConfig:
    """Configuration settings for video detection API"""
    
    # File upload constraints
    max_file_size_bytes: int = 524288000  # 500MB
    allowed_video_formats: List[str] = field(default_factory=lambda: ["mp4", "avi", "mov"])
    max_file_size_mb: int = 500
    
    # Processing settings
    max_processing_time_minutes: int = 30
    max_concurrent_analyses: int = 10
    frame_sampling_rate: int = 1
    
    # Detection methods
    default_detection_methods: List[str] = field(default_factory=lambda: ["resnet50", "clip"])
    confidence_threshold: float = 0.5
    
    # Storage settings
    upload_folder: str = "uploads"
    results_folder: str = "results"
    temp_folder: str = "temp"
    
    # API settings
    api_version: str = "v1"
    enable_blockchain_verification: bool = True
    enable_real_time_status: bool = True
    
    # NEW: Enhanced visualization settings
    enable_visualization_data: bool = True
    enable_interactive_navigation: bool = True
    enable_heatmap_generation: bool = True
    enable_confidence_visualization: bool = True
    
    # Performance settings
    chunk_size_bytes: int = 8192
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.allowed_video_formats is None:
            self.allowed_video_formats = ['mp4', 'avi', 'mov']
        
        if self.default_detection_methods is None:
            self.default_detection_methods = ['resnet50', 'clip', 'ensemble']
    
    @classmethod
    def from_env(cls) -> 'DetectionConfig':
        """Create detection config from environment variables"""
        return cls(
            max_file_size_bytes=int(os.getenv('DETECTION_MAX_FILE_SIZE', '524288000')),
            max_file_size_mb=int(os.getenv('DETECTION_MAX_FILE_SIZE_MB', '500')),
            max_processing_time_minutes=int(os.getenv('DETECTION_MAX_PROCESSING_TIME', '30')),
            max_concurrent_analyses=int(os.getenv('DETECTION_MAX_CONCURRENT', '10')),
            frame_sampling_rate=int(os.getenv('DETECTION_FRAME_SAMPLING_RATE', '1')),
            confidence_threshold=float(os.getenv('DETECTION_CONFIDENCE_THRESHOLD', '0.5')),
            upload_folder=os.getenv('DETECTION_UPLOAD_FOLDER', 'uploads'),
            results_folder=os.getenv('DETECTION_RESULTS_FOLDER', 'results'),
            temp_folder=os.getenv('DETECTION_TEMP_FOLDER', 'temp'),
            api_version=os.getenv('DETECTION_API_VERSION', 'v1'),
            enable_blockchain_verification=os.getenv('DETECTION_ENABLE_BLOCKCHAIN', 'true').lower() == 'true',
            enable_real_time_status=os.getenv('DETECTION_ENABLE_REALTIME', 'true').lower() == 'true',
            chunk_size_bytes=int(os.getenv('DETECTION_CHUNK_SIZE', '8192')),
            max_retries=int(os.getenv('DETECTION_MAX_RETRIES', '3')),
            retry_delay_seconds=int(os.getenv('DETECTION_RETRY_DELAY', '5'))
        )
    
    @property
    def max_file_size_formatted(self) -> str:
        """Get max file size in human readable format"""
        if self.max_file_size_bytes >= 1024 * 1024:
            return f"{self.max_file_size_bytes / (1024 * 1024):.0f}MB"
        elif self.max_file_size_bytes >= 1024:
            return f"{self.max_file_size_bytes / 1024:.0f}KB"
        else:
            return f"{self.max_file_size_bytes}B"
    
    @property
    def max_processing_time_timedelta(self) -> timedelta:
        """Get max processing time as timedelta"""
        return timedelta(minutes=self.max_processing_time_minutes)
    
    def validate_file_format(self, filename: str) -> bool:
        """
        Validate if file format is supported.
        
        Args:
            filename: Name of the file
            
        Returns:
            bool: True if format is supported
            
        Raises:
            ValueError: If format is not supported
        """
        if not filename:
            raise ValueError("No filename provided")
        
        file_extension = filename.lower().split('.')[-1]
        if file_extension not in self.allowed_video_formats:
            raise ValueError(f"Unsupported file format '{file_extension}'. Supported formats: {', '.join(self.allowed_video_formats)}")
        
        return True
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate if file size is within limits.
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            bool: True if size is valid
            
        Raises:
            ValueError: If size exceeds limit
        """
        if file_size > self.max_file_size_bytes:
            file_size_mb = file_size / (1024 * 1024)
            max_size_mb = self.max_file_size_bytes / (1024 * 1024)
            raise ValueError(f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB)")
        
        return True
    
    def get_detection_methods(self, custom_methods: Optional[List[str]] = None) -> List[str]:
        """
        Get detection methods to use.
        
        Args:
            custom_methods: Custom methods provided by user
            
        Returns:
            List[str]: Detection methods to use
        """
        if custom_methods:
            # Validate custom methods
            valid_methods = ['resnet50', 'clip', 'ensemble', 'diffusion_aware']
            for method in custom_methods:
                if method not in valid_methods:
                    raise ValueError(f"Invalid detection method '{method}'. Valid methods: {', '.join(valid_methods)}")
            return custom_methods
        
        return self.default_detection_methods.copy()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get configuration summary for debugging and monitoring.
        
        Returns:
            Dict[str, Any]: Configuration summary
        """
        return {
            'file_upload': {
                'max_file_size_bytes': self.max_file_size_bytes,
                'max_file_size_formatted': self.max_file_size_formatted,
                'allowed_formats': self.allowed_video_formats
            },
            'processing': {
                'max_processing_time_minutes': self.max_processing_time_minutes,
                'max_concurrent_analyses': self.max_concurrent_analyses,
                'frame_sampling_rate': self.frame_sampling_rate,
                'confidence_threshold': self.confidence_threshold
            },
            'detection_methods': {
                'default_methods': self.default_detection_methods,
                'available_methods': ['resnet50', 'clip', 'ensemble', 'diffusion_aware']
            },
            'storage': {
                'upload_folder': self.upload_folder,
                'results_folder': self.results_folder,
                'temp_folder': self.temp_folder
            },
            'api': {
                'version': self.api_version,
                'enable_blockchain_verification': self.enable_blockchain_verification,
                'enable_real_time_status': self.enable_real_time_status
            },
            'performance': {
                'chunk_size_bytes': self.chunk_size_bytes,
                'max_retries': self.max_retries,
                'retry_delay_seconds': self.retry_delay_seconds
            }
        }


@dataclass
class ProcessingConfig:
    """Configuration for video processing pipeline"""
    
    # Frame processing
    frame_extraction_fps: float = 1.0
    max_frames_per_analysis: int = 1000
    frame_resize_width: int = 224
    frame_resize_height: int = 224
    
    # Detection thresholds
    face_detection_confidence: float = 0.5
    anomaly_detection_threshold: float = 0.7
    temporal_consistency_threshold: float = 0.8
    
    # Performance optimization
    enable_gpu_acceleration: bool = True
    batch_size: int = 32
    num_workers: int = 4
    
    # Quality control
    min_video_duration_seconds: float = 1.0
    max_video_duration_seconds: float = 300.0  # 5 minutes
    min_resolution_width: int = 64
    min_resolution_height: int = 64
    
    @classmethod
    def from_env(cls) -> 'ProcessingConfig':
        """Create processing config from environment variables"""
        return cls(
            frame_extraction_fps=float(os.getenv('PROCESSING_FRAME_FPS', '1.0')),
            max_frames_per_analysis=int(os.getenv('PROCESSING_MAX_FRAMES', '1000')),
            frame_resize_width=int(os.getenv('PROCESSING_FRAME_WIDTH', '224')),
            frame_resize_height=int(os.getenv('PROCESSING_FRAME_HEIGHT', '224')),
            face_detection_confidence=float(os.getenv('PROCESSING_FACE_CONFIDENCE', '0.5')),
            anomaly_detection_threshold=float(os.getenv('PROCESSING_ANOMALY_THRESHOLD', '0.7')),
            temporal_consistency_threshold=float(os.getenv('PROCESSING_TEMPORAL_THRESHOLD', '0.8')),
            enable_gpu_acceleration=os.getenv('PROCESSING_ENABLE_GPU', 'true').lower() == 'true',
            batch_size=int(os.getenv('PROCESSING_BATCH_SIZE', '32')),
            num_workers=int(os.getenv('PROCESSING_NUM_WORKERS', '4')),
            min_video_duration_seconds=float(os.getenv('PROCESSING_MIN_DURATION', '1.0')),
            max_video_duration_seconds=float(os.getenv('PROCESSING_MAX_DURATION', '300.0')),
            min_resolution_width=int(os.getenv('PROCESSING_MIN_WIDTH', '64')),
            min_resolution_height=int(os.getenv('PROCESSING_MIN_HEIGHT', '64'))
        )


@dataclass
class APIConfig:
    """Configuration for API behavior and responses"""
    
    # Response settings
    include_debug_info: bool = False
    include_processing_details: bool = True
    include_frame_analysis: bool = True
    include_suspicious_regions: bool = True
    
    # Rate limiting
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    
    # Caching
    enable_response_caching: bool = True
    cache_ttl_seconds: int = 3600
    
    # Security
    require_authentication: bool = False
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ['*'])
    
    def __post_init__(self):
        """Initialize default values after dataclass creation"""
        if self.allowed_origins is None:
            self.allowed_origins = ['*']
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """Create API config from environment variables"""
        return cls(
            include_debug_info=os.getenv('API_INCLUDE_DEBUG', 'false').lower() == 'true',
            include_processing_details=os.getenv('API_INCLUDE_PROCESSING', 'true').lower() == 'true',
            include_frame_analysis=os.getenv('API_INCLUDE_FRAMES', 'true').lower() == 'true',
            include_suspicious_regions=os.getenv('API_INCLUDE_REGIONS', 'true').lower() == 'true',
            requests_per_minute=int(os.getenv('API_RATE_LIMIT_MINUTE', '60')),
            requests_per_hour=int(os.getenv('API_RATE_LIMIT_HOUR', '1000')),
            enable_response_caching=os.getenv('API_ENABLE_CACHE', 'true').lower() == 'true',
            cache_ttl_seconds=int(os.getenv('API_CACHE_TTL', '3600')),
            require_authentication=os.getenv('API_REQUIRE_AUTH', 'false').lower() == 'true',
            enable_cors=os.getenv('API_ENABLE_CORS', 'true').lower() == 'true'
        )


class DetectionSettings:
    """Main configuration class for detection API"""
    
    def __init__(self):
        self.detection = DetectionConfig.from_env()
        self.processing = ProcessingConfig.from_env()
        self.api = APIConfig.from_env()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate configuration and return validation results.
        
        Returns:
            Dict[str, Any]: Validation results
        """
        validation_results = {
            'detection': {
                'max_file_size_valid': self.detection.max_file_size_bytes > 0,
                'allowed_formats_configured': len(self.detection.allowed_video_formats) > 0,
                'processing_time_valid': self.detection.max_processing_time_minutes > 0,
                'concurrent_limit_valid': self.detection.max_concurrent_analyses > 0
            },
            'processing': {
                'frame_fps_valid': self.processing.frame_extraction_fps > 0,
                'max_frames_valid': self.processing.max_frames_per_analysis > 0,
                'resolution_valid': (
                    self.processing.frame_resize_width > 0 and 
                    self.processing.frame_resize_height > 0
                ),
                'duration_limits_valid': (
                    self.processing.min_video_duration_seconds > 0 and
                    self.processing.max_video_duration_seconds > self.processing.min_video_duration_seconds
                )
            },
            'api': {
                'rate_limits_valid': (
                    self.api.requests_per_minute > 0 and
                    self.api.requests_per_hour > 0
                ),
                'cache_ttl_valid': self.api.cache_ttl_seconds > 0
            }
        }
        
        # Overall validation
        overall_valid = all(
            all(section.values()) for section in validation_results.values()
            if isinstance(section, dict)
        )
        validation_results['overall_valid'] = {'valid': overall_valid}
        
        return validation_results
    
    def get_complete_config_summary(self) -> Dict[str, Any]:
        """
        Get complete configuration summary.
        
        Returns:
            Dict[str, Any]: Complete configuration summary
        """
        return {
            'detection': self.detection.get_config_summary(),
            'processing': {
                'frame_processing': {
                    'extraction_fps': self.processing.frame_extraction_fps,
                    'max_frames': self.processing.max_frames_per_analysis,
                    'resize_dimensions': f"{self.processing.frame_resize_width}x{self.processing.frame_resize_height}"
                },
                'detection_thresholds': {
                    'face_detection_confidence': self.processing.face_detection_confidence,
                    'anomaly_detection_threshold': self.processing.anomaly_detection_threshold,
                    'temporal_consistency_threshold': self.processing.temporal_consistency_threshold
                },
                'performance': {
                    'gpu_acceleration': self.processing.enable_gpu_acceleration,
                    'batch_size': self.processing.batch_size,
                    'num_workers': self.processing.num_workers
                },
                'quality_control': {
                    'min_duration_seconds': self.processing.min_video_duration_seconds,
                    'max_duration_seconds': self.processing.max_video_duration_seconds,
                    'min_resolution': f"{self.processing.min_resolution_width}x{self.processing.min_resolution_height}"
                }
            },
            'api': {
                'response_settings': {
                    'include_debug_info': self.api.include_debug_info,
                    'include_processing_details': self.api.include_processing_details,
                    'include_frame_analysis': self.api.include_frame_analysis,
                    'include_suspicious_regions': self.api.include_suspicious_regions
                },
                'rate_limiting': {
                    'requests_per_minute': self.api.requests_per_minute,
                    'requests_per_hour': self.api.requests_per_hour
                },
                'caching': {
                    'enabled': self.api.enable_response_caching,
                    'ttl_seconds': self.api.cache_ttl_seconds
                },
                'security': {
                    'require_authentication': self.api.require_authentication,
                    'enable_cors': self.api.enable_cors,
                    'allowed_origins': self.api.allowed_origins
                }
            },
            'validation': self.validate_configuration()
        }


# Global configuration instance
@dataclass
class VisualizationDataStoreConfig:
    """Configuration for visualization data store connections"""
    
    # Data store type and connection
    store_type: str = "redis"  # "redis", "postgresql", "mongodb"
    connection_url: Optional[str] = None
    database_name: str = "visualization_data"
    
    # Caching settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_size_mb: int = 500
    cache_cleanup_interval_seconds: int = 300  # 5 minutes
    
    # Data generation settings
    enable_heatmap_generation: bool = True
    enable_region_coordinates: bool = True
    enable_frame_navigation: bool = True
    enable_confidence_visualization: bool = True
    
    # Performance settings
    max_processing_time_ms: int = 50  # Keep under 100ms total
    parallel_processing_enabled: bool = True
    batch_size: int = 100


@dataclass
class SolanaBlockchainConfig:
    """Configuration for Solana blockchain connections and verification"""
    
    # Network settings
    enable_solana_integration: bool = True
    network_url: str = "https://api.mainnet-beta.solana.com"
    network_type: str = "mainnet-beta"  # "mainnet-beta", "testnet", "devnet"
    
    # RPC connection settings
    rpc_timeout_seconds: int = 5
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # Verification settings
    enable_real_time_verification: bool = True
    verification_cache_ttl_seconds: int = 300  # 5 minutes
    force_verification_freshness_seconds: int = 60  # 1 minute
    
    # Performance optimizations
    enable_transaction_caching: bool = True
    batch_verification_enabled: bool = True
    max_concurrent_verifications: int = 10
    
    # Security settings
    verify_transaction_signatures: bool = True
    enable_signature_validation: bool = True
    trusted_validator_set: Optional[List[str]] = None


@dataclass
class EnhancedDetectionSettings:
    """Enhanced configuration settings combining all detection services"""
    
    def __init__(self):
        self.detection = DetectionConfig()
        self.visualization_data_store = VisualizationDataStoreConfig()
        self.solana_blockchain = SolanaBlockchainConfig()
        self.redis = self._get_redis_config()
        
    def _get_redis_config(self):
        """Get Redis configuration from environment variables"""
        return {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD'),
            'decode_responses': True,
            'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '20'))
        }
    
    def get_complete_config_summary(self) -> Dict[str, Any]:
        """Get complete configuration summary"""
        return {
            'detection': {
                'max_file_size_mb': self.detection.max_file_size_mb,
                'allowed_formats': self.detection.allowed_video_formats,
                'enable_visualization_data': self.detection.enable_visualization_data,
                'enable_interactive_navigation': self.detection.enable_interactive_navigation,
                'enable_heatmap_generation': self.detection.enable_heatmap_generation,
                'enable_confidence_visualization': self.detection.enable_confidence_visualization,
                'enable_blockchain_verification': self.detection.enable_blockchain_verification
            },
            'visualization_data_store': {
                'store_type': self.visualization_data_store.store_type,
                'enable_caching': self.visualization_data_store.enable_caching,
                'cache_ttl_seconds': self.visualization_data_store.cache_ttl_seconds,
                'max_cache_size_mb': self.visualization_data_store.max_cache_size_mb,
                'enable_heatmap_generation': self.visualization_data_store.enable_heatmap_generation,
                'max_processing_time_ms': self.visualization_data_store.max_processing_time_ms
            },
            'solana_blockchain': {
                'enable_solana_integration': self.solana_blockchain.enable_solana_integration,
                'network_url': self.solana_blockchain.network_url,
                'network_type': self.solana_blockchain.network_type,
                'enable_real_time_verification': self.solana_blockchain.enable_real_time_verification,
                'verification_cache_ttl_seconds': self.solana_blockchain.verification_cache_ttl_seconds,
                'rpc_timeout_seconds': self.solana_blockchain.rpc_timeout_seconds
            },
            'redis': {
                'host': self.redis['host'],
                'port': self.redis['port'],
                'db': self.redis['db'],
                'max_connections': self.redis['max_connections']
            }
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate enhanced configuration"""
        validation_results = {
            'detection': {
                'max_file_size_valid': self.detection.max_file_size_mb > 0 and self.detection.max_file_size_mb <= 2000,
                'allowed_formats_configured': len(self.detection.allowed_video_formats) > 0,
                'visualization_settings_valid': all([
                    isinstance(self.detection.enable_visualization_data, bool),
                    isinstance(self.detection.enable_interactive_navigation, bool),
                    isinstance(self.detection.enable_heatmap_generation, bool),
                    isinstance(self.detection.enable_confidence_visualization, bool)
                ])
            },
            'visualization_data_store': {
                'store_type_valid': self.visualization_data_store.store_type in ['redis', 'postgresql', 'mongodb'],
                'cache_settings_valid': (
                    self.visualization_data_store.cache_ttl_seconds > 0 and
                    self.visualization_data_store.max_cache_size_mb > 0 and
                    self.visualization_data_store.max_processing_time_ms <= 100  # Maintain sub-100ms requirement
                ),
                'feature_flags_valid': all([
                    isinstance(self.visualization_data_store.enable_heatmap_generation, bool),
                    isinstance(self.visualization_data_store.enable_region_coordinates, bool),
                    isinstance(self.visualization_data_store.enable_frame_navigation, bool),
                    isinstance(self.visualization_data_store.enable_confidence_visualization, bool)
                ])
            },
            'solana_blockchain': {
                'network_settings_valid': bool(self.solana_blockchain.network_url),
                'rpc_settings_valid': (
                    self.solana_blockchain.rpc_timeout_seconds > 0 and
                    self.solana_blockchain.max_retries > 0
                ),
                'verification_settings_valid': (
                    self.solana_blockchain.verification_cache_ttl_seconds > 0 and
                    isinstance(self.solana_blockchain.enable_real_time_verification, bool)
                )
            },
            'redis': {
                'host_configured': bool(self.redis['host']),
                'port_valid': 1 <= self.redis['port'] <= 65535,
                'max_connections_valid': self.redis['max_connections'] > 0
            }
        }
        
        # Overall validation
        validation_results['overall_valid'] = all(
            all(section.values()) for section in validation_results.values()
            if isinstance(section, dict) and 'overall_valid' not in section
        )
        
        return validation_results


detection_settings = DetectionSettings()
enhanced_detection_settings = EnhancedDetectionSettings()


# Configuration validation functions
def validate_detection_configuration() -> bool:
    """Validate detection configuration"""
    validation_results = detection_settings.validate_configuration()
    return validation_results['overall_valid']


def get_detection_config_summary() -> Dict[str, Any]:
    """Get detection configuration summary for debugging"""
    return detection_settings.get_complete_config_summary()


# Export main classes and functions
__all__ = [
    'DetectionConfig',
    'ProcessingConfig',
    'APIConfig',
    'VisualizationDataStoreConfig',
    'SolanaBlockchainConfig',
    'EnhancedDetectionSettings',
    'DetectionSettings',
    'detection_settings',
    'enhanced_detection_settings',
    'validate_detection_configuration',
    'get_detection_config_summary'
]
