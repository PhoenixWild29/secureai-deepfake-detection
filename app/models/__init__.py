#!/usr/bin/env python3
"""
API Models Package
Pydantic models for frame analysis and detection responses
"""

from .frame_analysis import FrameAnalysisResult, FrameAnalysisSequence
from .detection import DetectionResponse

__all__ = [
    "FrameAnalysisResult",
    "FrameAnalysisSequence", 
    "DetectionResponse"
]
