#!/usr/bin/env python3
"""
Audit Logger Utility
Compliance-ready audit logging for report generation and export tracking
"""

import json
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """Structured audit log entry"""
    event_type: str
    analysis_id: str
    user_id: Optional[str]
    timestamp: str
    export_format: Optional[str]
    file_size_bytes: Optional[int]
    status: str  # success, failure, partial
    error_message: Optional[str]
    request_metadata: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    compliance_flags: List[str]


class AuditLogger:
    """
    Audit logger for compliance and security tracking.
    
    Provides comprehensive logging for:
    - Report generation events
    - Export requests and responses
    - Security and access events
    - Compliance audit trail
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        """
        Initialize audit logger.
        
        Args:
            log_file_path: Optional custom log file path
        """
        self.log_file_path = log_file_path or self._get_default_log_path()
        self._ensure_log_directory()
        
        # Configure audit-specific logger
        self.audit_logger = logging.getLogger(f"audit_logger_{id(self)}")
        self.audit_logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.audit_logger.handlers:
            self._setup_file_handler()
            self._setup_console_handler()
    
    def _get_default_log_path(self) -> str:
        """Generate default log file path with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"logs/audit_export_{timestamp}.log"
    
    def _ensure_log_directory(self):
        """Ensure log directory exists"""
        log_path = Path(self.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _setup_file_handler(self):
        """Setup file handler for audit logs"""
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        
        # Custom formatter for audit logs
        audit_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(audit_formatter)
        self.audit_logger.addHandler(file_handler)
    
    def _setup_console_handler(self):
        """Setup console handler for development"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        console_formatter = logging.Formatter(
            '%(asctime)s | AUDIT | %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.audit_logger.addHandler(console_handler)
    
    async def log_export_request(
        self,
        analysis_id: str,
        export_format: str,
        user_id: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log an export request for audit trail.
        
        Args:
            analysis_id: Analysis identifier
            export_format: Requested export format (pdf, json, csv)
            user_id: User requesting export (if authenticated)
            request_metadata: Additional request data
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            AuditLogEntry: Created audit log entry
        """
        audit_entry = AuditLogEntry(
            event_type="export_request",
            analysis_id=analysis_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            export_format=export_format,
            file_size_bytes=None,
            status="pending",
            error_message=None,
            request_metadata=request_metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            compliance_flags=["export_tracking", "user_action"]
        )
        
        await self._write_audit_entry(audit_entry)
        return audit_entry
    
    async def log_export_success(
        self,
        analysis_id: str,
        export_format: str,
        file_size_bytes: int,
        user_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> AuditLogEntry:
        """
        Log successful export completion.
        
        Args:
            analysis_id: Analysis identifier
            export_format: Exported format
            file_size_bytes: Size of generated file
            user_id: User who requested export
            processing_time_ms: Time taken to generate export
            
        Returns:
            AuditLogEntry: Created audit log entry
        """
        audit_entry = AuditLogEntry(
            event_type="export_success",
            analysis_id=analysis_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            export_format=export_format,
            file_size_bytes=file_size_bytes,
            status="success",
            error_message=None,
            request_metadata={"processing_time_ms": processing_time_ms},
            ip_address=None,
            user_agent=None,
            compliance_flags=["export_success", "file_generation", "compliance_logged"]
        )
        
        await self._write_audit_entry(audit_entry)
        return audit_entry
    
    async def log_export_failure(
        self,
        analysis_id: str,
        export_format: str,
        error_message: str,
        user_id: Optional[str] = None,
        exception_type: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log export failure for security audit.
        
        Args:
            analysis_id: Analysis identifier
            export_format: Failed format
            error_message: Error description
            user_id: User who requested export
            exception_type: Type of exception that occurred
            
        Returns:
            AuditLogEntry: Created audit log entry
        """
        audit_entry = AuditLogEntry(
            event_type="export_failure",
            analysis_id=analysis_id,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            export_format=export_format,
            file_size_bytes=None,
            status="failure",
            error_message=error_message,
            request_metadata={"exception_type": exception_type},
            ip_address=None,
            user_agent=None,
            compliance_flags=["export_failure", "security_event", "error_tracking"]
        )
        
        await self._write_audit_entry(audit_entry)
        return audit_entry
    
    async def log_bulk_export_request(
        self,
        analysis_ids: List[str],
        export_format: str,
        user_id: Optional[str] = None,
        total_records: Optional[int] = None
    ) -> AuditLogEntry:
        """
        Log bulk export request for compliance tracking.
        
        Args:
            analysis_ids: List of analysis identifiers
            export_format: Export format for all records
            user_id: User requesting bulk export
            total_records: Total number of records to export
            
        Returns:
            AuditLogEntry: Created audit log entry
        """
        audit_entry = AuditLogEntry(
            event_type="bulk_export_request",
            analysis_id=",".join(analysis_ids[:5]) + ("..." if len(analysis_ids) > 5 else ""),
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            export_format=export_format,
            file_size_bytes=None,
            status="pending",
            error_message=None,
            request_metadata={
                "record_count": len(analysis_ids),
                "total_records": total_records or len(analysis_ids),
                "analysis_ids_count": len(analysis_ids)
            },
            ip_address=None,
            user_agent=None,
            compliance_flags=["bulk_export", "batch_processing", "compliance_logged"]
        )
        
        await self._write_audit_entry(audit_entry)
        return audit_entry
    
    async def log_security_event(
        self,
        event_type: str,
        description: str,
        severity: str = "medium",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event
            description: Event description
            severity: Event severity (low, medium, high, critical)
            user_id: Associated user
            ip_address: Source IP address
            additional_context: Additional context data
            
        Returns:
            AuditLogEntry: Created audit log entry
        """
        audit_entry = AuditLogEntry(
            event_type=f"security_{event_type}",
            analysis_id=None,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            export_format=None,
            file_size_bytes=None,
            status="logged",
            error_message=None,
            request_metadata={
                "security_event": True,
                "severity": severity,
                "description": description,
                **additional_context or {}
            },
            ip_address=ip_address,
            user_agent=None,
            compliance_flags=["security_audit", severity, "event_logged"]
        )
        
        await self._write_audit_entry(audit_entry)
        return audit_entry
    
    async def _write_audit_entry(self, entry: AuditLogEntry):
        """Write audit entry to log file and structured storage"""
        try:
            # Convert to JSON-serializable format
            entry_dict = asdict(entry)
            
            # Write structured log entry
            log_message = json.dumps(entry_dict, ensure_ascii=False, indent=None)
            self.audit_logger.info(log_message)
            
            # Also write to compliance-specific storage if needed
            await self._write_compliance_entry(entry_dict)
            
        except Exception as e:
            # Fallback logging if structured logging fails
            logger.error(f"Failed to write audit entry: {str(e)}")
            self.audit_logger.error(f"Failed to write audit entry for {entry.analysis_id}: {str(e)}")
    
    async def _write_compliance_entry(self, entry_dict: Dict[str, Any]):
        """Write entry to compliance-specific storage (placeholder for future implementation)"""
        # This could write to a compliance database, immutable ledger, etc.
        # For now, we'll ensure the file-based audit trail is comprehensive
        logger.debug(f"Compliance entry logged: {entry_dict.get('event_type')}")
    
    async def query_audit_logs(
        self,
        analysis_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs for compliance reporting.
        
        Args:
            analysis_id: Filter by analysis ID
            user_id: Filter by user ID
            event_type: Filter by event type
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum number of results
            
        Returns:
            List of matching audit log entries
        """
        try:
            # This is a simplified version - in production, this would query a database
            # For file-based logs, we'd parse the log file and filter
            
            # Placeholder implementation - would be replaced with database query
            return []
            
        except Exception as e:
            logger.error(f"Failed to query audit logs: {str(e)}")
            return []
    
    async def generate_compliance_report(
        self,
        report_period: str,
        include_security_events: bool = True,
        include_export_events: bool = True
    ) -> Dict[str, Any]:
        """
        Generate compliance report for regulatory purposes.
        
        Args:
            report_period: Reporting period identifier
            include_security_events: Include security events
            include_export_events: Include export events
            
        Returns:
            Compliance report data
        """
        try:
            compliance_report = {
                "report_metadata": {
                    "generated_timestamp": datetime.now(timezone.utc).isoformat(),
                    "report_period": report_period,
                    "auditor_version": "1.0.0"
                },
                "summary_statistics": {},
                "export_events": [],
                "security_events": [],
                "compliance_flags": []
            }
            
            # Generate summary statistics (placeholder)
            compliance_report["summary_statistics"] = {
                "total_exports": 0,
                "total_security_events": 0,
                "compliance_score": "100%"
            }
            
            logger.info(f"Generated compliance report for period {report_period}")
            return compliance_report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            raise Exception(f"Compliance report generation failed: {str(e)}")


# Global audit logger instance for easy import
audit_logger = AuditLogger()


# Utility function for quick audit logging
async def log_quick_export_event(
    analysis_id: str,
    event_type: str,
    export_format: str,
    status: str,
    **kwargs
) -> AuditLogEntry:
    """
    Quick utility function for logging export events.
    
    Args:
        analysis_id: Analysis identifier
        event_type: Type of event (request, success, failure)
        export_format: Export format
        status: Event status
        **kwargs: Additional event data
        
    Returns:
        AuditLogEntry: Created audit log entry
    """
    global audit_logger
    
    if event_type == "request":
        return await audit_logger.log_export_request(analysis_id, export_format, **kwargs)
    elif event_type == "success":
        return await audit_logger.log_export_success(analysis_id, export_format, **kwargs)
    elif event_type == "failure":
        return await audit_logger.log_export_failure(analysis_id, export_format, **kwargs)
    else:
        raise ValueError(f"Unknown event type: {event_type}")
