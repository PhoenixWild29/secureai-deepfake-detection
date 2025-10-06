#!/usr/bin/env python3
"""
PostgreSQL Database Client
Utility module for database operations including storing detection results and performance metrics
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    PostgreSQL database client for storing detection results and performance metrics.
    Supports both synchronous and asynchronous operations.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ):
        """
        Initialize database client.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Connection pool size
            max_overflow: Maximum pool overflow
            pool_timeout: Pool timeout in seconds
            pool_recycle: Pool recycle time in seconds
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        
        # Connection pools
        self._sync_pool = None
        self._async_engine = None
        self._async_session_factory = None
        
        # Table names
        self.ANALYSES_TABLE = 'analyses'
        self.DETECTION_RESULTS_TABLE = 'detection_results'
        self.FRAME_ANALYSIS_TABLE = 'frame_analysis'
        self.PERFORMANCE_METRICS_TABLE = 'performance_metrics'
        self.SUSPICIOUS_REGIONS_TABLE = 'suspicious_regions'
    
    def _get_sync_pool(self) -> ThreadedConnectionPool:
        """Get synchronous connection pool."""
        if self._sync_pool is None:
            self._sync_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size,
                dsn=self.database_url,
                cursor_factory=RealDictCursor
            )
        return self._sync_pool
    
    def _get_async_engine(self):
        """Get asynchronous SQLAlchemy engine."""
        if self._async_engine is None:
            # Convert postgresql:// to postgresql+asyncpg://
            async_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            
            self._async_engine = create_async_engine(
                async_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_timeout=self.pool_timeout,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,
                echo=False
            )
            
            self._async_session_factory = sessionmaker(
                self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        
        return self._async_engine, self._async_session_factory
    
    # Analysis Management
    
    def create_analysis_record(
        self,
        analysis_id: str,
        video_path: str,
        filename: str,
        file_size: int,
        status: str = 'pending',
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create analysis record in database.
        
        Args:
            analysis_id: Analysis ID
            video_path: Path to video file
            filename: Video filename
            file_size: File size in bytes
            status: Analysis status
            config: Analysis configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO analyses (
                            analysis_id, video_path, filename, file_size,
                            status, config, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (analysis_id) DO UPDATE SET
                            status = EXCLUDED.status,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        analysis_id,
                        video_path,
                        filename,
                        file_size,
                        status,
                        json.dumps(config) if config else None,
                        datetime.now(timezone.utc),
                        datetime.now(timezone.utc)
                    ))
                    
                    conn.commit()
                    logger.info(f"Created analysis record: {analysis_id}")
                    return True
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error creating analysis record: {str(e)}")
            return False
    
    async def create_analysis_record_async(
        self,
        analysis_id: str,
        video_path: str,
        filename: str,
        file_size: int,
        status: str = 'pending',
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create analysis record in database (async).
        
        Args:
            analysis_id: Analysis ID
            video_path: Path to video file
            filename: Video filename
            file_size: File size in bytes
            status: Analysis status
            config: Analysis configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            engine, session_factory = self._get_async_engine()
            
            async with session_factory() as session:
                await session.execute(sa.text("""
                    INSERT INTO analyses (
                        analysis_id, video_path, filename, file_size,
                        status, config, created_at, updated_at
                    ) VALUES (
                        :analysis_id, :video_path, :filename, :file_size,
                        :status, :config, :created_at, :updated_at
                    )
                    ON CONFLICT (analysis_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
                """), {
                    'analysis_id': analysis_id,
                    'video_path': video_path,
                    'filename': filename,
                    'file_size': file_size,
                    'status': status,
                    'config': json.dumps(config) if config else None,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                })
                
                await session.commit()
                logger.info(f"Created analysis record: {analysis_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating analysis record: {str(e)}")
            return False
    
    def update_analysis_status(
        self,
        analysis_id: str,
        status: str,
        error_message: Optional[str] = None,
        progress_percentage: Optional[float] = None
    ) -> bool:
        """
        Update analysis status.
        
        Args:
            analysis_id: Analysis ID
            status: New status
            error_message: Error message if failed
            progress_percentage: Progress percentage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Build update query dynamically
                    update_fields = ['status = %s', 'updated_at = %s']
                    update_values = [status, datetime.now(timezone.utc)]
                    
                    if error_message:
                        update_fields.append('error_message = %s')
                        update_values.append(error_message)
                    
                    if progress_percentage is not None:
                        update_fields.append('progress_percentage = %s')
                        update_values.append(progress_percentage)
                    
                    update_values.append(analysis_id)
                    
                    query = f"""
                        UPDATE analyses 
                        SET {', '.join(update_fields)}
                        WHERE analysis_id = %s
                    """
                    
                    cursor.execute(query, update_values)
                    conn.commit()
                    
                    logger.info(f"Updated analysis status: {analysis_id} -> {status}")
                    return True
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error updating analysis status: {str(e)}")
            return False
    
    def get_analysis_record(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analysis record.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Analysis record or None if not found
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM analyses WHERE analysis_id = %s
                    """, (analysis_id,))
                    
                    result = cursor.fetchone()
                    if result:
                        # Convert to dict and parse JSON fields
                        record = dict(result)
                        if record.get('config'):
                            record['config'] = json.loads(record['config'])
                        return record
                    return None
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting analysis record: {str(e)}")
            return None
    
    # Detection Results Storage
    
    def store_detection_result(
        self,
        analysis_id: str,
        overall_confidence: float,
        detection_summary: Dict[str, Any],
        processing_time_seconds: float,
        detection_methods_used: List[str],
        blockchain_hash: Optional[str] = None
    ) -> bool:
        """
        Store detection result.
        
        Args:
            analysis_id: Analysis ID
            overall_confidence: Overall confidence score
            detection_summary: Detection summary data
            processing_time_seconds: Processing time in seconds
            detection_methods_used: List of detection methods used
            blockchain_hash: Blockchain verification hash
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO detection_results (
                            analysis_id, overall_confidence, detection_summary,
                            processing_time_seconds, detection_methods_used,
                            blockchain_hash, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (analysis_id) DO UPDATE SET
                            overall_confidence = EXCLUDED.overall_confidence,
                            detection_summary = EXCLUDED.detection_summary,
                            processing_time_seconds = EXCLUDED.processing_time_seconds,
                            detection_methods_used = EXCLUDED.detection_methods_used,
                            blockchain_hash = EXCLUDED.blockchain_hash,
                            created_at = EXCLUDED.created_at
                    """, (
                        analysis_id,
                        overall_confidence,
                        json.dumps(detection_summary),
                        processing_time_seconds,
                        json.dumps(detection_methods_used),
                        blockchain_hash,
                        datetime.now(timezone.utc)
                    ))
                    
                    conn.commit()
                    logger.info(f"Stored detection result: {analysis_id}")
                    return True
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error storing detection result: {str(e)}")
            return False
    
    def store_frame_analysis(
        self,
        analysis_id: str,
        frame_analyses: List[Dict[str, Any]]
    ) -> bool:
        """
        Store frame analysis data.
        
        Args:
            analysis_id: Analysis ID
            frame_analyses: List of frame analysis data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Clear existing frame analyses for this analysis
                    cursor.execute("""
                        DELETE FROM frame_analysis WHERE analysis_id = %s
                    """, (analysis_id,))
                    
                    # Insert new frame analyses
                    for frame_data in frame_analyses:
                        cursor.execute("""
                            INSERT INTO frame_analysis (
                                analysis_id, frame_number, timestamp,
                                confidence_score, suspicious_regions,
                                detection_methods, processing_time_ms
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            analysis_id,
                            frame_data.get('frame_number'),
                            frame_data.get('timestamp'),
                            frame_data.get('confidence_score'),
                            json.dumps(frame_data.get('suspicious_regions', [])),
                            json.dumps(frame_data.get('detection_methods', [])),
                            frame_data.get('processing_time_ms')
                        ))
                    
                    conn.commit()
                    logger.info(f"Stored {len(frame_analyses)} frame analyses: {analysis_id}")
                    return True
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error storing frame analysis: {str(e)}")
            return False
    
    def store_suspicious_regions(
        self,
        analysis_id: str,
        suspicious_regions: List[Dict[str, Any]]
    ) -> bool:
        """
        Store suspicious regions data.
        
        Args:
            analysis_id: Analysis ID
            suspicious_regions: List of suspicious region data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Clear existing suspicious regions for this analysis
                    cursor.execute("""
                        DELETE FROM suspicious_regions WHERE analysis_id = %s
                    """, (analysis_id,))
                    
                    # Insert new suspicious regions
                    for region_data in suspicious_regions:
                        cursor.execute("""
                            INSERT INTO suspicious_regions (
                                analysis_id, region_id, frame_number,
                                bounding_box, confidence_score,
                                detection_method, anomaly_type, severity
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            analysis_id,
                            region_data.get('region_id'),
                            region_data.get('frame_number'),
                            json.dumps(region_data.get('bounding_box', {})),
                            region_data.get('confidence_score'),
                            region_data.get('detection_method'),
                            region_data.get('anomaly_type'),
                            region_data.get('severity')
                        ))
                    
                    conn.commit()
                    logger.info(f"Stored {len(suspicious_regions)} suspicious regions: {analysis_id}")
                    return True
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error storing suspicious regions: {str(e)}")
            return False
    
    # Performance Metrics
    
    def store_performance_metrics(
        self,
        analysis_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Store performance metrics.
        
        Args:
            analysis_id: Analysis ID
            metrics: Performance metrics data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO performance_metrics (
                            analysis_id, metrics_data, created_at
                        ) VALUES (
                            %s, %s, %s
                        )
                        ON CONFLICT (analysis_id) DO UPDATE SET
                            metrics_data = EXCLUDED.metrics_data,
                            created_at = EXCLUDED.created_at
                    """, (
                        analysis_id,
                        json.dumps(metrics),
                        datetime.now(timezone.utc)
                    ))
                    
                    conn.commit()
                    logger.info(f"Stored performance metrics: {analysis_id}")
                    return True
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error storing performance metrics: {str(e)}")
            return False
    
    def get_performance_metrics(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Performance metrics or None if not found
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT metrics_data FROM performance_metrics 
                        WHERE analysis_id = %s
                    """, (analysis_id,))
                    
                    result = cursor.fetchone()
                    if result:
                        return json.loads(result['metrics_data'])
                    return None
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return None
    
    # Result Retrieval
    
    def get_complete_analysis_result(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete analysis result including all related data.
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Complete analysis result or None if not found
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Get analysis record
                    cursor.execute("""
                        SELECT * FROM analyses WHERE analysis_id = %s
                    """, (analysis_id,))
                    analysis_record = cursor.fetchone()
                    
                    if not analysis_record:
                        return None
                    
                    # Get detection result
                    cursor.execute("""
                        SELECT * FROM detection_results WHERE analysis_id = %s
                    """, (analysis_id,))
                    detection_result = cursor.fetchone()
                    
                    # Get frame analyses
                    cursor.execute("""
                        SELECT * FROM frame_analysis WHERE analysis_id = %s
                        ORDER BY frame_number
                    """, (analysis_id,))
                    frame_analyses = cursor.fetchall()
                    
                    # Get suspicious regions
                    cursor.execute("""
                        SELECT * FROM suspicious_regions WHERE analysis_id = %s
                        ORDER BY frame_number, confidence_score DESC
                    """, (analysis_id,))
                    suspicious_regions = cursor.fetchall()
                    
                    # Get performance metrics
                    cursor.execute("""
                        SELECT metrics_data FROM performance_metrics WHERE analysis_id = %s
                    """, (analysis_id,))
                    metrics_result = cursor.fetchone()
                    
                    # Build complete result
                    result = dict(analysis_record)
                    
                    if result.get('config'):
                        result['config'] = json.loads(result['config'])
                    
                    if detection_result:
                        result['detection_result'] = dict(detection_result)
                        if result['detection_result'].get('detection_summary'):
                            result['detection_result']['detection_summary'] = json.loads(
                                result['detection_result']['detection_summary']
                            )
                        if result['detection_result'].get('detection_methods_used'):
                            result['detection_result']['detection_methods_used'] = json.loads(
                                result['detection_result']['detection_methods_used']
                            )
                    
                    result['frame_analyses'] = []
                    for frame_data in frame_analyses:
                        frame_dict = dict(frame_data)
                        if frame_dict.get('suspicious_regions'):
                            frame_dict['suspicious_regions'] = json.loads(frame_dict['suspicious_regions'])
                        if frame_dict.get('detection_methods'):
                            frame_dict['detection_methods'] = json.loads(frame_dict['detection_methods'])
                        result['frame_analyses'].append(frame_dict)
                    
                    result['suspicious_regions'] = []
                    for region_data in suspicious_regions:
                        region_dict = dict(region_data)
                        if region_dict.get('bounding_box'):
                            region_dict['bounding_box'] = json.loads(region_dict['bounding_box'])
                        result['suspicious_regions'].append(region_dict)
                    
                    if metrics_result:
                        result['performance_metrics'] = json.loads(metrics_result['metrics_data'])
                    
                    return result
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting complete analysis result: {str(e)}")
            return None
    
    # Health Check
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check database connection health.
        
        Returns:
            Health status information
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            'status': 'healthy',
                            'database_url': self.database_url,
                            'pool_size': self.pool_size,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                    else:
                        return {
                            'status': 'unhealthy',
                            'error': 'Database query failed',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    # Cleanup
    
    def cleanup_old_records(self, days_old: int = 30) -> int:
        """
        Clean up old analysis records.
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            Number of records cleaned up
        """
        try:
            pool = self._get_sync_pool()
            conn = pool.getconn()
            
            try:
                with conn.cursor() as cursor:
                    # Delete old analyses and related records
                    cursor.execute("""
                        DELETE FROM analyses 
                        WHERE created_at < NOW() - INTERVAL '%s days'
                    """, (days_old,))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    logger.info(f"Cleaned up {deleted_count} old analysis records")
                    return deleted_count
                    
            finally:
                pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error cleaning up old records: {str(e)}")
            return 0


# Global database client instance
db_client = DatabaseClient(
    database_url=os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/deepfake_detection')
)


# Utility functions for easy access
def create_analysis_record(
    analysis_id: str,
    video_path: str,
    filename: str,
    file_size: int,
    status: str = 'pending',
    config: Optional[Dict[str, Any]] = None
) -> bool:
    """Create analysis record in database."""
    return db_client.create_analysis_record(analysis_id, video_path, filename, file_size, status, config)


def update_analysis_status(
    analysis_id: str,
    status: str,
    error_message: Optional[str] = None,
    progress_percentage: Optional[float] = None
) -> bool:
    """Update analysis status."""
    return db_client.update_analysis_status(analysis_id, status, error_message, progress_percentage)


def store_detection_result(
    analysis_id: str,
    overall_confidence: float,
    detection_summary: Dict[str, Any],
    processing_time_seconds: float,
    detection_methods_used: List[str],
    blockchain_hash: Optional[str] = None
) -> bool:
    """Store detection result."""
    return db_client.store_detection_result(
        analysis_id, overall_confidence, detection_summary,
        processing_time_seconds, detection_methods_used, blockchain_hash
    )


def store_frame_analysis(analysis_id: str, frame_analyses: List[Dict[str, Any]]) -> bool:
    """Store frame analysis data."""
    return db_client.store_frame_analysis(analysis_id, frame_analyses)


def store_suspicious_regions(analysis_id: str, suspicious_regions: List[Dict[str, Any]]) -> bool:
    """Store suspicious regions data."""
    return db_client.store_suspicious_regions(analysis_id, suspicious_regions)


def store_performance_metrics(analysis_id: str, metrics: Dict[str, Any]) -> bool:
    """Store performance metrics."""
    return db_client.store_performance_metrics(analysis_id, metrics)


def get_complete_analysis_result(analysis_id: str) -> Optional[Dict[str, Any]]:
    """Get complete analysis result."""
    return db_client.get_complete_analysis_result(analysis_id)


# Export
__all__ = [
    'DatabaseClient',
    'db_client',
    'create_analysis_record',
    'update_analysis_status',
    'store_detection_result',
    'store_frame_analysis',
    'store_suspicious_regions',
    'store_performance_metrics',
    'get_complete_analysis_result'
]
