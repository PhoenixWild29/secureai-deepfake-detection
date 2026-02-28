#!/usr/bin/env python3
"""
Detection Serialization Service
Serialization patterns for multiple export formats maintaining data consistency
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID, uuid4
from datetime import datetime, timezone
from decimal import Decimal
import json

# Import existing Core Detection Engine models
from ..core_models.models import DetectionResult, FrameAnalysis, Analysis, Video
from ..models.detection_results import ExportFormatEnum


class DetectionSerializationService:
    """
    Service class for serializing detection results into various export formats.
    Maintains data consistency with existing DetectionResponse model structure.
    """
    
    def __init__(self):
        """Initialize serialization service"""
        pass
    
    def serialize_to_json(
        self, 
        result_data: Dict[str, Any], 
        include_frames: bool = True,
        include_blockchain: bool = True
    ) -> Dict[str, Any]:
        """
        Serialize detection result to JSON format.
        Maintains compatibility with existing DetectionResponse structure.
        """
        json_data = {
            # Core DetectionResponse fields
            "analysis_id": str(result_data.get("analysis_id", "")),
            "status": result_data.get("status", "completed"),
            "overall_confidence": float(result_data.get("overall_confidence", 0.0)),
            "processing_time_ms": result_data.get("processing_time_ms", 0),
            "created_at": result_data.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(result_data.get("created_at"), datetime) else result_data.get("created_at"),
            
            # Extended fields for visualization
            "frame_count": result_data.get("frame_count", 0),
            "suspicious_frames": result_data.get("suspicious_frames", 0),
            "confidence_distribution": result_data.get("confidence_distribution", {}),
            "suspicious_regions_summary": result_data.get("suspicious_regions_summary", []),
            
            # Export metadata
            "export_format": "json",
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "export_version": "1.0"
        }
        
        # Include blockchain data if requested
        if include_blockchain:
            json_data["blockchain_hash"] = result_data.get("blockchain_hash")
            json_data["blockchain_verification"] = result_data.get("blockchain_verification", {})
        
        # Include frame-level data if requested
        if include_frames and "frame_analysis" in result_data:
            json_data["frame_analysis"] = self._serialize_frame_analysis_list(result_data["frame_analysis"])
        
        # Include audit trail
        json_data["audit_trail"] = self.create_audit_trail(result_data)
        
        return json_data
    
    def prepare_csv_data(
        self, 
        result_data: Dict[str, Any], 
        frame_data: List[FrameAnalysis]
    ) -> List[Dict[str, Any]]:
        """
        Prepare data for CSV export format.
        Creates flattened structure with frame-level rows.
        """
        csv_rows = []
        
        # Header row with summary data
        header_row = {
            "analysis_id": str(result_data.get("analysis_id", "")),
            "overall_confidence": float(result_data.get("overall_confidence", 0.0)),
            "frame_count": result_data.get("frame_count", 0),
            "suspicious_frames": result_data.get("suspicious_frames", 0),
            "processing_time_ms": result_data.get("processing_time_ms", 0),
            "created_at": result_data.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(result_data.get("created_at"), datetime) else result_data.get("created_at"),
            "blockchain_hash": result_data.get("blockchain_hash", ""),
            "frame_number": "SUMMARY",
            "frame_confidence": float(result_data.get("overall_confidence", 0.0)),
            "frame_processing_time_ms": 0,
            "suspicious_regions_count": len(result_data.get("suspicious_regions_summary", [])),
            "frame_artifacts": ""
        }
        csv_rows.append(header_row)
        
        # Frame-level rows
        for frame in frame_data:
            frame_row = {
                "analysis_id": str(result_data.get("analysis_id", "")),
                "overall_confidence": float(result_data.get("overall_confidence", 0.0)),
                "frame_count": result_data.get("frame_count", 0),
                "suspicious_frames": result_data.get("suspicious_frames", 0),
                "processing_time_ms": result_data.get("processing_time_ms", 0),
                "created_at": result_data.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(result_data.get("created_at"), datetime) else result_data.get("created_at"),
                "blockchain_hash": result_data.get("blockchain_hash", ""),
                "frame_number": frame.frame_number,
                "frame_confidence": float(frame.confidence_score),
                "frame_processing_time_ms": frame.processing_time_ms or 0,
                "suspicious_regions_count": len(frame.suspicious_regions) if frame.suspicious_regions else 0,
                "frame_artifacts": json.dumps(frame.artifacts) if frame.artifacts else ""
            }
            csv_rows.append(frame_row)
        
        return csv_rows
    
    def prepare_pdf_data(
        self, 
        result_data: Dict[str, Any], 
        frame_data: List[FrameAnalysis]
    ) -> Dict[str, Any]:
        """
        Prepare structured data for PDF export format.
        Organizes data for document generation.
        """
        pdf_data = {
            # Document metadata
            "document_info": {
                "title": "Deepfake Detection Analysis Report",
                "analysis_id": str(result_data.get("analysis_id", "")),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "report_version": "1.0"
            },
            
            # Executive summary
            "executive_summary": {
                "overall_confidence": float(result_data.get("overall_confidence", 0.0)),
                "confidence_percentage": float(result_data.get("overall_confidence", 0.0)) * 100,
                "is_fake": float(result_data.get("overall_confidence", 0.0)) > 0.5,
                "frame_count": result_data.get("frame_count", 0),
                "suspicious_frames": result_data.get("suspicious_frames", 0),
                "processing_time_seconds": result_data.get("processing_time_ms", 0) / 1000.0,
                "created_at": result_data.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(result_data.get("created_at"), datetime) else result_data.get("created_at")
            },
            
            # Technical details
            "technical_details": {
                "analysis_id": str(result_data.get("analysis_id", "")),
                "processing_time_ms": result_data.get("processing_time_ms", 0),
                "blockchain_verification": result_data.get("blockchain_verification", {}),
                "confidence_distribution": result_data.get("confidence_distribution", {}),
                "suspicious_regions_summary": result_data.get("suspicious_regions_summary", [])
            },
            
            # Frame analysis summary
            "frame_analysis_summary": {
                "total_frames": len(frame_data),
                "suspicious_frames": len([f for f in frame_data if f.confidence_score > 0.5]),
                "average_confidence": sum(float(f.confidence_score) for f in frame_data) / len(frame_data) if frame_data else 0.0,
                "confidence_range": {
                    "min": min(float(f.confidence_score) for f in frame_data) if frame_data else 0.0,
                    "max": max(float(f.confidence_score) for f in frame_data) if frame_data else 0.0
                }
            },
            
            # Detailed frame data (first 10 frames for PDF)
            "frame_details": [
                {
                    "frame_number": frame.frame_number,
                    "confidence_score": float(frame.confidence_score),
                    "processing_time_ms": frame.processing_time_ms or 0,
                    "suspicious_regions": frame.suspicious_regions or {},
                    "artifacts": frame.artifacts or {}
                }
                for frame in frame_data[:10]  # Limit for PDF readability
            ],
            
            # Audit information
            "audit_trail": self.create_audit_trail(result_data)
        }
        
        return pdf_data
    
    def create_audit_trail(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive audit trail for data integrity.
        Preserves audit trail requirements from existing models.
        """
        audit_trail = {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "export_source": "detection_results_api",
            "data_version": "1.0",
            "original_analysis_id": str(data.get("analysis_id", "")),
            "original_created_at": data.get("created_at", datetime.now(timezone.utc)).isoformat() if isinstance(data.get("created_at"), datetime) else str(data.get("created_at", "")),
            "blockchain_hash": data.get("blockchain_hash", ""),
            "data_integrity_checks": {
                "confidence_range_valid": self._validate_confidence_range(data.get("overall_confidence", 0.0)),
                "frame_count_positive": data.get("frame_count", 0) >= 0,
                "suspicious_frames_valid": data.get("suspicious_frames", 0) <= data.get("frame_count", 0),
                "timestamp_present": bool(data.get("created_at"))
            },
            "serialization_metadata": {
                "frames_included": bool(data.get("frame_analysis")),
                "blockchain_included": bool(data.get("blockchain_hash")),
                "regions_summary_included": bool(data.get("suspicious_regions_summary")),
                "confidence_distribution_included": bool(data.get("confidence_distribution"))
            }
        }
        
        return audit_trail
    
    def format_blockchain_verification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format blockchain verification data for export.
        """
        blockchain_data = data.get("blockchain_verification", {})
        
        formatted_data = {
            "blockchain_hash": data.get("blockchain_hash", ""),
            "verification_status": blockchain_data.get("status", "not_available"),
            "is_tamper_proof": blockchain_data.get("is_tamper_proof", False),
            "verification_timestamp": blockchain_data.get("verification_timestamp"),
            "verification_details": blockchain_data.get("verification_details", {}),
            "hash_validation": {
                "length": len(data.get("blockchain_hash", "")),
                "format": "hex" if data.get("blockchain_hash", "") and all(c in '0123456789abcdefABCDEF' for c in data.get("blockchain_hash", "")) else "unknown",
                "is_valid_format": bool(data.get("blockchain_hash", ""))
            }
        }
        
        return formatted_data
    
    def aggregate_frame_statistics(self, frames: List[FrameAnalysis]) -> Dict[str, Any]:
        """
        Create statistical summaries from frame analysis data.
        """
        if not frames:
            return {
                "total_frames": 0,
                "average_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "suspicious_frames": 0,
                "confidence_std_dev": 0.0
            }
        
        confidence_scores = [float(frame.confidence_score) for frame in frames]
        suspicious_count = len([f for f in frames if f.confidence_score > 0.5])
        
        # Calculate statistics
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        min_confidence = min(confidence_scores)
        max_confidence = max(confidence_scores)
        
        # Calculate standard deviation
        variance = sum((score - avg_confidence) ** 2 for score in confidence_scores) / len(confidence_scores)
        std_dev = variance ** 0.5
        
        # Processing time statistics
        processing_times = [frame.processing_time_ms or 0 for frame in frames]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            "total_frames": len(frames),
            "average_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "confidence_std_dev": std_dev,
            "suspicious_frames": suspicious_count,
            "suspicious_percentage": (suspicious_count / len(frames)) * 100,
            "average_processing_time_ms": avg_processing_time,
            "total_processing_time_ms": sum(processing_times),
            "frames_with_regions": len([f for f in frames if f.suspicious_regions]),
            "frames_with_artifacts": len([f for f in frames if f.artifacts])
        }
    
    def _serialize_frame_analysis_list(self, frame_analyses: List[FrameAnalysis]) -> List[Dict[str, Any]]:
        """
        Serialize list of FrameAnalysis objects to dictionaries.
        """
        serialized_frames = []
        
        for frame in frame_analyses:
            frame_data = {
                "frame_number": frame.frame_number,
                "confidence_score": float(frame.confidence_score),
                "processing_time_ms": frame.processing_time_ms,
                "suspicious_regions": frame.suspicious_regions or {},
                "artifacts": frame.artifacts or {}
            }
            serialized_frames.append(frame_data)
        
        return serialized_frames
    
    def _validate_confidence_range(self, confidence: Union[float, Decimal, int]) -> bool:
        """
        Validate confidence score is within valid range.
        """
        try:
            conf_float = float(confidence)
            return 0.0 <= conf_float <= 1.0
        except (ValueError, TypeError):
            return False
    
    def create_export_manifest(self, export_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create export manifest for tracking and validation.
        """
        manifest = {
            "export_id": str(uuid4()),
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "export_format": export_request.get("format", "json"),
            "analysis_id": export_request.get("analysis_id", ""),
            "include_frames": export_request.get("include_frames", True),
            "include_blockchain": export_request.get("include_blockchain", True),
            "export_options": export_request.get("export_options", {}),
            "manifest_version": "1.0",
            "export_service": "detection_serialization_service"
        }
        
        return manifest
    
    def validate_export_data_integrity(self, serialized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate serialized export data for integrity.
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "validation_checks": {}
        }
        
        # Check required fields
        required_fields = ["analysis_id", "overall_confidence", "created_at"]
        for field in required_fields:
            if field not in serialized_data:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["is_valid"] = False
            else:
                validation_result["validation_checks"][f"{field}_present"] = True
        
        # Validate confidence score
        if "overall_confidence" in serialized_data:
            confidence = serialized_data["overall_confidence"]
            is_valid_range = 0.0 <= confidence <= 1.0
            validation_result["validation_checks"]["confidence_range_valid"] = is_valid_range
            if not is_valid_range:
                validation_result["errors"].append("overall_confidence must be between 0.0 and 1.0")
                validation_result["is_valid"] = False
        
        # Validate frame count consistency
        if "frame_count" in serialized_data and "frame_analysis" in serialized_data:
            expected_count = serialized_data["frame_count"]
            actual_count = len(serialized_data["frame_analysis"])
            validation_result["validation_checks"]["frame_count_consistent"] = expected_count == actual_count
            if expected_count != actual_count:
                validation_result["warnings"].append(f"Frame count mismatch: expected {expected_count}, found {actual_count}")
        
        # Validate audit trail presence
        if "audit_trail" in serialized_data:
            audit_trail = serialized_data["audit_trail"]
            has_required_audit_fields = all(field in audit_trail for field in ["export_timestamp", "data_version", "original_analysis_id"])
            validation_result["validation_checks"]["audit_trail_complete"] = has_required_audit_fields
            if not has_required_audit_fields:
                validation_result["warnings"].append("Incomplete audit trail")
        
        return validation_result
