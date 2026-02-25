#!/usr/bin/env python3
"""
Video Upload Service
Business logic for handling video uploads, session management, and file processing
"""

import os
import uuid
import asyncio
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ..database.models.upload_session import UploadSession
from ..database.config import get_db_session
from ..utils.hash_generator import generate_content_hash
from ..config.settings import get_upload_settings
from ..errors.api_errors import UploadSessionError, FileValidationError


# Configure logging
logger = logging.getLogger(__name__)


class VideoUploadService:
    """
    Service for handling video uploads with session management and deduplication.
    """
    
    def __init__(self):
        """Initialize the upload service."""
        self.settings = get_upload_settings()
        self.temp_dir = Path(self.settings.temp_upload_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure upload directory exists
        self.upload_dir = Path(self.settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def handle_chunk(
        self,
        session_id: Optional[str],
        chunk_index: int,
        total_chunks: int,
        chunk_content: bytes,
        filename: str,
        file_hash: Optional[str],
        user_id: Optional[str],
        upload_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a single chunk of a multipart upload.
        
        Args:
            session_id: Existing session ID or None for new session
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
            chunk_content: Chunk data
            filename: Original filename
            file_hash: Optional file hash for deduplication
            user_id: User ID
            upload_options: Upload options
            
        Returns:
            Dictionary with session info and upload status
        """
        try:
            # Create new session or get existing one
            if session_id:
                session = await self._get_session(session_id)
                if not session:
                    raise UploadSessionError(f"Session not found: {session_id}")
            else:
                session = await self._create_session(
                    filename=filename,
                    total_chunks=total_chunks,
                    file_hash=file_hash,
                    user_id=user_id,
                    upload_options=upload_options
                )
                session_id = session.id
            
            # Validate chunk index
            if chunk_index >= total_chunks:
                raise UploadSessionError(f"Invalid chunk index: {chunk_index} >= {total_chunks}")
            
            # Save chunk
            chunk_path = self._get_chunk_path(session_id, chunk_index)
            with open(chunk_path, 'wb') as f:
                f.write(chunk_content)
            
            # Update session
            await self._update_session_progress(session_id, chunk_index)
            
            # Check if all chunks are received
            chunks_received = await self._count_received_chunks(session_id)
            
            if chunks_received == total_chunks:
                # Assemble complete file
                complete_file_content = await self._assemble_chunks(session_id, total_chunks)
                
                # Validate file size
                if len(complete_file_content) > self.settings.max_file_size:
                    await self.cleanup_session(session_id)
                    raise FileValidationError(
                        message=f"File size exceeds maximum allowed size",
                        filename=filename,
                        file_size=len(complete_file_content),
                        details={'max_size': self.settings.max_file_size}
                    )
                
                # Update session as complete
                await self._mark_session_complete(session_id, len(complete_file_content))
                
                return {
                    'session_id': session_id,
                    'upload_complete': True,
                    'complete_file_content': complete_file_content,
                    'chunks_received': chunks_received,
                    'file_size': len(complete_file_content)
                }
            else:
                return {
                    'session_id': session_id,
                    'upload_complete': False,
                    'chunks_received': chunks_received,
                    'total_chunks': total_chunks
                }
                
        except Exception as e:
            logger.error(f"Error handling chunk: {e}")
            if session_id:
                await self.cleanup_session(session_id)
            raise
    
    async def save_uploaded_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        file_hash: str,
        user_id: Optional[str],
        upload_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save uploaded file and create upload record.
        
        Args:
            file_content: Complete file content
            filename: Original filename
            content_type: MIME content type
            file_hash: File content hash
            user_id: User ID
            upload_options: Upload options
            
        Returns:
            Dictionary with upload details
        """
        try:
            # Generate unique identifiers
            upload_id = str(uuid.uuid4())
            analysis_id = str(uuid.uuid4())
            
            # Create safe filename
            safe_filename = self._sanitize_filename(filename)
            unique_filename = f"{upload_id}_{safe_filename}"
            
            # Save file
            file_path = self.upload_dir / unique_filename
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Create upload record in database
            async with get_db_session() as db:
                # Here you would create an UploadRecord in the database
                # For now, we'll just return the file info
                pass
            
            logger.info(f"File saved successfully: {unique_filename}")
            
            return {
                'upload_id': upload_id,
                'analysis_id': analysis_id,
                'file_path': str(file_path),
                'filename': unique_filename,
                'original_filename': filename,
                'file_size': len(file_content),
                'file_hash': file_hash,
                'content_type': content_type,
                'user_id': user_id,
                'upload_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            raise
    
    async def check_duplicate(self, file_hash: str) -> Dict[str, Any]:
        """
        Check if file hash already exists in the system.
        
        Args:
            file_hash: File content hash
            
        Returns:
            Dictionary with duplicate information
        """
        try:
            # TODO: Implement actual deduplication check using EmbeddingCache
            # For now, return no duplicate
            return {
                'is_duplicate': False,
                'upload_id': None,
                'analysis_id': None,
                'result': None
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return {'is_duplicate': False}
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get upload session status.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session status or None if not found
        """
        try:
            session = await self._get_session(session_id)
            if not session:
                return None
            
            chunks_received = await self._count_received_chunks(session_id)
            
            return {
                'session_id': session_id,
                'filename': session.filename,
                'total_chunks': session.total_chunks,
                'chunks_received': chunks_received,
                'progress_percentage': round((chunks_received / session.total_chunks) * 100, 2),
                'status': session.status,
                'created_at': session.created_at.isoformat(),
                'last_updated': session.last_updated.isoformat(),
                'expires_at': session.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return None
    
    async def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up upload session and remove temporary files.
        
        Args:
            session_id: Session ID to clean up
            
        Returns:
            True if cleanup successful
        """
        try:
            # Remove chunk files
            chunk_dir = self.temp_dir / session_id
            if chunk_dir.exists():
                import shutil
                shutil.rmtree(chunk_dir)
            
            # Remove session from database
            async with get_db_session() as db:
                # TODO: Remove session from database
                pass
            
            logger.info(f"Session cleaned up: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up session: {e}")
            return False
    
    async def _create_session(
        self,
        filename: str,
        total_chunks: int,
        file_hash: Optional[str],
        user_id: Optional[str],
        upload_options: Dict[str, Any]
    ) -> 'UploadSession':
        """Create a new upload session."""
        session_id = str(uuid.uuid4())
        
        # Create session directory
        session_dir = self.temp_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # TODO: Create session in database
        # For now, create a mock session object
        class MockSession:
            def __init__(self):
                self.id = session_id
                self.filename = filename
                self.total_chunks = total_chunks
                self.file_hash = file_hash
                self.user_id = user_id
                self.upload_options = upload_options
                self.status = 'active'
                self.created_at = datetime.now(timezone.utc)
                self.last_updated = datetime.now(timezone.utc)
                self.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        return MockSession()
    
    async def _get_session(self, session_id: str) -> Optional['UploadSession']:
        """Get existing upload session."""
        try:
            # TODO: Get session from database
            # For now, check if session directory exists
            session_dir = self.temp_dir / session_id
            if not session_dir.exists():
                return None
            
            # Mock session object
            class MockSession:
                def __init__(self):
                    self.id = session_id
                    self.filename = "unknown"
                    self.total_chunks = 0
                    self.file_hash = None
                    self.user_id = None
                    self.upload_options = {}
                    self.status = 'active'
                    self.created_at = datetime.now(timezone.utc)
                    self.last_updated = datetime.now(timezone.utc)
                    self.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            
            return MockSession()
            
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def _update_session_progress(self, session_id: str, chunk_index: int) -> None:
        """Update session progress."""
        try:
            # TODO: Update session in database
            pass
        except Exception as e:
            logger.error(f"Error updating session progress: {e}")
    
    async def _mark_session_complete(self, session_id: str, file_size: int) -> None:
        """Mark session as complete."""
        try:
            # TODO: Update session status in database
            pass
        except Exception as e:
            logger.error(f"Error marking session complete: {e}")
    
    async def _count_received_chunks(self, session_id: str) -> int:
        """Count received chunks for a session."""
        try:
            session_dir = self.temp_dir / session_id
            if not session_dir.exists():
                return 0
            
            chunk_files = list(session_dir.glob("chunk_*"))
            return len(chunk_files)
            
        except Exception as e:
            logger.error(f"Error counting chunks: {e}")
            return 0
    
    async def _assemble_chunks(self, session_id: str, total_chunks: int) -> bytes:
        """Assemble chunks into complete file content."""
        try:
            session_dir = self.temp_dir / session_id
            complete_content = bytearray()
            
            for i in range(total_chunks):
                chunk_path = session_dir / f"chunk_{i}"
                if chunk_path.exists():
                    with open(chunk_path, 'rb') as f:
                        complete_content.extend(f.read())
                else:
                    raise UploadSessionError(f"Missing chunk {i}")
            
            return bytes(complete_content)
            
        except Exception as e:
            logger.error(f"Error assembling chunks: {e}")
            raise UploadSessionError(f"Failed to assemble chunks: {str(e)}")
    
    def _get_chunk_path(self, session_id: str, chunk_index: int) -> Path:
        """Get path for a specific chunk."""
        session_dir = self.temp_dir / session_id
        return session_dir / f"chunk_{chunk_index}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        import re
        
        # Remove or replace unsafe characters
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Ensure filename doesn't start with dot
        if safe_filename.startswith('.'):
            safe_filename = 'file_' + safe_filename
        
        # Limit length
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:95] + ext
        
        return safe_filename


# Global service instance
_upload_service: Optional[VideoUploadService] = None


def get_video_upload_service() -> VideoUploadService:
    """Get or create the global upload service instance."""
    global _upload_service
    if _upload_service is None:
        _upload_service = VideoUploadService()
    return _upload_service


# Export main service class
__all__ = [
    'VideoUploadService',
    'get_video_upload_service'
]
