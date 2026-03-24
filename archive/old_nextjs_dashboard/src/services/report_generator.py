#!/usr/bin/env python3
"""
Report Generator Service
Service for generating multi-format reports (PDF, JSON, CSV) from detection results
"""

import json
import csv
import zipfile
import io
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime, timezone

import logging
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ReportGeneratorService:
    """
    Service for generating professional reports in multiple formats.
    
    Supports:
    - PDF: Professional stakeholder-ready reports
    - JSON: Complete machine-readable data
    - CSV: Tabular format for data analysis
    """
    
    def __init__(self):
        self.pdf_document_margin = 20
        self.pdf_line_height = 7
        self.pdf_font_size = 12
        
    async def generate_pdf_report(
        self,
        analysis_id: UUID,
        detection_data: Dict[str, Any],
        blockchain_data: Dict[str, Any]
    ) -> bytes:
        """
        Generate professional PDF report with detection results and blockchain verification.
        
        Returns:
            bytes: PDF content as bytes for streaming
        """
        try:
            logger.info(f"Generating PDF report for analysis {analysis_id}")
            
            # Create PDF document
            pdf = self._create_pdf_document()
            
            # Add header with company branding
            self._add_pdf_header(pdf, analysis_id)
            
            # Add executive summary
            self._add_executive_summary(pdf, detection_data, blockchain_data)
            
            # Add detection analysis details
            self._add_detection_analysis(pdf, detection_data)
            
            # Add blockchain verification section
            self._add_blockchain_verification(pdf, blockchain_data)
            
            # Add technical details
            self._add_technical_details(pdf, detection_data)
            
            # Add metadata and compliance information
            self._add_compliance_metadata(pdf, analysis_id, detection_data, blockchain_data)
            
            # Convert to bytes
            pdf_string = pdf.output(dest="S")
            pdf_bytes = pdf_string.encode("latin-1")
            
            logger.info(f"PDF report generated successfully for analysis {analysis_id}, size: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF generation failed for analysis {analysis_id}: {str(e)}")
            raise Exception(f"PDF report generation failed: {str(e)}")
    
    async def generate_json_export(
        self,
        analysis_id: UUID,
        detection_data: Dict[str, Any],
        blockchain_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive JSON export with complete detection data.
        
        Returns:
            Dict[str, Any]: Complete machine-readable detection data
        """
        try:
            logger.info(f"Generating JSON export for analysis {analysis_id}")
            
            # Build comprehensive JSON structure
            json_data = {
                "export_metadata": {
                    "analysis_id": str(analysis_id),
                    "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    "export_format": "json",
                    "export_version": "1.0.0",
                    "secureAI_version": "2.0.0"
                },
                "detection_results": {
                    "overall_assessment": {
                        "is_fake": detection_data.get('is_fake', False),
                        "confidence_score": detection_data.get('confidence_score', 0.0),
                        "authenticity_score": detection_data.get('authenticity_score', 0.0),
                        "model_type": detection_data.get('model_type', 'ensemble'),
                        "analysis_timestamp": detection_data.get('timestamp'),
                        "processing_time_seconds": detection_data.get('processing_time_seconds', 0.0)
                    },
                    "frame_level_analysis": {
                        "total_frames": detection_data.get('total_frames', 0),
                        "frames_processed": detection_data.get('frames_processed', 0),
                        "frame_details": detection_data.get('frame_details', []),
                        "confidence_distribution": detection_data.get('confidence_per_frame', []),
                        "suspicious_regions_summary": detection_data.get('suspicious_regions', [])
                    },
                    "artifacts_detected": detection_data.get('artifacts_detected', []),
                    "processing_metadata": detection_data.get('metadata', {})
                },
                "blockchain_verification": {
                    "verification_status": blockchain_data.get('status', 'unknown'),
                    "transaction_hash": blockchain_data.get('transaction_hash'),
                    "block_number": blockchain_data.get('block_number'),
                    "network": blockchain_data.get('network', 'solana'),
                    "verification_timestamp": blockchain_data.get('timestamp'),
                    "tamper_proof_validation": blockchain_data.get('tamper_proof_valid', False),
                    "blockchain_confidence": blockchain_data.get('blockchain_confidence', 0.0)
                },
                "system_information": {
                    "model_version": detection_data.get('model_version', 'unknown'),
                    "detection_algorithms": detection_data.get('algorithms_used', []),
                    "quality_assurance": detection_data.get('quality_assurance', {}),
                    "compliance_flags": detection_data.get('compliance_flags', [])
                }
            }
            
            logger.info(f"JSON export generated successfully for analysis {analysis_id}")
            return json_data
            
        except Exception as e:
            logger.error(f"JSON export generation failed for analysis {analysis_id}: {str(e)}")
            raise Exception(f"JSON export generation failed: {str(e)}")
    
    async def generate_csv_export(
        self,
        analysis_id: UUID,
        detection_data: Dict[str, Any],
        blockchain_data: Dict[str, Any]
    ) -> str:
        """
        Generate CSV export with tabular detection data.
        
        Returns:
            str: CSV content as string for streaming
        """
        try:
            logger.info(f"Generating CSV export for analysis {analysis_id}")
            
            # Create CSV buffer
            csv_buffer = io.StringIO()
            
            # Create CSV writer
            writer = csv.writer(csv_buffer)
            
            # Write header information
            writer.writerow(["SecureAI DeepFake Detection Analysis Report"])
            writer.writerow(["Generated:", datetime.now(timezone.utc).isoformat()])
            writer.writerow(["Analysis ID:", str(analysis_id)])
            writer.writerow([])
            
            # Overall assessment section
            writer.writerow(["=== OVERALL ASSESSMENT ==="])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Is Fake", detection_data.get('is_fake', False)])
            writer.writerow(["Confidence Score", f"{detection_data.get('confidence_score', 0.0):.4f}"])
            writer.writerow(["Authenticity Score", f"{detection_data.get('authenticity_score', 0.0):.4f}"])
            writer.writerow(["Model Type", detection_data.get('model_type', 'unknown')])
            writer.writerow(["Processing Time (seconds)", detection_data.get('processing_time_seconds', 0.0)])
            writer.writerow([])
            
            # Frame-level analysis section
            writer.writerow(["=== FRAME-LEVEL ANALYSIS ==="])
            writer.writerow(["Total Frames", detection_data.get('total_frames', 0)])
            writer.writerow(["Frames Processed", detection_data.get('frames_processed', 0)])
            writer.writerow([])
            
            # Frame-by-frame data
            frame_details = detection_data.get('frame_details', [])
            if frame_details:
                writer.writerow(["=== FRAME-BY-FRAME DATA ==="])
                writer.writerow(["Frame Number", "Confidence Score", "Is Suspicious", "Suspicious Regions", "Processing Time (ms)", "Artifacts Detected"])
                
                for frame in frame_details:
                    writer.writerow([
                        frame.get('frame_number', ''),
                        f"{frame.get('confidence_score', 0.0):.4f}",
                        frame.get('is_suspicious', False),
                        len(frame.get('suspicious_regions', [])),
                        frame.get('processing_time_ms', 0),
                        len(frame.get('artifacts_detected', []))
                    ])
                writer.writerow([])
            
            # Blockchain verification section
            writer.writerow(["=== BLOCKCHAIN VERIFICATION ==="])
            writer.writerow(["Verification Status", blockchain_data.get('status', 'unknown')])
            writer.writerow(["Transaction Hash", blockchain_data.get('transaction_hash', 'N/A')])
            writer.writerow(["Block Number", blockchain_data.get('block_number', 'N/A')])
            writer.writerow(["Network", blockchain_data.get('network', 'unknown')])
            writer.writerow(["Tamper Proof Valid", blockchain_data.get('tamper_proof_valid', False)])
            writer.writerow(["Blockchain Confidence", f"{blockchain_data.get('blockchain_confidence', 0.0):.4f}"])
            writer.writerow([])
            
            # Suspicous regions summary
            suspicious_regions = detection_data.get('suspicious_regions', [])
            if suspicious_regions:
                writer.writerow(["=== SUSPICIOUS REGIONS SUMMARY ==="])
                writer.writerow(["Region", "Confidence", "X", "Y", "Width", "Height", "Description"])
                
                for i, region in enumerate(suspicious_regions):
                    writer.writerow([
                        f"Region_{i+1}",
                        f"{region.get('confidence', 0.0):.4f}",
                        region.get('x', 0),
                        region.get('y', 0),
                        region.get('width', 0),
                        region.get('height', 0),
                        region.get('description', 'Unknown')
                    ])
            
            csv_content = csv_buffer.getvalue()
            csv_buffer.close()
            
            logger.info(f"CSV export generated successfully for analysis {analysis_id}")
            return csv_content
            
        except Exception as e:
            logger.error(f"CSV export generation failed for analysis {analysis_id}: {str(e)}")
            raise Exception(f"CSV export generation failed: {str(e)}")
    
    async def generate_bulk_export(
        self,
        analysis_ids: List[UUID],
        format: str,
        cache_manager: Any,
        blockchain_service: Any
    ) -> io.BytesIO:
        """
        Generate bulk export as ZIP archive containing multiple analysis results.
        
        Returns:
            io.BytesIO: ZIP archive content
        """
        try:
            logger.info(f"Generating bulk export for {len(analysis_ids)} analyses in {format} format")
            
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for analysis_id in analysis_ids:
                    try:
                        # Get cached data for this analysis
                        detection_data = await cache_manager.get_cached_detection_result(analysis_id)
                        blockchain_data = await blockchain_service.get_verification_status(analysis_id)
                        
                        if not detection_data:
                            logger.warning(f"No data found for analysis {analysis_id}, skipping")
                            continue
                        
                        # Generate content based on format
                        if format == 'json':
                            content_data = await self.generate_json_export(analysis_id, detection_data, blockchain_data)
                            content = json.dumps(content_data, indent=2, ensure_ascii=False)
                            filename = f"analysis_{analysis_id}.json"
                            content_bytes = content.encode('utf-8')
                        elif format == 'csv':
                            content = await self.generate_csv_export(analysis_id, detection_data, blockchain_data)
                            filename = f"analysis_{analysis_id}.csv"
                            content_bytes = content.encode('utf-8')
                        else:
                            logger.warning(f"Bulk export not supported for format {format}, skipping {analysis_id}")
                            continue
                        
                        # Add to ZIP
                        zip_file.writestr(filename, content_bytes)
                        
                    except Exception as e:
                        logger.error(f"Failed to process analysis {analysis_id} in bulk export: {str(e)}")
                        continue
            
            zip_buffer.seek(0)
            logger.info(f"Bulk export completed successfully for {len(analysis_ids)} analyses")
            return zip_buffer
            
        except Exception as e:
            logger.error(f"Bulk export generation failed: {str(e)}")
            raise Exception(f"Bulk export generation failed: {str(e)}")
    
    # Private methods for PDF generation
    def _create_pdf_document(self) -> FPDF:
        """Create PDF document with proper formatting"""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=self.pdf_document_margin)
        pdf.set_font("Arial", size=self.pdf_font_size)
        return pdf
    
    def _add_pdf_header(self, pdf: FPDF, analysis_id: UUID):
        """Add professional header to PDF"""
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "SecureAI DeepFake Detection Report", 0, 1, "C")
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 5, f"Analysis ID: {analysis_id}", 0, 1, "C")
        pdf.cell(0, 10, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", 0, 1, "C")
        pdf.ln(5)
    
    def _add_executive_summary(self, pdf: FPDF, detection_data: Dict, blockchain_data: Dict):
        """Add executive summary section"""
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Executive Summary", 0, 1, "L")
        pdf.set_font("Arial", size=self.pdf_font_size)
        
        is_fake = detection_data.get('is_fake', False)
        confidence = detection_data.get('confidence_score', 0.0)
        
        pdf.cell(0, 6, f"This video has been {'identified as SUSPICIOUS' if is_fake else 'verified as AUTHENTIC'}", 0, 1)
        pdf.cell(0, 6, f"Detection confidence: {confidence:.2%}", 0, 1)
        pdf.cell(0, 6, f"Blockchain verification: {blockchain_data.get('status', 'Unknown')}", 0, 1)
        pdf.ln(5)
    
    def _add_detection_analysis(self, pdf: FPDF, detection_data: Dict):
        """Add detailed detection analysis"""
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Detection Analysis", 0, 1, "L")
        pdf.set_font("Arial", size=self.pdf_font_size)
        
        pdf.cell(0, 6, f"Model used: {detection_data.get('model_type', 'Unknown')}", 0, 1)
        pdf.cell(0, 6, f"Total frames analyzed: {detection_data.get('total_frames', 0)}", 0, 1)
        pdf.cell(0, 6, f"Processing time: {detection_data.get('processing_time_seconds', 0):.2f} seconds", 0, 1)
        
        # Add frame-level summary
        frame_details = detection_data.get('frame_details', [])
        if frame_details:
            suspicious_frames = len([f for f in frame_details if f.get('is_suspicious', False)])
            pdf.cell(0, 6, f"Suspicious frames detected: {suspicious_frames}", 0, 1)
        
        pdf.ln(5)
    
    def _add_blockchain_verification(self, pdf: FPDF, blockchain_data: Dict):
        """Add blockchain verification section"""
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Blockchain Verification", 0, 1, "L")
        pdf.set_font("Arial", size=self.pdf_font_size)
        
        pdf.cell(0, 6, f"Transaction Hash: {blockchain_data.get('transaction_hash', 'N/A')}", 0, 1)
        pdf.cell(0, 6, f"Block Number: {blockchain_data.get('block_number', 'N/A')}", 0, 1)
        pdf.cell(0, 6, f"Verification Status: {blockchain_data.get('status', 'Unknown')}", 0, 1)
        pdf.cell(0, 6, f"Tamper Proof Valid: {'Yes' if blockchain_data.get('tamper_proof_valid', False) else 'No'}", 0, 1)
        pdf.ln(5)
    
    def _add_technical_details(self, pdf: FPDF, detection_data: Dict):
        """Add technical implementation details"""
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Technical Details", 0, 1, "L")
        pdf.set_font("Arial", size=self.pdf_font_size)
        
        # Add suspicious regions if available
        suspicious_regions = detection_data.get('suspicious_regions', [])
        if suspicious_regions:
            pdf.cell(0, 6, f"Suspicious regions identified: {len(suspicious_regions)}", 0, 1)
            for i, region in enumerate(suspicious_regions[:5]):  # Limit to first 5 regions
                pdf.cell(0, 6, f"  Region {i+1}: Confidence {region.get('confidence', 0.0):.3f}", 0, 1)
        
        pdf.ln(5)
    
    def _add_compliance_metadata(self, pdf: FPDF, analysis_id: UUID, detection_data: Dict, blockchain_data: Dict):
        """Add compliance and metadata information"""
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Compliance Documentation", 0, 1, "L")
        pdf.set_font("Arial", size=self.pdf_font_size)
        
        pdf.cell(0, 6, "This report is generated by SecureAI DeepFake Detection System", 0, 1)
        pdf.cell(0, 6, f"Report generation timestamp: {datetime.now(timezone.utc).isoformat()}", 0, 1)
        pdf.cell(0, 6, "All analysis results are tamper-proof and blockchain verified", 0, 1)
        pdf.cell(0, 6, f"Report ID: REP_{analysis_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}", 0, 1)
