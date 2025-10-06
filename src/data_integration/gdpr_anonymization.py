#!/usr/bin/env python3
"""
GDPR Anonymization Module
Implements privacy-compliant data anonymization for analytics visualization
"""

import logging
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class AnonymizationMethod(str, Enum):
    """Available anonymization methods"""
    K_ANONYMITY = "k_anonymity"
    L_DIVERSITY = "l_diversity"
    T_CLOSENESS = "t_closeness"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    HASHING = "hashing"
    PSEUDONYMIZATION = "pseudonymization"
    GENERALIZATION = "generalization"
    SUPPRESSION = "suppression"


class PrivacyLevel(str, Enum):
    """Privacy protection levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class AnonymizationConfig:
    """Configuration for anonymization process"""
    method: AnonymizationMethod
    privacy_level: PrivacyLevel
    k_value: int = 3  # For k-anonymity
    l_value: int = 2  # For l-diversity
    epsilon: float = 1.0  # For differential privacy
    suppression_threshold: float = 0.05  # For suppression
    generalization_levels: Dict[str, int] = None


class AnonymizedData(BaseModel):
    """Model for anonymized data"""
    original_count: int = Field(..., description="Original number of records")
    anonymized_count: int = Field(..., description="Number of records after anonymization")
    suppression_rate: float = Field(..., description="Percentage of records suppressed")
    privacy_level: PrivacyLevel = Field(..., description="Privacy protection level applied")
    anonymization_method: AnonymizationMethod = Field(..., description="Method used for anonymization")
    data_quality_score: float = Field(..., description="Quality score of anonymized data (0.0-1.0)")


class GDPRAnonymizer:
    """
    GDPR-compliant data anonymization for analytics visualization
    Implements various anonymization techniques to protect user privacy
    """
    
    def __init__(self, config: Optional[AnonymizationConfig] = None):
        """
        Initialize GDPR anonymizer
        
        Args:
            config: Anonymization configuration
        """
        self.config = config or AnonymizationConfig(
            method=AnonymizationMethod.K_ANONYMITY,
            privacy_level=PrivacyLevel.MEDIUM
        )
        
        # Initialize anonymization statistics
        self.stats = {
            'total_anonymizations': 0,
            'total_records_processed': 0,
            'total_records_suppressed': 0,
            'methods_used': {},
            'privacy_levels_used': {}
        }
        
        logger.info(f"Initialized GDPR anonymizer with method: {self.config.method}")
    
    async def anonymize_analysis_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize individual analysis data
        
        Args:
            analysis_data: Raw analysis data
            
        Returns:
            Anonymized analysis data
        """
        try:
            logger.debug("Anonymizing analysis data")
            
            anonymized_data = analysis_data.copy()
            
            # Anonymize user identifiers
            if 'user_id' in anonymized_data:
                anonymized_data['user_id'] = self._pseudonymize_user_id(anonymized_data['user_id'])
            
            # Anonymize file information
            if 'filename' in anonymized_data:
                anonymized_data['filename'] = self._anonymize_filename(anonymized_data['filename'])
            
            if 'file_path' in anonymized_data:
                anonymized_data['file_path'] = self._anonymize_file_path(anonymized_data['file_path'])
            
            # Anonymize timestamps (generalize to hour/day level)
            if 'created_at' in anonymized_data:
                anonymized_data['created_at'] = self._generalize_timestamp(
                    anonymized_data['created_at'], 
                    self.config.privacy_level
                )
            
            if 'completed_at' in anonymized_data:
                anonymized_data['completed_at'] = self._generalize_timestamp(
                    anonymized_data['completed_at'], 
                    self.config.privacy_level
                )
            
            # Anonymize metadata
            if 'metadata' in anonymized_data and isinstance(anonymized_data['metadata'], dict):
                anonymized_data['metadata'] = self._anonymize_metadata(anonymized_data['metadata'])
            
            # Update statistics
            self._update_stats('analysis_data')
            
            logger.debug("Successfully anonymized analysis data")
            return anonymized_data
            
        except Exception as e:
            logger.error(f"Failed to anonymize analysis data: {str(e)}")
            # Return minimal safe data
            return {
                'id': self._generate_anonymous_id(),
                'status': analysis_data.get('status', 'unknown'),
                'created_at': self._generalize_timestamp(datetime.now(), PrivacyLevel.HIGH),
                'anonymized': True
            }
    
    async def anonymize_statistics_data(self, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize statistics data
        
        Args:
            stats_data: Raw statistics data
            
        Returns:
            Anonymized statistics data
        """
        try:
            logger.debug("Anonymizing statistics data")
            
            anonymized_stats = stats_data.copy()
            
            # Apply noise to sensitive numerical data
            sensitive_fields = [
                'total_analyses', 'completed_analyses', 'failed_analyses',
                'total_file_size', 'unique_videos'
            ]
            
            for field in sensitive_fields:
                if field in anonymized_stats and isinstance(anonymized_stats[field], (int, float)):
                    if self.config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
                        anonymized_stats[field] = self._add_differential_privacy_noise(
                            anonymized_stats[field]
                        )
                    elif self.config.privacy_level in [PrivacyLevel.HIGH, PrivacyLevel.MAXIMUM]:
                        # Round to nearest 5 or 10 for high privacy
                        anonymized_stats[field] = self._round_to_privacy_level(
                            anonymized_stats[field]
                        )
            
            # Anonymize timestamp
            if 'last_analysis' in anonymized_stats:
                anonymized_stats['last_analysis'] = self._generalize_timestamp(
                    anonymized_stats['last_analysis'],
                    self.config.privacy_level
                )
            
            # Update statistics
            self._update_stats('statistics_data')
            
            logger.debug("Successfully anonymized statistics data")
            return anonymized_stats
            
        except Exception as e:
            logger.error(f"Failed to anonymize statistics data: {str(e)}")
            return {}
    
    async def anonymize_performance_data(self, perf_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize performance data
        
        Args:
            perf_data: Raw performance data
            
        Returns:
            Anonymized performance data
        """
        try:
            logger.debug("Anonymizing performance data")
            
            anonymized_perf = perf_data.copy()
            
            # Apply noise to performance metrics
            performance_fields = [
                'avg_response_time', 'throughput', 'error_rate', 'uptime',
                'cache_hit_rate'
            ]
            
            for field in performance_fields:
                if field in anonymized_perf and isinstance(anonymized_perf[field], (int, float)):
                    if self.config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
                        anonymized_perf[field] = self._add_differential_privacy_noise(
                            anonymized_perf[field]
                        )
                    elif self.config.privacy_level == PrivacyLevel.HIGH:
                        # Round to reduce precision
                        anonymized_perf[field] = round(anonymized_perf[field], 2)
            
            # Anonymize nested performance data
            if 'database_performance' in anonymized_perf:
                anonymized_perf['database_performance'] = await self.anonymize_performance_data(
                    anonymized_perf['database_performance']
                )
            
            if 'api_performance' in anonymized_perf:
                anonymized_perf['api_performance'] = await self.anonymize_performance_data(
                    anonymized_perf['api_performance']
                )
            
            # Update statistics
            self._update_stats('performance_data')
            
            logger.debug("Successfully anonymized performance data")
            return anonymized_perf
            
        except Exception as e:
            logger.error(f"Failed to anonymize performance data: {str(e)}")
            return {}
    
    async def anonymize_trend_data(self, trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize trend analysis data
        
        Args:
            trend_data: Raw trend data
            
        Returns:
            Anonymized trend data
        """
        try:
            logger.debug("Anonymizing trend data")
            
            anonymized_trend = trend_data.copy()
            
            # Anonymize date information
            if 'date' in anonymized_trend:
                anonymized_trend['date'] = self._generalize_timestamp(
                    anonymized_trend['date'],
                    self.config.privacy_level
                )
            
            # Apply noise to trend metrics
            trend_fields = [
                'analyses_count', 'completed_count', 'avg_processing_time',
                'avg_confidence', 'unique_videos'
            ]
            
            for field in trend_fields:
                if field in anonymized_trend and isinstance(anonymized_trend[field], (int, float)):
                    if self.config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
                        anonymized_trend[field] = self._add_differential_privacy_noise(
                            anonymized_trend[field]
                        )
                    elif self.config.privacy_level in [PrivacyLevel.HIGH, PrivacyLevel.MAXIMUM]:
                        anonymized_trend[field] = self._round_to_privacy_level(
                            anonymized_trend[field]
                        )
            
            # Update statistics
            self._update_stats('trend_data')
            
            logger.debug("Successfully anonymized trend data")
            return anonymized_trend
            
        except Exception as e:
            logger.error(f"Failed to anonymize trend data: {str(e)}")
            return {}
    
    async def anonymize_analytics_data(self, analytics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize comprehensive analytics data
        
        Args:
            analytics_data: Raw analytics data
            
        Returns:
            Anonymized analytics data
        """
        try:
            logger.debug("Anonymizing analytics data")
            
            anonymized_analytics = analytics_data.copy()
            
            # Anonymize user engagement metrics
            if 'user_engagement' in anonymized_analytics:
                anonymized_analytics['user_engagement'] = await self._anonymize_user_engagement(
                    anonymized_analytics['user_engagement']
                )
            
            # Anonymize detection performance
            if 'detection_performance' in anonymized_analytics:
                anonymized_analytics['detection_performance'] = await self.anonymize_performance_data(
                    anonymized_analytics['detection_performance']
                )
            
            # Anonymize system utilization
            if 'system_utilization' in anonymized_analytics:
                anonymized_analytics['system_utilization'] = await self.anonymize_performance_data(
                    anonymized_analytics['system_utilization']
                )
            
            # Add privacy compliance metadata
            anonymized_analytics['privacy_compliance'] = {
                'anonymization_method': self.config.method.value,
                'privacy_level': self.config.privacy_level.value,
                'anonymized_at': datetime.now(timezone.utc).isoformat(),
                'compliance_standard': 'GDPR'
            }
            
            # Update statistics
            self._update_stats('analytics_data')
            
            logger.info("Successfully anonymized analytics data")
            return anonymized_analytics
            
        except Exception as e:
            logger.error(f"Failed to anonymize analytics data: {str(e)}")
            return {
                'error': 'Anonymization failed',
                'privacy_compliance': {
                    'anonymization_method': self.config.method.value,
                    'privacy_level': self.config.privacy_level.value,
                    'anonymized_at': datetime.now(timezone.utc).isoformat(),
                    'compliance_standard': 'GDPR'
                }
            }
    
    async def apply_k_anonymity(self, data: List[Dict[str, Any]], k: int = None) -> List[Dict[str, Any]]:
        """
        Apply k-anonymity to a dataset
        
        Args:
            data: List of records to anonymize
            k: K value for k-anonymity (defaults to config value)
            
        Returns:
            K-anonymous dataset
        """
        try:
            k_value = k or self.config.k_value
            logger.debug(f"Applying k-anonymity with k={k_value}")
            
            if len(data) < k_value:
                logger.warning(f"Dataset size ({len(data)}) is less than k-value ({k_value})")
                return []
            
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(data)
            
            # Identify quasi-identifiers (columns that could identify individuals)
            quasi_identifiers = self._identify_quasi_identifiers(df.columns)
            
            if not quasi_identifiers:
                logger.warning("No quasi-identifiers found for k-anonymity")
                return data
            
            # Group by quasi-identifiers and filter groups with size >= k
            grouped = df.groupby(quasi_identifiers)
            k_anonymous_groups = []
            
            for name, group in grouped:
                if len(group) >= k_value:
                    k_anonymous_groups.append(group)
                else:
                    # Suppress groups that don't meet k-anonymity
                    logger.debug(f"Suppressing group with {len(group)} records (k={k_value})")
            
            if not k_anonymous_groups:
                logger.warning("No groups meet k-anonymity requirements")
                return []
            
            # Combine k-anonymous groups
            result_df = pd.concat(k_anonymous_groups, ignore_index=True)
            
            # Convert back to list of dictionaries
            result = result_df.to_dict('records')
            
            logger.info(f"Applied k-anonymity: {len(data)} -> {len(result)} records")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply k-anonymity: {str(e)}")
            return []
    
    def _pseudonymize_user_id(self, user_id: str) -> str:
        """Pseudonymize user ID using hashing"""
        salt = "secureai_salt_2024"  # In production, use a secure salt
        return hashlib.sha256(f"{user_id}{salt}".encode()).hexdigest()[:16]
    
    def _anonymize_filename(self, filename: str) -> str:
        """Anonymize filename while preserving extension"""
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            # Replace name with hash, keep extension
            return f"file_{hashlib.md5(name.encode()).hexdigest()[:8]}.{ext}"
        else:
            return f"file_{hashlib.md5(filename.encode()).hexdigest()[:8]}"
    
    def _anonymize_file_path(self, file_path: str) -> str:
        """Anonymize file path"""
        # Replace with generic path structure
        return "/anonymized/path/to/video"
    
    def _generalize_timestamp(self, timestamp: Union[str, datetime], privacy_level: PrivacyLevel) -> str:
        """Generalize timestamp based on privacy level"""
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return timestamp
        
        if privacy_level == PrivacyLevel.LOW:
            # Keep hour precision
            return timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        elif privacy_level == PrivacyLevel.MEDIUM:
            # Keep day precision
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif privacy_level == PrivacyLevel.HIGH:
            # Keep week precision (round to Monday)
            days_since_monday = timestamp.weekday()
            week_start = timestamp - timedelta(days=days_since_monday)
            return week_start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:  # MAXIMUM
            # Keep month precision
            return timestamp.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    def _anonymize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize metadata dictionary"""
        anonymized = {}
        
        for key, value in metadata.items():
            if key in ['user_ip', 'user_agent', 'session_id']:
                # Skip sensitive fields
                continue
            elif isinstance(value, str) and len(value) > 50:
                # Truncate long strings
                anonymized[key] = value[:50] + "..."
            elif isinstance(value, (dict, list)):
                # Recursively anonymize nested structures
                anonymized[key] = self._anonymize_metadata(value) if isinstance(value, dict) else value
            else:
                anonymized[key] = value
        
        return anonymized
    
    def _add_differential_privacy_noise(self, value: float) -> float:
        """Add differential privacy noise to a value"""
        # Laplace mechanism for differential privacy
        epsilon = self.config.epsilon
        sensitivity = 1.0  # Assuming sensitivity of 1
        
        noise = np.random.laplace(0, sensitivity / epsilon)
        return value + noise
    
    def _round_to_privacy_level(self, value: Union[int, float]) -> Union[int, float]:
        """Round value based on privacy level"""
        if self.config.privacy_level == PrivacyLevel.HIGH:
            if isinstance(value, int):
                return round(value, -1)  # Round to nearest 10
            else:
                return round(value, 1)   # Round to 1 decimal place
        elif self.config.privacy_level == PrivacyLevel.MAXIMUM:
            if isinstance(value, int):
                return round(value, -2)  # Round to nearest 100
            else:
                return round(value, 0)   # Round to integer
        
        return value
    
    def _generate_anonymous_id(self) -> str:
        """Generate anonymous ID"""
        return f"anon_{uuid.uuid4().hex[:12]}"
    
    def _identify_quasi_identifiers(self, columns: List[str]) -> List[str]:
        """Identify quasi-identifier columns"""
        quasi_identifiers = []
        
        # Common quasi-identifiers in analytics data
        qi_patterns = [
            'created_at', 'timestamp', 'date', 'time',
            'location', 'region', 'country', 'city',
            'age', 'gender', 'occupation'
        ]
        
        for col in columns:
            if any(pattern in col.lower() for pattern in qi_patterns):
                quasi_identifiers.append(col)
        
        return quasi_identifiers
    
    async def _anonymize_user_engagement(self, engagement_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize user engagement data"""
        anonymized = engagement_data.copy()
        
        # Apply noise to user counts
        if 'active_users' in anonymized:
            anonymized['active_users'] = self._round_to_privacy_level(anonymized['active_users'])
        
        if 'new_users' in anonymized:
            anonymized['new_users'] = self._round_to_privacy_level(anonymized['new_users'])
        
        # Anonymize percentages
        percentage_fields = [
            'user_retention_rate', 'avg_session_duration', 'user_satisfaction_score'
        ]
        
        for field in percentage_fields:
            if field in anonymized and isinstance(anonymized[field], (int, float)):
                anonymized[field] = round(anonymized[field], 1)
        
        return anonymized
    
    def _update_stats(self, data_type: str) -> None:
        """Update anonymization statistics"""
        self.stats['total_anonymizations'] += 1
        self.stats['total_records_processed'] += 1
        
        # Track methods used
        method = self.config.method.value
        self.stats['methods_used'][method] = self.stats['methods_used'].get(method, 0) + 1
        
        # Track privacy levels used
        level = self.config.privacy_level.value
        self.stats['privacy_levels_used'][level] = self.stats['privacy_levels_used'].get(level, 0) + 1
    
    def get_anonymization_stats(self) -> Dict[str, Any]:
        """Get anonymization statistics"""
        return {
            **self.stats,
            'current_config': {
                'method': self.config.method.value,
                'privacy_level': self.config.privacy_level.value,
                'k_value': self.config.k_value,
                'epsilon': self.config.epsilon
            }
        }
    
    async def validate_privacy_compliance(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data meets privacy compliance requirements
        
        Args:
            data: Data to validate
            
        Returns:
            True if compliant, False otherwise
        """
        try:
            # Check for direct identifiers
            direct_identifiers = ['email', 'phone', 'ssn', 'credit_card']
            for identifier in direct_identifiers:
                if any(identifier in str(key).lower() for key in data.keys()):
                    logger.warning(f"Direct identifier found: {identifier}")
                    return False
            
            # Check for quasi-identifiers that might need generalization
            quasi_identifiers = ['timestamp', 'created_at', 'user_id']
            for qi in quasi_identifiers:
                if qi in data and not self._is_generalized(data[qi]):
                    logger.warning(f"Quasi-identifier not generalized: {qi}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating privacy compliance: {str(e)}")
            return False
    
    def _is_generalized(self, value: Any) -> bool:
        """Check if a value is generalized (simplified check)"""
        if isinstance(value, str) and 'T' in value:
            # Check if timestamp is generalized (no seconds/microseconds)
            return ':00.000' not in value and ':00Z' not in value
        
        return True  # Assume other values are generalized
