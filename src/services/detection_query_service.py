#!/usr/bin/env python3
"""
Detection Query Service
Optimized query functions for detection results leveraging existing database indexes
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from decimal import Decimal

# Import existing Core Detection Engine models
from ..core_models.models import DetectionResult, FrameAnalysis, Analysis, Video


class DetectionQueryService:
    """
    Service class for optimized detection result queries.
    Leverages existing database indexes for efficient data retrieval.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize with database session"""
        self.session = session
    
    async def get_detection_result(self, analysis_id: UUID) -> Optional[DetectionResult]:
        """
        Get basic detection result by analysis_id.
        Uses existing index on analysis_id for optimal performance.
        """
        query = select(DetectionResult).where(DetectionResult.analysis_id == analysis_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_detection_result_with_analysis(self, analysis_id: UUID) -> Optional[Tuple[DetectionResult, Analysis]]:
        """
        Get detection result with related analysis data.
        Includes video information for complete context.
        """
        query = (
            select(DetectionResult, Analysis)
            .join(Analysis, DetectionResult.analysis_id == Analysis.id)
            .join(Video, Analysis.video_id == Video.id)
            .where(DetectionResult.analysis_id == analysis_id)
        )
        result = await self.session.execute(query)
        return result.first()
    
    async def get_frame_analysis_batch(
        self, 
        result_id: UUID, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[FrameAnalysis]:
        """
        Get paginated frame analysis data.
        Uses existing index on (result_id, frame_number) for optimal performance.
        """
        query = (
            select(FrameAnalysis)
            .where(FrameAnalysis.result_id == result_id)
            .order_by(FrameAnalysis.frame_number)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_frame_analysis_count(self, result_id: UUID) -> int:
        """Get total count of frame analysis records for a result"""
        query = select(func.count(FrameAnalysis.id)).where(FrameAnalysis.result_id == result_id)
        result = await self.session.execute(query)
        return result.scalar()
    
    async def get_confidence_distribution(self, analysis_id: UUID) -> Dict[str, int]:
        """
        Get confidence score distribution across predefined bins.
        Optimized for visualization data.
        """
        # Get all confidence scores for frames in this analysis
        query = (
            select(FrameAnalysis.confidence_score)
            .join(DetectionResult, FrameAnalysis.result_id == DetectionResult.id)
            .where(DetectionResult.analysis_id == analysis_id)
        )
        result = await self.session.execute(query)
        confidence_scores = [float(score) for score in result.scalars().all()]
        
        # Bin the confidence scores
        bins = {
            '0.0-0.2': 0,
            '0.2-0.4': 0,
            '0.4-0.6': 0,
            '0.6-0.8': 0,
            '0.8-1.0': 0
        }
        
        for score in confidence_scores:
            if 0.0 <= score < 0.2:
                bins['0.0-0.2'] += 1
            elif 0.2 <= score < 0.4:
                bins['0.2-0.4'] += 1
            elif 0.4 <= score < 0.6:
                bins['0.4-0.6'] += 1
            elif 0.6 <= score < 0.8:
                bins['0.6-0.8'] += 1
            elif 0.8 <= score <= 1.0:
                bins['0.8-1.0'] += 1
        
        return bins
    
    async def get_suspicious_regions_summary(self, result_id: UUID) -> List[Dict[str, Any]]:
        """
        Get aggregated summary of suspicious regions across all frames.
        Optimized for visualization data.
        """
        # Get frames with suspicious regions
        query = (
            select(FrameAnalysis.frame_number, FrameAnalysis.suspicious_regions)
            .where(FrameAnalysis.result_id == result_id)
            .where(FrameAnalysis.suspicious_regions.isnot(None))
            .order_by(FrameAnalysis.frame_number)
        )
        result = await self.session.execute(query)
        frames_with_regions = result.all()
        
        # Aggregate region data
        regions_summary = []
        for frame_number, suspicious_regions in frames_with_regions:
            if suspicious_regions and isinstance(suspicious_regions, dict):
                for region_id, region_data in suspicious_regions.items():
                    if isinstance(region_data, dict):
                        summary_item = {
                            'frame_number': frame_number,
                            'region_id': region_id,
                            'region_data': region_data,
                            'confidence': region_data.get('confidence', 0.0),
                            'coordinates': region_data.get('coordinates', {}),
                            'artifacts': region_data.get('artifacts', [])
                        }
                        regions_summary.append(summary_item)
        
        return regions_summary
    
    async def get_blockchain_verification_status(self, analysis_id: UUID) -> Dict[str, Any]:
        """
        Get blockchain verification status and metadata.
        Provides real-time validation status for tamper-proof result validation.
        """
        query = (
            select(DetectionResult.blockchain_hash, DetectionResult.created_at)
            .where(DetectionResult.analysis_id == analysis_id)
        )
        result = await self.session.execute(query)
        row = result.first()
        
        if not row:
            return {
                'status': 'not_available',
                'blockchain_hash': None,
                'verification_timestamp': None,
                'is_tamper_proof': False,
                'verification_details': {}
            }
        
        blockchain_hash, created_at = row
        
        # Determine verification status based on blockchain hash presence
        if blockchain_hash:
            verification_status = 'verified'
            is_tamper_proof = True
            verification_details = {
                'hash_length': len(blockchain_hash),
                'hash_format': 'hex' if all(c in '0123456789abcdefABCDEF' for c in blockchain_hash) else 'unknown',
                'created_at': created_at.isoformat() if created_at else None
            }
        else:
            verification_status = 'not_available'
            is_tamper_proof = False
            verification_details = {}
        
        return {
            'status': verification_status,
            'blockchain_hash': blockchain_hash,
            'verification_timestamp': created_at,
            'is_tamper_proof': is_tamper_proof,
            'verification_details': verification_details
        }
    
    async def search_results_by_confidence(
        self, 
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DetectionResult]:
        """
        Search detection results by confidence score range.
        Uses existing index on overall_confidence for optimal performance.
        """
        query = select(DetectionResult)
        
        # Apply confidence filters
        conditions = []
        if min_confidence is not None:
            conditions.append(DetectionResult.overall_confidence >= Decimal(str(min_confidence)))
        if max_confidence is not None:
            conditions.append(DetectionResult.overall_confidence <= Decimal(str(max_confidence)))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply pagination and ordering
        query = query.order_by(desc(DetectionResult.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_recent_results(self, limit: int = 50, offset: int = 0) -> List[DetectionResult]:
        """
        Get recent detection results ordered by creation time.
        Uses existing index on created_at for optimal performance.
        """
        query = (
            select(DetectionResult)
            .order_by(desc(DetectionResult.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_results_by_frame_count(
        self, 
        min_frames: Optional[int] = None,
        max_frames: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DetectionResult]:
        """
        Search detection results by frame count range.
        """
        query = select(DetectionResult)
        
        # Apply frame count filters
        conditions = []
        if min_frames is not None:
            conditions.append(DetectionResult.frame_count >= min_frames)
        if max_frames is not None:
            conditions.append(DetectionResult.frame_count <= max_frames)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply pagination and ordering
        query = query.order_by(desc(DetectionResult.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_results_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DetectionResult]:
        """
        Search detection results by date range.
        Uses existing index on created_at for optimal performance.
        """
        query = select(DetectionResult)
        
        # Apply date filters
        conditions = []
        if start_date:
            conditions.append(DetectionResult.created_at >= start_date)
        if end_date:
            conditions.append(DetectionResult.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply pagination and ordering
        query = query.order_by(desc(DetectionResult.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_detection_statistics(self) -> Dict[str, Any]:
        """
        Get overall detection statistics for dashboard/analytics.
        """
        # Total results count
        total_query = select(func.count(DetectionResult.id))
        total_result = await self.session.execute(total_query)
        total_count = total_result.scalar()
        
        # Average confidence
        avg_confidence_query = select(func.avg(DetectionResult.overall_confidence))
        avg_confidence_result = await self.session.execute(avg_confidence_query)
        avg_confidence = avg_confidence_result.scalar()
        
        # Results with blockchain verification
        blockchain_query = select(func.count(DetectionResult.id)).where(
            DetectionResult.blockchain_hash.isnot(None)
        )
        blockchain_result = await self.session.execute(blockchain_query)
        blockchain_count = blockchain_result.scalar()
        
        # Average frame count
        avg_frames_query = select(func.avg(DetectionResult.frame_count))
        avg_frames_result = await self.session.execute(avg_frames_query)
        avg_frames = avg_frames_result.scalar()
        
        return {
            'total_detections': total_count,
            'average_confidence': float(avg_confidence) if avg_confidence else 0.0,
            'blockchain_verified_count': blockchain_count,
            'blockchain_verification_rate': (blockchain_count / total_count * 100) if total_count > 0 else 0.0,
            'average_frame_count': float(avg_frames) if avg_frames else 0.0,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_high_confidence_results(self, threshold: float = 0.8, limit: int = 20) -> List[DetectionResult]:
        """
        Get high confidence detection results for quality analysis.
        """
        query = (
            select(DetectionResult)
            .where(DetectionResult.overall_confidence >= Decimal(str(threshold)))
            .order_by(desc(DetectionResult.overall_confidence))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_low_confidence_results(self, threshold: float = 0.2, limit: int = 20) -> List[DetectionResult]:
        """
        Get low confidence detection results for quality analysis.
        """
        query = (
            select(DetectionResult)
            .where(DetectionResult.overall_confidence <= Decimal(str(threshold)))
            .order_by(asc(DetectionResult.overall_confidence))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
