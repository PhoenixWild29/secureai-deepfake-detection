#!/usr/bin/env python3
"""
Migration: Create Upload Session Tables
Create tables for upload session tracking, chunk management, and progress logging
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create upload session tables."""
    
    # Create upload_session table
    op.create_table(
        'upload_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_hash', sa.String(length=128), nullable=True),
        sa.Column('total_chunks', sa.Integer(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('chunks_received', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'FAILED', 'EXPIRED', 'CANCELLED', name='uploadsessionstatus'), nullable=False, default='ACTIVE'),
        sa.Column('user_id', sa.String(length=128), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('upload_options', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=dict),
        sa.Column('priority', sa.Integer(), nullable=False, default=5),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=dict),
        sa.Column('upload_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processing_job_id', sa.String(length=128), nullable=True),
        sa.Column('progress_percentage', sa.Float(), nullable=False, default=0.0),
        sa.Column('bytes_uploaded', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create indexes for upload_session
    op.create_index('idx_upload_session_session_id', 'upload_session', ['session_id'])
    op.create_index('idx_upload_session_user_id', 'upload_session', ['user_id'])
    op.create_index('idx_upload_session_status', 'upload_session', ['status'])
    op.create_index('idx_upload_session_expires_at', 'upload_session', ['expires_at'])
    op.create_index('idx_upload_session_file_hash', 'upload_session', ['file_hash'])
    op.create_index('idx_upload_session_created_at', 'upload_session', ['created_at'])
    
    # Create upload_chunk table
    op.create_table(
        'upload_chunk',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('chunk_hash', sa.String(length=128), nullable=True),
        sa.Column('storage_path', sa.String(length=512), nullable=True),
        sa.Column('received', sa.Boolean(), nullable=False, default=False),
        sa.Column('verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for upload_chunk
    op.create_index('idx_upload_chunk_session_id', 'upload_chunk', ['session_id'])
    op.create_index('idx_upload_chunk_session_index', 'upload_chunk', ['session_id', 'chunk_index'])
    op.create_index('idx_upload_chunk_received', 'upload_chunk', ['received'])
    op.create_index('idx_upload_chunk_verified', 'upload_chunk', ['verified'])
    
    # Create upload_progress_log table
    op.create_table(
        'upload_progress_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('progress_percentage', sa.Float(), nullable=False),
        sa.Column('bytes_uploaded', sa.Integer(), nullable=False),
        sa.Column('chunks_received', sa.Integer(), nullable=False),
        sa.Column('upload_speed_mbps', sa.Float(), nullable=True),
        sa.Column('estimated_time_remaining', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for upload_progress_log
    op.create_index('idx_upload_progress_session_id', 'upload_progress_log', ['session_id'])
    op.create_index('idx_upload_progress_timestamp', 'upload_progress_log', ['timestamp'])
    op.create_index('idx_upload_progress_event_type', 'upload_progress_log', ['event_type'])


def downgrade():
    """Drop upload session tables."""
    
    # Drop indexes
    op.drop_index('idx_upload_progress_event_type', 'upload_progress_log')
    op.drop_index('idx_upload_progress_timestamp', 'upload_progress_log')
    op.drop_index('idx_upload_progress_session_id', 'upload_progress_log')
    
    op.drop_index('idx_upload_chunk_verified', 'upload_chunk')
    op.drop_index('idx_upload_chunk_received', 'upload_chunk')
    op.drop_index('idx_upload_chunk_session_index', 'upload_chunk')
    op.drop_index('idx_upload_chunk_session_id', 'upload_chunk')
    
    op.drop_index('idx_upload_session_created_at', 'upload_session')
    op.drop_index('idx_upload_session_file_hash', 'upload_session')
    op.drop_index('idx_upload_session_expires_at', 'upload_session')
    op.drop_index('idx_upload_session_status', 'upload_session')
    op.drop_index('idx_upload_session_user_id', 'upload_session')
    op.drop_index('idx_upload_session_session_id', 'upload_session')
    
    # Drop tables
    op.drop_table('upload_progress_log')
    op.drop_table('upload_chunk')
    op.drop_table('upload_session')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS uploadsessionstatus")
