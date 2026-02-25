"""Add composite index on (result_id, frame_number) to FrameAnalysis table

Revision ID: add_frame_analysis_composite_index
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_frame_analysis_composite_index'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Add composite index on (result_id, frame_number) to FrameAnalysis table.
    
    This index optimizes database queries for efficient frame-by-frame navigation
    and confidence score retrieval during real-time processing.
    """
    # Create composite index on (result_id, frame_number)
    op.create_index(
        'idx_frame_analysis_result_frame_composite',
        'frame_analysis',
        ['result_id', 'frame_number'],
        unique=False,
        postgresql_concurrently=True  # Use concurrent index creation for production
    )
    
    # Create additional performance index on confidence_score for filtering
    op.create_index(
        'idx_frame_analysis_confidence_score',
        'frame_analysis',
        ['confidence_score'],
        unique=False,
        postgresql_concurrently=True
    )
    
    # Create index on processing_time_ms for performance monitoring
    op.create_index(
        'idx_frame_analysis_processing_time',
        'frame_analysis',
        ['processing_time_ms'],
        unique=False,
        postgresql_concurrently=True
    )


def downgrade():
    """
    Remove the composite index and related performance indexes.
    """
    # Drop indexes in reverse order
    op.drop_index('idx_frame_analysis_processing_time', table_name='frame_analysis')
    op.drop_index('idx_frame_analysis_confidence_score', table_name='frame_analysis')
    op.drop_index('idx_frame_analysis_result_frame_composite', table_name='frame_analysis')
