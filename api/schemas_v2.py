#!/usr/bin/env python3
"""
API Schemas v2
Pydantic models for request/response validation and OpenAPI documentation (WO-15).
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo
from fastapi import UploadFile


MAX_UPLOAD_MB = 500
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


class FrameAnalysisResult(BaseModel):
	"""
	Nested frame-level analysis details for a detection response.
	"""
	frame_number: int = Field(..., ge=0, description="Zero-based index of the analyzed frame.")
	confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0..1.0) for this frame.")
	suspicious_regions: Optional[List[Dict[str, Any]]] = Field(
		None,
		description="Optional list of structured region annotations identified as suspicious."
	)
	artifacts: Optional[Dict[str, Any]] = Field(
		None,
		description="Optional structured details of artifacts detected in this frame."
	)
	processing_time_ms: Optional[int] = Field(
		None,
		ge=0,
		description="Processing time for this frame in milliseconds (non-decreasing across sequence)."
	)
	embedding_cached: Optional[bool] = Field(
		None,
		description="Whether the embedding for this frame was served from cache."
	)

	@field_validator("confidence_score")
	@classmethod
	def validate_confidence_range(cls, v: float) -> float:
		if v < 0.0 or v > 1.0:
			raise ValueError("confidence_score must be within [0.0, 1.0]")
		return v


class DetectionResponse(BaseModel):
	"""
	Standardized detection response payload.
	"""
	analysis_id: UUID = Field(..., description="Unique identifier of the analysis.")
	overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall detection confidence (0.0..1.0).")
	status: str = Field(..., description="Processing status (e.g., 'queued', 'processing', 'completed', 'failed').")
	frame_count: int = Field(..., ge=0, description="Total number of frames analyzed.")
	suspicious_frames: int = Field(..., ge=0, description="Total number of frames flagged as suspicious.")
	blockchain_hash: Optional[str] = Field(None, description="Blockchain transaction hash for verification, if available.")
	frame_analysis: List[FrameAnalysisResult] = Field(
		default_factory=list,
		description="List of frame-level analysis results."
	)
	processing_time_ms: int = Field(..., ge=0, description="Total processing time in milliseconds.")
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(timezone.utc),
		description="Timestamp when the detection result was created (UTC)."
	)

	@field_validator("overall_confidence")
	@classmethod
	def validate_overall_confidence(cls, v: float) -> float:
		if v < 0.0 or v > 1.0:
			raise ValueError("overall_confidence must be within [0.0, 1.0]")
		return v

	@model_validator(mode="after")
	def validate_frame_sequence(self) -> "DetectionResponse":
		if not self.frame_analysis:
			return self
		# Ensure frames are sequential starting from 0 with step 1
		expected = 0
		last_time: Optional[int] = None
		for fa in self.frame_analysis:
			if fa.frame_number != expected:
				raise ValueError(f"frame_analysis must be sequential starting at 0; expected {expected} but found {fa.frame_number}")
			if fa.processing_time_ms is not None:
				if last_time is not None and fa.processing_time_ms < last_time:
					raise ValueError("processing_time_ms must be non-decreasing across frames")
				last_time = fa.processing_time_ms
			expected += 1
		return self


class VideoUploadRequest(BaseModel):
	"""
	Request model for uploading a video for analysis.
	Includes UploadFile, optional description, file size (<= 500MB) and format validation.
	"""
	file: UploadFile = Field(..., description="The video file to analyze. Supported: MP4, AVI, MOV, MKV, WEBM.")
	description: Optional[str] = Field(None, max_length=1000, description="Optional human-readable description (<=1000 chars).")

	@field_validator("file")
	@classmethod
	def validate_file_constraints(cls, v: UploadFile, info: ValidationInfo) -> UploadFile:
		# Validate file extension
		filename = v.filename or ""
		lower = filename.lower()
		ext = "." + lower.split(".")[-1] if "." in lower else ""
		if ext not in SUPPORTED_EXTENSIONS:
			raise ValueError(
				f"Unsupported file format '{ext}'. Supported: {', '.join(sorted(e.upper() for e in SUPPORTED_EXTENSIONS))}"
			)

		# Best-effort size validation without fully reading the stream
		try:
			spooled = getattr(v, "file", None)
			if hasattr(spooled, "tell") and hasattr(spooled, "seek"):
				pos = spooled.tell()
				spooled.seek(0, 2)  # seek to end
				size = spooled.tell()
				spooled.seek(pos)
				if size > MAX_UPLOAD_BYTES:
					raise ValueError(f"File exceeds {MAX_UPLOAD_MB}MB limit")
			# Fallback: if server provided size metadata
			size_hint = getattr(v, "size", None)
			if isinstance(size_hint, int) and size_hint > MAX_UPLOAD_BYTES:
				raise ValueError(f"File exceeds {MAX_UPLOAD_MB}MB limit")
		except Exception:
			# If size cannot be determined at model-validate time, allow and enforce at endpoint layer
			pass
		return v
