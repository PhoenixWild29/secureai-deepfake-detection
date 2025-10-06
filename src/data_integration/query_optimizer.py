"""
Query Optimizer
Helper functions and classes to construct optimized PostgreSQL queries
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import (
    text, select, func, and_, or_, desc, asc, case,
    distinct, literal_column, between
)
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select

from ..models.core_detection import Video, Analysis, DetectionResult, FrameAnalysis
from ..data_integration.dashboard_data_service import DashboardQueryParams

logger = logging.getLogger(__name__)


class QueryOptimizationError(Exception):
    """Custom exception for query optimization errors"""
    pass


@dataclass
class QueryPerformanceMetrics:
    """Metrics for query performance tracking"""
    execution_time: float
    rows_returned: int
    indexes_used: List[str]
    query_complexity: str


class IndexStrategy(Enum):
    """Available indexing strategies"""
    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    COMPOSITE = "composite"
    PARTIAL = "partial"
    COVERING = "covering"


class QueryOptimizer:
    """
    Optimizes PostgreSQL queries for dashboard data retrieval
    Leverages existing indexes and foreign key relationships
    """
    
    def __init__(self):
        self.performance_metrics = []
        self.query_cache = {}
        
        # Define commonly used indexes (based on assumed schema)
        self.indexes = {
            "video_created_at": "idx_video_created_at",
            "video_user_id": "idx_video_user_id",
            "analysis_video_id": "idx_analysis_video_id",
            "analysis_status": "idx_analysis_status",
            "analysis_created_at": "idx_analysis_created_at",
            "detection_result_analysis_id": "idx_detection_result_analysis_id",
            "frame_analysis_analysis_id": "idx_frame_analysis_analysis_id",
            "composite_user_date": "idx_composite_user_date"
        }
    
    async def build_recent_analyses_query(
        self, 
        params: DashboardQueryParams
    ) -> Select:
        """
        Build optimized query for recent analyses
        
        Args:
            params: Query parameters
            
        Returns:
            Optimized SQLAlchemy Select query
        """
        try:
            # Base query with proper joins and index hints
            query = (
                select(
                    Analysis.id,
                    Analysis.status,
                    Analysis.created_at,
                    Analysis.completed_at,
                    Analysis.confidence_score,
                    Analysis.processing_time,
                    Video.id.label('video_id'),
                    Video.filename,
                    Video.file_size,
                    Video.duration,
                    DetectionResult.detection_type,
                    DetectionResult.confidence,
                    DetectionResult.is_deepfake
                )
                .select_from(
                    Analysis.__table__
                    .join(Video.__table__, Analysis.video_id == Video.id)
                    .outerjoin(DetectionResult.__table__, Analysis.id == DetectionResult.analysis_id)
                )
                .where(
                    and_(
                        Video.user_id == params.user_id,
                        Analysis.created_at >= params.start_date if params.start_date else True,
                        Analysis.created_at <= params.end_date if params.end_date else True,
                        Analysis.status == params.analysis_status if params.analysis_status else True
                    )
                )
                .order_by(desc(Analysis.created_at))
                .limit(params.limit)
                .offset(params.offset)
            )
            
            # Add index hints for optimization
            query = self._add_index_hints(query, [
                self.indexes["composite_user_date"],
                self.indexes["analysis_created_at"]
            ])
            
            logger.debug(f"Built recent analyses query for user {params.user_id}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build recent analyses query: {str(e)}")
            raise QueryOptimizationError(f"Recent analyses query build failed: {str(e)}")
    
    async def build_analysis_statistics_query(
        self, 
        params: DashboardQueryParams
    ) -> Select:
        """
        Build optimized query for analysis statistics
        
        Args:
            params: Query parameters
            
        Returns:
            Optimized SQLAlchemy Select query
        """
        try:
            # Use aggregation with proper grouping and indexes
            query = (
                select(
                    func.count(Analysis.id).label('total_analyses'),
                    func.count(
                        case(
                            (Analysis.status == 'completed', 1),
                            else_=None
                        )
                    ).label('completed_analyses'),
                    func.count(
                        case(
                            (Analysis.status == 'failed', 1),
                            else_=None
                        )
                    ).label('failed_analyses'),
                    func.count(
                        case(
                            (Analysis.status == 'processing', 1),
                            else_=None
                        )
                    ).label('processing_analyses'),
                    func.avg(Analysis.processing_time).label('avg_processing_time'),
                    func.avg(Analysis.confidence_score).label('avg_confidence'),
                    func.max(Analysis.created_at).label('last_analysis'),
                    func.sum(Video.file_size).label('total_file_size'),
                    func.count(distinct(Video.id)).label('unique_videos')
                )
                .select_from(
                    Analysis.__table__
                    .join(Video.__table__, Analysis.video_id == Video.id)
                )
                .where(
                    and_(
                        Video.user_id == params.user_id,
                        Analysis.created_at >= params.start_date if params.start_date else True,
                        Analysis.created_at <= params.end_date if params.end_date else True
                    )
                )
            )
            
            # Add index hints
            query = self._add_index_hints(query, [
                self.indexes["composite_user_date"],
                self.indexes["analysis_status"]
            ])
            
            logger.debug(f"Built analysis statistics query for user {params.user_id}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build analysis statistics query: {str(e)}")
            raise QueryOptimizationError(f"Analysis statistics query build failed: {str(e)}")
    
    async def build_detection_performance_query(
        self, 
        params: DashboardQueryParams
    ) -> Select:
        """
        Build optimized query for detection performance metrics
        
        Args:
            params: Query parameters
            
        Returns:
            Optimized SQLAlchemy Select query
        """
        try:
            query = (
                select(
                    func.count(DetectionResult.id).label('total_detections'),
                    func.count(
                        case(
                            (DetectionResult.is_deepfake == True, 1),
                            else_=None
                        )
                    ).label('deepfake_detections'),
                    func.count(
                        case(
                            (DetectionResult.is_deepfake == False, 1),
                            else_=None
                        )
                    ).label('authentic_detections'),
                    func.avg(DetectionResult.confidence).label('avg_detection_confidence'),
                    func.max(DetectionResult.confidence).label('max_confidence'),
                    func.min(DetectionResult.confidence).label('min_confidence'),
                    func.count(distinct(DetectionResult.detection_type)).label('detection_types_count'),
                    func.avg(
                        case(
                            (DetectionResult.is_deepfake == True, DetectionResult.confidence),
                            else_=None
                        )
                    ).label('avg_deepfake_confidence'),
                    func.avg(
                        case(
                            (DetectionResult.is_deepfake == False, DetectionResult.confidence),
                            else_=None
                        )
                    ).label('avg_authentic_confidence')
                )
                .select_from(
                    DetectionResult.__table__
                    .join(Analysis.__table__, DetectionResult.analysis_id == Analysis.id)
                    .join(Video.__table__, Analysis.video_id == Video.id)
                )
                .where(
                    and_(
                        Video.user_id == params.user_id,
                        DetectionResult.created_at >= params.start_date if params.start_date else True,
                        DetectionResult.created_at <= params.end_date if params.end_date else True
                    )
                )
            )
            
            # Add index hints
            query = self._add_index_hints(query, [
                self.indexes["detection_result_analysis_id"],
                self.indexes["composite_user_date"]
            ])
            
            logger.debug(f"Built detection performance query for user {params.user_id}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build detection performance query: {str(e)}")
            raise QueryOptimizationError(f"Detection performance query build failed: {str(e)}")
    
    async def build_trend_analysis_query(
        self, 
        params: DashboardQueryParams
    ) -> Select:
        """
        Build optimized query for trend analysis
        
        Args:
            params: Query parameters
            
        Returns:
            Optimized SQLAlchemy Select query
        """
        try:
            # Default to last 30 days if no date range specified
            start_date = params.start_date or (datetime.now() - timedelta(days=30))
            end_date = params.end_date or datetime.now()
            
            query = (
                select(
                    func.date_trunc('day', Analysis.created_at).label('date'),
                    func.count(Analysis.id).label('analyses_count'),
                    func.count(
                        case(
                            (Analysis.status == 'completed', 1),
                            else_=None
                        )
                    ).label('completed_count'),
                    func.avg(Analysis.processing_time).label('avg_processing_time'),
                    func.avg(Analysis.confidence_score).label('avg_confidence'),
                    func.count(distinct(Video.id)).label('unique_videos')
                )
                .select_from(
                    Analysis.__table__
                    .join(Video.__table__, Analysis.video_id == Video.id)
                )
                .where(
                    and_(
                        Video.user_id == params.user_id,
                        Analysis.created_at >= start_date,
                        Analysis.created_at <= end_date
                    )
                )
                .group_by(func.date_trunc('day', Analysis.created_at))
                .order_by(asc(func.date_trunc('day', Analysis.created_at)))
            )
            
            # Add index hints
            query = self._add_index_hints(query, [
                self.indexes["composite_user_date"],
                self.indexes["analysis_created_at"]
            ])
            
            logger.debug(f"Built trend analysis query for user {params.user_id}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build trend analysis query: {str(e)}")
            raise QueryOptimizationError(f"Trend analysis query build failed: {str(e)}")
    
    async def build_frame_analysis_query(
        self, 
        params: DashboardQueryParams,
        analysis_id: Optional[str] = None
    ) -> Select:
        """
        Build optimized query for frame analysis data
        
        Args:
            params: Query parameters
            analysis_id: Optional specific analysis ID
            
        Returns:
            Optimized SQLAlchemy Select query
        """
        try:
            query = (
                select(
                    FrameAnalysis.id,
                    FrameAnalysis.frame_number,
                    FrameAnalysis.timestamp,
                    FrameAnalysis.confidence,
                    FrameAnalysis.is_deepfake,
                    FrameAnalysis.detection_method,
                    FrameAnalysis.processing_time,
                    Analysis.id.label('analysis_id'),
                    Analysis.status.label('analysis_status')
                )
                .select_from(
                    FrameAnalysis.__table__
                    .join(Analysis.__table__, FrameAnalysis.analysis_id == Analysis.id)
                    .join(Video.__table__, Analysis.video_id == Video.id)
                )
                .where(
                    and_(
                        Video.user_id == params.user_id,
                        FrameAnalysis.analysis_id == analysis_id if analysis_id else True,
                        FrameAnalysis.created_at >= params.start_date if params.start_date else True,
                        FrameAnalysis.created_at <= params.end_date if params.end_date else True
                    )
                )
                .order_by(asc(FrameAnalysis.frame_number))
            )
            
            # Add index hints
            query = self._add_index_hints(query, [
                self.indexes["frame_analysis_analysis_id"],
                self.indexes["composite_user_date"]
            ])
            
            logger.debug(f"Built frame analysis query for user {params.user_id}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build frame analysis query: {str(e)}")
            raise QueryOptimizationError(f"Frame analysis query build failed: {str(e)}")
    
    async def build_video_metadata_query(
        self, 
        params: DashboardQueryParams
    ) -> Select:
        """
        Build optimized query for video metadata
        
        Args:
            params: Query parameters
            
        Returns:
            Optimized SQLAlchemy Select query
        """
        try:
            query = (
                select(
                    Video.id,
                    Video.filename,
                    Video.file_size,
                    Video.duration,
                    Video.resolution,
                    Video.codec,
                    Video.created_at,
                    Video.upload_status,
                    func.count(Analysis.id).label('analysis_count'),
                    func.max(Analysis.created_at).label('last_analysis'),
                    func.avg(Analysis.confidence_score).label('avg_confidence')
                )
                .select_from(
                    Video.__table__
                    .outerjoin(Analysis.__table__, Video.id == Analysis.video_id)
                )
                .where(
                    and_(
                        Video.user_id == params.user_id,
                        Video.created_at >= params.start_date if params.start_date else True,
                        Video.created_at <= params.end_date if params.end_date else True,
                        Video.video_type == params.video_type if params.video_type else True
                    )
                )
                .group_by(Video.id)
                .order_by(desc(Video.created_at))
                .limit(params.limit)
                .offset(params.offset)
            )
            
            # Add index hints
            query = self._add_index_hints(query, [
                self.indexes["video_user_id"],
                self.indexes["video_created_at"]
            ])
            
            logger.debug(f"Built video metadata query for user {params.user_id}")
            return query
            
        except Exception as e:
            logger.error(f"Failed to build video metadata query: {str(e)}")
            raise QueryOptimizationError(f"Video metadata query build failed: {str(e)}")
    
    def _add_index_hints(self, query: Select, indexes: List[str]) -> Select:
        """
        Add index hints to query (PostgreSQL specific)
        
        Args:
            query: SQLAlchemy Select query
            indexes: List of index names to hint
            
        Returns:
            Query with index hints
        """
        try:
            # For PostgreSQL, we can add index hints using comments
            # This is a simplified approach - in practice, you might use
            # more sophisticated query planning
            
            index_hint = f"/*+ USE_INDEX({','.join(indexes)}) */"
            
            # Add as a comment to the query
            query = query.prefix_with(text(index_hint))
            
            return query
            
        except Exception as e:
            logger.warning(f"Failed to add index hints: {str(e)}")
            return query
    
    def optimize_query_for_performance(self, query: Select) -> Select:
        """
        Apply general performance optimizations to a query
        
        Args:
            query: SQLAlchemy Select query
            
        Returns:
            Optimized query
        """
        try:
            # Add query optimization hints
            optimized_query = query
            
            # Limit result set if not already limited
            if not hasattr(query, '_limit') or query._limit is None:
                optimized_query = optimized_query.limit(1000)  # Default limit
            
            # Add query timeout hint
            optimized_query = optimized_query.prefix_with(
                text("/*+ MAX_EXECUTION_TIME(30000) */")  # 30 second timeout
            )
            
            return optimized_query
            
        except Exception as e:
            logger.warning(f"Failed to optimize query: {str(e)}")
            return query
    
    def analyze_query_performance(self, query: Select) -> QueryPerformanceMetrics:
        """
        Analyze query performance characteristics
        
        Args:
            query: SQLAlchemy Select query
            
        Returns:
            QueryPerformanceMetrics object
        """
        try:
            # This is a simplified analysis - in practice, you would
            # execute EXPLAIN ANALYZE and parse the results
            
            complexity = "simple"
            
            # Analyze query complexity based on joins and subqueries
            query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
            
            join_count = query_str.upper().count('JOIN')
            subquery_count = query_str.upper().count('SELECT') - 1
            
            if join_count > 3 or subquery_count > 2:
                complexity = "complex"
            elif join_count > 1 or subquery_count > 0:
                complexity = "moderate"
            
            return QueryPerformanceMetrics(
                execution_time=0.0,  # Would be measured during execution
                rows_returned=0,     # Would be counted during execution
                indexes_used=[],    # Would be determined from EXPLAIN
                query_complexity=complexity
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze query performance: {str(e)}")
            return QueryPerformanceMetrics(
                execution_time=0.0,
                rows_returned=0,
                indexes_used=[],
                query_complexity="unknown"
            )
    
    def get_recommended_indexes(self, query: Select) -> List[str]:
        """
        Get recommended indexes for a query
        
        Args:
            query: SQLAlchemy Select query
            
        Returns:
            List of recommended index names
        """
        try:
            recommendations = []
            
            # Analyze WHERE clauses for index recommendations
            query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
            
            # Simple pattern matching for common index needs
            if 'user_id' in query_str and 'created_at' in query_str:
                recommendations.append(self.indexes["composite_user_date"])
            
            if 'video_id' in query_str:
                recommendations.append(self.indexes["video_user_id"])
            
            if 'analysis_id' in query_str:
                recommendations.append(self.indexes["analysis_video_id"])
            
            if 'status' in query_str:
                recommendations.append(self.indexes["analysis_status"])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get index recommendations: {str(e)}")
            return []
    
    async def execute_optimized_query(
        self, 
        query: Select, 
        session
    ) -> Any:
        """
        Execute query with performance monitoring
        
        Args:
            query: SQLAlchemy Select query
            session: Database session
            
        Returns:
            Query result
        """
        try:
            import time
            start_time = time.time()
            
            # Execute the query
            result = await session.execute(query)
            
            execution_time = time.time() - start_time
            
            # Record performance metrics
            metrics = QueryPerformanceMetrics(
                execution_time=execution_time,
                rows_returned=result.rowcount if hasattr(result, 'rowcount') else 0,
                indexes_used=self.get_recommended_indexes(query),
                query_complexity=self.analyze_query_performance(query).query_complexity
            )
            
            self.performance_metrics.append(metrics)
            
            logger.debug(f"Query executed in {execution_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute optimized query: {str(e)}")
            raise QueryOptimizationError(f"Query execution failed: {str(e)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get summary of query performance metrics
        
        Returns:
            Dictionary with performance summary
        """
        if not self.performance_metrics:
            return {"message": "No performance metrics available"}
        
        total_queries = len(self.performance_metrics)
        avg_execution_time = sum(m.execution_time for m in self.performance_metrics) / total_queries
        total_rows = sum(m.rows_returned for m in self.performance_metrics)
        
        complexity_distribution = {}
        for metrics in self.performance_metrics:
            complexity = metrics.query_complexity
            complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
        
        return {
            "total_queries": total_queries,
            "average_execution_time": avg_execution_time,
            "total_rows_returned": total_rows,
            "complexity_distribution": complexity_distribution,
            "recommended_indexes": list(set(
                idx for metrics in self.performance_metrics 
                for idx in metrics.indexes_used
            ))
        }
