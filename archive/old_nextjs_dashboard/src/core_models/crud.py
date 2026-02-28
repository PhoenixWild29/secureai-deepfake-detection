#!/usr/bin/env python3
"""
Async CRUD helpers for core models
"""

from typing import Optional
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID as PyUUID
from datetime import datetime, timezone

from .models import Video, Analysis, DetectionResult, FrameAnalysis, AnalysisStatusEnum


async def get_video_by_hash(session: AsyncSession, file_hash: str) -> Optional[Video]:
	result = await session.execute(select(Video).where(Video.file_hash == file_hash))
	return result.scalars().first()


async def get_or_create_video(
	session: AsyncSession,
	*,
	filename: str,
	file_hash: str,
	file_size: int,
	format: str,
	s3_key: Optional[str] = None,
	user_id: Optional[PyUUID] = None,
) -> Video:
	# Try existing by unique hash
	existing = await get_video_by_hash(session, file_hash)
	if existing:
		return existing
	
	video = Video(
		filename=filename,
		file_hash=file_hash,
		file_size=file_size,
		format=format,
		s3_key=s3_key,
		upload_timestamp=datetime.now(timezone.utc),
		user_id=user_id,
	)
	
	session.add(video)
	try:
		await session.commit()
		await session.refresh(video)
		return video
	except IntegrityError:
		# Unique constraint hit due to race, fetch existing
		await session.rollback()
		existing = await get_video_by_hash(session, file_hash)
		if existing:
			return existing
		raise


async def create_analysis(
	session: AsyncSession,
	*,
	video_id: PyUUID,
	model_version: Optional[str] = None,
	status: AnalysisStatusEnum = AnalysisStatusEnum.QUEUED,
) -> Analysis:
	analysis = Analysis(
		video_id=video_id,
		model_version=model_version,
		status=status,
	)
	session.add(analysis)
	await session.commit()
	await session.refresh(analysis)
	return analysis


async def create_detection_result(
	session: AsyncSession,
	*,
	analysis_id: PyUUID,
	overall_confidence: float,
	frame_count: int,
	suspicious_frames: int,
	blockchain_hash: str,
	artifacts_detected: Optional[dict] = None,
	processing_metadata: Optional[dict] = None,
) -> DetectionResult:
	result = DetectionResult(
		analysis_id=analysis_id,
		overall_confidence=overall_confidence,
		frame_count=frame_count,
		suspicious_frames=suspicious_frames,
		blockchain_hash=blockchain_hash,
		artifacts_detected=artifacts_detected,
		processing_metadata=processing_metadata,
	)
	session.add(result)
	await session.commit()
	await session.refresh(result)
	return result


async def create_frame_analysis(
	session: AsyncSession,
	*,
	result_id: PyUUID,
	frame_number: int,
	confidence_score: float,
	suspicious_regions: Optional[dict] = None,
	artifacts: Optional[dict] = None,
	processing_time_ms: Optional[int] = None,
) -> FrameAnalysis:
	frame = FrameAnalysis(
		result_id=result_id,
		frame_number=frame_number,
		confidence_score=confidence_score,
		suspicious_regions=suspicious_regions,
		artifacts=artifacts,
		processing_time_ms=processing_time_ms,
	)
	session.add(frame)
	await session.commit()
	await session.refresh(frame)
	return frame
