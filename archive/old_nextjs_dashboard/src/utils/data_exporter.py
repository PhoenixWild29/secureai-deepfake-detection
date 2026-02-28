#!/usr/bin/env python3
"""
Data Export Utility
Multi-format export capabilities for analytics data and stakeholder reporting
"""

import os
import json
import csv
import zipfile
import hashlib
import tempfile
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Union, BinaryIO
from pathlib import Path
import structlog
from decimal import Decimal
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io

from src.models.analytics_data import (
    AnalyticsResponse,
    AnalyticsExportRequest,
    AnalyticsExportResult,
    ExportFormat,
    DataClassification,
    DetectionPerformanceMetric,
    UserEngagementMetric,
    SystemUtilizationMetric,
    TrendAnalysis,
    PredictiveAnalytics,
    AnalyticsInsight
)

logger = structlog.get_logger(__name__)


class DataExporter:
    """
    Multi-format data exporter for analytics and stakeholder reporting
    Supports CSV, JSON, PDF, and Excel formats with privacy compliance
    """
    
    def __init__(self, export_directory: str = "exports"):
        """
        Initialize data exporter
        
        Args:
            export_directory: Directory to store exported files
        """
        self.export_directory = Path(export_directory)
        self.export_directory.mkdir(exist_ok=True)
        
        # Export statistics
        self.stats = {
            'total_exports': 0,
            'successful_exports': 0,
            'failed_exports': 0,
            'total_bytes_exported': 0
        }
        
        logger.info("DataExporter initialized", export_directory=export_directory)
    
    async def export_analytics_data(
        self,
        analytics_data: AnalyticsResponse,
        export_request: AnalyticsExportRequest
    ) -> AnalyticsExportResult:
        """
        Export analytics data in the specified format
        
        Args:
            analytics_data: Analytics data to export
            export_request: Export configuration and parameters
            
        Returns:
            Export result with download information
        """
        start_time = datetime.now(timezone.utc)
        self.stats['total_exports'] += 1
        
        try:
            logger.info(
                "Starting analytics data export",
                export_id=export_request.request_id,
                format=export_request.export_format,
                classification=export_request.data_classification
            )
            
            # Validate permissions and data classification
            await self._validate_export_permissions(analytics_data, export_request)
            
            # Generate export file
            file_path, file_size = await self._generate_export_file(
                analytics_data, export_request
            )
            
            # Calculate checksum for integrity verification
            checksum = self._calculate_file_checksum(file_path)
            
            # Generate download URL (in production, this would be a secure signed URL)
            download_url = self._generate_download_url(file_path, export_request)
            
            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(hours=export_request.expiration_hours)
            
            # Count total records
            total_records = (
                len(analytics_data.detection_performance) +
                len(analytics_data.user_engagement) +
                len(analytics_data.system_utilization) +
                len(analytics_data.trends) +
                len(analytics_data.predictions) +
                len(analytics_data.insights)
            )
            
            # Create export result
            export_result = AnalyticsExportResult(
                request_id=export_request.request_id,
                export_format=export_request.export_format,
                file_size_bytes=file_size,
                download_url=download_url,
                expires_at=expires_at,
                checksum=checksum,
                record_count=total_records
            )
            
            # Update statistics
            self.stats['successful_exports'] += 1
            self.stats['total_bytes_exported'] += file_size
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                "Analytics data export completed",
                export_id=export_request.request_id,
                file_size_bytes=file_size,
                record_count=total_records,
                execution_time_seconds=execution_time
            )
            
            return export_result
            
        except Exception as e:
            self.stats['failed_exports'] += 1
            logger.error(
                "Analytics data export failed",
                export_id=export_request.request_id,
                error=str(e)
            )
            raise
    
    async def _validate_export_permissions(
        self,
        analytics_data: AnalyticsResponse,
        export_request: AnalyticsExportRequest
    ):
        """Validate export permissions and data classification"""
        
        # Check data classification compatibility
        if export_request.data_classification == DataClassification.PUBLIC:
            if analytics_data.data_classification in [DataClassification.INTERNAL, DataClassification.CONFIDENTIAL]:
                raise ValueError("Cannot export confidential data as public")
        
        if export_request.data_classification == DataClassification.INTERNAL:
            if analytics_data.data_classification == DataClassification.CONFIDENTIAL:
                raise ValueError("Cannot export confidential data as internal")
        
        # Additional permission checks would be implemented here
        # based on user roles and access controls
        
        logger.debug(
            "Export permissions validated",
            data_classification=analytics_data.data_classification,
            export_classification=export_request.data_classification
        )
    
    async def _generate_export_file(
        self,
        analytics_data: AnalyticsResponse,
        export_request: AnalyticsExportRequest
    ) -> tuple[Path, int]:
        """Generate export file in the specified format"""
        
        # Create unique filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"analytics_export_{timestamp}_{export_request.request_id[:8]}.{export_request.export_format.value}"
        file_path = self.export_directory / filename
        
        try:
            if export_request.export_format == ExportFormat.CSV:
                await self._export_to_csv(analytics_data, file_path, export_request)
            elif export_request.export_format == ExportFormat.JSON:
                await self._export_to_json(analytics_data, file_path, export_request)
            elif export_request.export_format == ExportFormat.PDF:
                await self._export_to_pdf(analytics_data, file_path, export_request)
            elif export_request.export_format == ExportFormat.EXCEL:
                await self._export_to_excel(analytics_data, file_path, export_request)
            else:
                raise ValueError(f"Unsupported export format: {export_request.export_format}")
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Compress if requested
            if export_request.compression:
                compressed_path = file_path.with_suffix(f"{file_path.suffix}.zip")
                with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(file_path, file_path.name)
                
                # Remove original file and update path
                file_path.unlink()
                file_path = compressed_path
                file_size = file_path.stat().st_size
            
            return file_path, file_size
            
        except Exception as e:
            # Clean up file if it exists
            if file_path.exists():
                file_path.unlink()
            raise
    
    async def _export_to_csv(
        self,
        analytics_data: AnalyticsResponse,
        file_path: Path,
        export_request: AnalyticsExportRequest
    ):
        """Export analytics data to CSV format"""
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write metadata header
            if export_request.include_metadata:
                writer.writerow(['METADATA'])
                writer.writerow(['Export ID', analytics_data.request_id])
                writer.writerow(['Export Date', analytics_data.timestamp.isoformat()])
                writer.writerow(['Data Classification', analytics_data.data_classification.value])
                writer.writerow(['Total Records', analytics_data.total_records])
                writer.writerow(['Query Execution Time (ms)', analytics_data.query_execution_time_ms])
                writer.writerow([])
            
            # Export detection performance metrics
            if analytics_data.detection_performance:
                writer.writerow(['DETECTION PERFORMANCE METRICS'])
                writer.writerow([
                    'Metric Name', 'Value', 'Unit', 'Timestamp', 'Confidence Interval Lower',
                    'Confidence Interval Upper', 'Metadata'
                ])
                
                for metric in analytics_data.detection_performance:
                    confidence_lower = ""
                    confidence_upper = ""
                    if metric.confidence_interval:
                        confidence_lower = metric.confidence_interval.get('lower', '')
                        confidence_upper = metric.confidence_interval.get('upper', '')
                    
                    writer.writerow([
                        metric.metric_name,
                        float(metric.value),
                        metric.unit,
                        metric.timestamp.isoformat(),
                        confidence_lower,
                        confidence_upper,
                        json.dumps(metric.metadata) if metric.metadata else ""
                    ])
                
                writer.writerow([])
            
            # Export user engagement metrics
            if analytics_data.user_engagement:
                writer.writerow(['USER ENGAGEMENT METRICS'])
                writer.writerow([
                    'User ID', 'Metric Name', 'Value', 'Timestamp', 'Session ID',
                    'Feature Used', 'Duration Seconds'
                ])
                
                for metric in analytics_data.user_engagement:
                    writer.writerow([
                        metric.user_id,
                        metric.metric_name,
                        float(metric.value),
                        metric.timestamp.isoformat(),
                        metric.session_id or "",
                        metric.feature_used or "",
                        metric.duration_seconds or ""
                    ])
                
                writer.writerow([])
            
            # Export system utilization metrics
            if analytics_data.system_utilization:
                writer.writerow(['SYSTEM UTILIZATION METRICS'])
                writer.writerow([
                    'Resource Type', 'Metric Name', 'Value', 'Unit', 'Timestamp',
                    'Node ID', 'Warning Threshold', 'Critical Threshold'
                ])
                
                for metric in analytics_data.system_utilization:
                    writer.writerow([
                        metric.resource_type,
                        metric.metric_name,
                        float(metric.value),
                        metric.unit,
                        metric.timestamp.isoformat(),
                        metric.node_id or "",
                        float(metric.threshold_warning) if metric.threshold_warning else "",
                        float(metric.threshold_critical) if metric.threshold_critical else ""
                    ])
                
                writer.writerow([])
            
            # Export trends
            if analytics_data.trends:
                writer.writerow(['TREND ANALYSIS'])
                writer.writerow([
                    'Metric Name', 'Trend Direction', 'Change Percentage', 'Period Start',
                    'Period End', 'Correlation Coefficient', 'Significance Level'
                ])
                
                for trend in analytics_data.trends:
                    writer.writerow([
                        trend.metric_name,
                        trend.trend_direction.value,
                        float(trend.change_percentage),
                        trend.period_start.isoformat(),
                        trend.period_end.isoformat(),
                        float(trend.correlation_coefficient) if trend.correlation_coefficient else "",
                        float(trend.significance_level) if trend.significance_level else ""
                    ])
                
                writer.writerow([])
            
            # Export insights
            if analytics_data.insights:
                writer.writerow(['ANALYTICS INSIGHTS'])
                writer.writerow([
                    'Title', 'Description', 'Type', 'Severity', 'Affected Metrics',
                    'Recommended Actions', 'Confidence', 'Created At'
                ])
                
                for insight in analytics_data.insights:
                    writer.writerow([
                        insight.title,
                        insight.description,
                        insight.insight_type,
                        insight.severity,
                        "; ".join(insight.affected_metrics),
                        "; ".join(insight.recommended_actions),
                        float(insight.confidence),
                        insight.created_at.isoformat()
                    ])
    
    async def _export_to_json(
        self,
        analytics_data: AnalyticsResponse,
        file_path: Path,
        export_request: AnalyticsExportRequest
    ):
        """Export analytics data to JSON format"""
        
        # Convert to dictionary with proper serialization
        export_data = {
            "metadata": {
                "export_id": analytics_data.request_id,
                "export_timestamp": analytics_data.timestamp.isoformat(),
                "data_classification": analytics_data.data_classification.value,
                "total_records": analytics_data.total_records,
                "query_execution_time_ms": analytics_data.query_execution_time_ms,
                "cache_hit": analytics_data.cache_hit,
                "data_freshness_minutes": analytics_data.data_freshness_minutes
            },
            "date_range": {
                "type": analytics_data.date_range.type.value,
                "start_date": analytics_data.date_range.start_date.isoformat() if analytics_data.date_range.start_date else None,
                "end_date": analytics_data.date_range.end_date.isoformat() if analytics_data.date_range.end_date else None
            },
            "filters_applied": [
                {
                    "type": filter.type.value,
                    "value": filter.value,
                    "operator": filter.operator
                }
                for filter in analytics_data.filters_applied
            ],
            "detection_performance": [
                {
                    "metric_name": metric.metric_name,
                    "value": float(metric.value),
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "confidence_interval": {
                        "lower": float(metric.confidence_interval["lower"]),
                        "upper": float(metric.confidence_interval["upper"])
                    } if metric.confidence_interval else None,
                    "metadata": metric.metadata
                }
                for metric in analytics_data.detection_performance
            ],
            "user_engagement": [
                {
                    "user_id": metric.user_id,
                    "metric_name": metric.metric_name,
                    "value": float(metric.value),
                    "timestamp": metric.timestamp.isoformat(),
                    "session_id": metric.session_id,
                    "feature_used": metric.feature_used,
                    "duration_seconds": metric.duration_seconds
                }
                for metric in analytics_data.user_engagement
            ],
            "system_utilization": [
                {
                    "resource_type": metric.resource_type,
                    "metric_name": metric.metric_name,
                    "value": float(metric.value),
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "node_id": metric.node_id,
                    "threshold_warning": float(metric.threshold_warning) if metric.threshold_warning else None,
                    "threshold_critical": float(metric.threshold_critical) if metric.threshold_critical else None
                }
                for metric in analytics_data.system_utilization
            ],
            "trends": [
                {
                    "metric_name": trend.metric_name,
                    "trend_direction": trend.trend_direction.value,
                    "change_percentage": float(trend.change_percentage),
                    "period_start": trend.period_start.isoformat(),
                    "period_end": trend.period_end.isoformat(),
                    "data_points": [float(point) for point in trend.data_points],
                    "correlation_coefficient": float(trend.correlation_coefficient) if trend.correlation_coefficient else None,
                    "significance_level": float(trend.significance_level) if trend.significance_level else None
                }
                for trend in analytics_data.trends
            ],
            "predictions": [
                {
                    "metric_name": pred.metric_name,
                    "predicted_value": float(pred.predicted_value),
                    "confidence_score": float(pred.confidence_score),
                    "prediction_date": pred.prediction_date.isoformat(),
                    "model_used": pred.model_used,
                    "historical_accuracy": float(pred.historical_accuracy),
                    "prediction_interval": {
                        "lower": float(pred.prediction_interval["lower"]),
                        "upper": float(pred.prediction_interval["upper"])
                    }
                }
                for pred in analytics_data.predictions
            ],
            "insights": [
                {
                    "insight_id": insight.insight_id,
                    "title": insight.title,
                    "description": insight.description,
                    "insight_type": insight.insight_type,
                    "severity": insight.severity,
                    "affected_metrics": insight.affected_metrics,
                    "recommended_actions": insight.recommended_actions,
                    "confidence": float(insight.confidence),
                    "created_at": insight.created_at.isoformat()
                }
                for insight in analytics_data.insights
            ]
        }
        
        # Write JSON file with pretty formatting
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
    
    async def _export_to_pdf(
        self,
        analytics_data: AnalyticsResponse,
        file_path: Path,
        export_request: AnalyticsExportRequest
    ):
        """Export analytics data to PDF format for stakeholder reporting"""
        
        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        story.append(Paragraph("Analytics Report", title_style))
        story.append(Spacer(1, 12))
        
        # Metadata section
        if export_request.include_metadata:
            story.append(Paragraph("Report Information", styles['Heading2']))
            
            metadata_data = [
                ['Export ID:', analytics_data.request_id],
                ['Export Date:', analytics_data.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')],
                ['Data Classification:', analytics_data.data_classification.value.title()],
                ['Total Records:', str(analytics_data.total_records)],
                ['Query Execution Time:', f"{analytics_data.query_execution_time_ms:.2f} ms"],
                ['Data Freshness:', f"{analytics_data.data_freshness_minutes} minutes"]
            ]
            
            metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
            metadata_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (1, 0), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(metadata_table)
            story.append(Spacer(1, 20))
        
        # Detection Performance Summary
        if analytics_data.detection_performance:
            story.append(Paragraph("Detection Performance Metrics", styles['Heading2']))
            
            # Create summary table
            perf_data = [['Metric', 'Value', 'Unit', 'Timestamp']]
            for metric in analytics_data.detection_performance[:10]:  # Limit to first 10 for PDF
                perf_data.append([
                    metric.metric_name,
                    f"{float(metric.value):.2f}",
                    metric.unit,
                    metric.timestamp.strftime('%Y-%m-%d %H:%M')
                ])
            
            perf_table = Table(perf_data, colWidths=[2*inch, 1*inch, 1*inch, 1.5*inch])
            perf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(perf_table)
            story.append(Spacer(1, 20))
        
        # User Engagement Summary
        if analytics_data.user_engagement:
            story.append(Paragraph("User Engagement Metrics", styles['Heading2']))
            
            # Create summary table
            engagement_data = [['User ID', 'Metric', 'Value', 'Feature Used']]
            for metric in analytics_data.user_engagement[:10]:  # Limit to first 10 for PDF
                engagement_data.append([
                    metric.user_id[:8] + "...",  # Truncate for privacy
                    metric.metric_name,
                    f"{float(metric.value):.0f}",
                    metric.feature_used or "N/A"
                ])
            
            engagement_table = Table(engagement_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.5*inch])
            engagement_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(engagement_table)
            story.append(Spacer(1, 20))
        
        # Insights Section
        if analytics_data.insights:
            story.append(Paragraph("Key Insights & Recommendations", styles['Heading2']))
            
            for insight in analytics_data.insights:
                # Insight title
                insight_title_style = ParagraphStyle(
                    'InsightTitle',
                    parent=styles['Heading3'],
                    fontSize=12,
                    spaceAfter=6,
                    textColor=colors.darkblue
                )
                story.append(Paragraph(insight.title, insight_title_style))
                
                # Insight description
                story.append(Paragraph(insight.description, styles['Normal']))
                
                # Recommendations
                if insight.recommended_actions:
                    story.append(Paragraph("Recommended Actions:", styles['Heading4']))
                    for action in insight.recommended_actions:
                        story.append(Paragraph(f"• {action}", styles['Normal']))
                
                story.append(Spacer(1, 12))
        
        # Footer
        story.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        story.append(Paragraph(
            f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | "
            f"Classification: {analytics_data.data_classification.value.upper()}",
            footer_style
        ))
        
        # Build PDF
        doc.build(story)
    
    async def _export_to_excel(
        self,
        analytics_data: AnalyticsResponse,
        file_path: Path,
        export_request: AnalyticsExportRequest
    ):
        """Export analytics data to Excel format"""
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            
            # Metadata sheet
            if export_request.include_metadata:
                metadata_df = pd.DataFrame([
                    ['Export ID', analytics_data.request_id],
                    ['Export Date', analytics_data.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')],
                    ['Data Classification', analytics_data.data_classification.value],
                    ['Total Records', analytics_data.total_records],
                    ['Query Execution Time (ms)', analytics_data.query_execution_time_ms],
                    ['Data Freshness (minutes)', analytics_data.data_freshness_minutes]
                ], columns=['Field', 'Value'])
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            # Detection Performance sheet
            if analytics_data.detection_performance:
                perf_data = []
                for metric in analytics_data.detection_performance:
                    perf_data.append({
                        'Metric Name': metric.metric_name,
                        'Value': float(metric.value),
                        'Unit': metric.unit,
                        'Timestamp': metric.timestamp,
                        'Confidence Interval Lower': float(metric.confidence_interval['lower']) if metric.confidence_interval and 'lower' in metric.confidence_interval else None,
                        'Confidence Interval Upper': float(metric.confidence_interval['upper']) if metric.confidence_interval and 'upper' in metric.confidence_interval else None,
                        'Metadata': json.dumps(metric.metadata) if metric.metadata else ""
                    })
                
                perf_df = pd.DataFrame(perf_data)
                perf_df.to_excel(writer, sheet_name='Detection Performance', index=False)
            
            # User Engagement sheet
            if analytics_data.user_engagement:
                engagement_data = []
                for metric in analytics_data.user_engagement:
                    engagement_data.append({
                        'User ID': metric.user_id,
                        'Metric Name': metric.metric_name,
                        'Value': float(metric.value),
                        'Timestamp': metric.timestamp,
                        'Session ID': metric.session_id,
                        'Feature Used': metric.feature_used,
                        'Duration (seconds)': metric.duration_seconds
                    })
                
                engagement_df = pd.DataFrame(engagement_data)
                engagement_df.to_excel(writer, sheet_name='User Engagement', index=False)
            
            # System Utilization sheet
            if analytics_data.system_utilization:
                util_data = []
                for metric in analytics_data.system_utilization:
                    util_data.append({
                        'Resource Type': metric.resource_type,
                        'Metric Name': metric.metric_name,
                        'Value': float(metric.value),
                        'Unit': metric.unit,
                        'Timestamp': metric.timestamp,
                        'Node ID': metric.node_id,
                        'Warning Threshold': float(metric.threshold_warning) if metric.threshold_warning else None,
                        'Critical Threshold': float(metric.threshold_critical) if metric.threshold_critical else None
                    })
                
                util_df = pd.DataFrame(util_data)
                util_df.to_excel(writer, sheet_name='System Utilization', index=False)
            
            # Trends sheet
            if analytics_data.trends:
                trends_data = []
                for trend in analytics_data.trends:
                    trends_data.append({
                        'Metric Name': trend.metric_name,
                        'Trend Direction': trend.trend_direction.value,
                        'Change Percentage': float(trend.change_percentage),
                        'Period Start': trend.period_start,
                        'Period End': trend.period_end,
                        'Correlation Coefficient': float(trend.correlation_coefficient) if trend.correlation_coefficient else None,
                        'Significance Level': float(trend.significance_level) if trend.significance_level else None
                    })
                
                trends_df = pd.DataFrame(trends_data)
                trends_df.to_excel(writer, sheet_name='Trends', index=False)
            
            # Insights sheet
            if analytics_data.insights:
                insights_data = []
                for insight in analytics_data.insights:
                    insights_data.append({
                        'Title': insight.title,
                        'Description': insight.description,
                        'Type': insight.insight_type,
                        'Severity': insight.severity,
                        'Affected Metrics': "; ".join(insight.affected_metrics),
                        'Recommended Actions': "; ".join(insight.recommended_actions),
                        'Confidence': float(insight.confidence),
                        'Created At': insight.created_at
                    })
                
                insights_df = pd.DataFrame(insights_data)
                insights_df.to_excel(writer, sheet_name='Insights', index=False)
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum for file integrity verification"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _generate_download_url(self, file_path: Path, export_request: AnalyticsExportRequest) -> str:
        """Generate download URL for exported file"""
        # In production, this would generate a secure signed URL
        # For now, return a simple file path
        return f"/api/v1/analytics/exports/{file_path.name}"
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export statistics"""
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_exports'] / self.stats['total_exports']
                if self.stats['total_exports'] > 0 else 0
            ),
            'average_file_size_bytes': (
                self.stats['total_bytes_exported'] / self.stats['successful_exports']
                if self.stats['successful_exports'] > 0 else 0
            )
        }
    
    def cleanup_expired_exports(self, max_age_hours: int = 24) -> int:
        """Clean up expired export files"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for file_path in self.export_directory.iterdir():
            if file_path.is_file():
                file_modified = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
                if file_modified < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
        
        logger.info("Expired exports cleaned up", cleaned_count=cleaned_count)
        return cleaned_count


# Global exporter instance
_exporter: Optional[DataExporter] = None


async def get_data_exporter() -> DataExporter:
    """Get global data exporter instance"""
    global _exporter
    
    if _exporter is None:
        export_dir = os.getenv('ANALYTICS_EXPORT_DIRECTORY', 'exports')
        _exporter = DataExporter(export_dir)
    
    return _exporter
