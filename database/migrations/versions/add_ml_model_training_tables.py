#!/usr/bin/env python3
"""
Database Migration: Add ML Model Training Tables
Alembic migration script to create ML model training related tables
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers
revision = 'add_ml_model_training_tables'
down_revision = 'add_frame_analysis_composite_index'  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Create ML model training tables."""
    
    # Create training_jobs table
    op.create_table(
        'training_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_name', sa.String(255), nullable=False, index=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True, index=True),
        sa.Column('model_type', sa.Enum('ensemble', 'resnet50', 'clip', 'custom', name='modeltype'), nullable=False),
        sa.Column('dataset_path', sa.String(500), nullable=False),
        sa.Column('hyperparameters', sa.Text, nullable=True),
        sa.Column('validation_threshold', sa.Float, nullable=False, default=0.95),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='trainingstatus'), nullable=False, default='pending'),
        sa.Column('progress_percentage', sa.Float, nullable=True),
        sa.Column('current_stage', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_traceback', sa.Text, nullable=True),
        sa.Column('cpu_usage_percent', sa.Float, nullable=True),
        sa.Column('memory_usage_mb', sa.Float, nullable=True),
        sa.Column('gpu_usage_percent', sa.Float, nullable=True),
        sa.Column('gpu_memory_usage_mb', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
    )
    
    # Create ml_model_versions table
    op.create_table(
        'ml_model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('model_name', sa.String(255), nullable=False, index=True),
        sa.Column('version', sa.String(50), nullable=False, index=True),
        sa.Column('model_type', sa.Enum('ensemble', 'resnet50', 'clip', 'custom', name='modeltype'), nullable=False),
        sa.Column('mlflow_run_id', sa.String(255), nullable=True, index=True),
        sa.Column('mlflow_model_uri', sa.String(500), nullable=True),
        sa.Column('artifact_uri', sa.String(500), nullable=True),
        sa.Column('training_data_s3_path', sa.String(500), nullable=False),
        sa.Column('training_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('hyperparameters', sa.Text, nullable=True),
        sa.Column('auc_score', sa.Float, nullable=True),
        sa.Column('accuracy', sa.Float, nullable=True),
        sa.Column('precision', sa.Float, nullable=True),
        sa.Column('recall', sa.Float, nullable=True),
        sa.Column('f1_score', sa.Float, nullable=True),
        sa.Column('validation_threshold', sa.Float, nullable=True),
        sa.Column('status', sa.Enum('training', 'trained', 'validated', 'deployed', 'failed', 'archived', name='modelstatus'), nullable=False, default='training'),
        sa.Column('is_deployed', sa.Boolean, nullable=False, default=False),
        sa.Column('deployment_stage', sa.String(50), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['training_job_id'], ['training_jobs.id'], ondelete='SET NULL'),
    )
    
    # Create model_metrics table
    op.create_table(
        'model_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('model_version_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('metric_name', sa.String(100), nullable=False, index=True),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('dataset_split', sa.String(50), nullable=True),
        sa.Column('evaluation_timestamp', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('metadata', sa.Text, nullable=True),
        sa.ForeignKeyConstraint(['model_version_id'], ['ml_model_versions.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_training_jobs_status', 'training_jobs', ['status'])
    op.create_index('idx_training_jobs_model_type', 'training_jobs', ['model_type'])
    op.create_index('idx_training_jobs_created_at', 'training_jobs', ['created_at'])
    
    op.create_index('idx_ml_model_versions_model_name_version', 'ml_model_versions', ['model_name', 'version'], unique=True)
    op.create_index('idx_ml_model_versions_status', 'ml_model_versions', ['status'])
    op.create_index('idx_ml_model_versions_model_type', 'ml_model_versions', ['model_type'])
    op.create_index('idx_ml_model_versions_is_deployed', 'ml_model_versions', ['is_deployed'])
    op.create_index('idx_ml_model_versions_created_at', 'ml_model_versions', ['created_at'])
    
    op.create_index('idx_model_metrics_model_version_id', 'model_metrics', ['model_version_id'])
    op.create_index('idx_model_metrics_metric_name', 'model_metrics', ['metric_name'])
    op.create_index('idx_model_metrics_metric_type', 'model_metrics', ['metric_type'])
    op.create_index('idx_model_metrics_evaluation_timestamp', 'model_metrics', ['evaluation_timestamp'])


def downgrade():
    """Drop ML model training tables."""
    
    # Drop indexes first
    op.drop_index('idx_model_metrics_evaluation_timestamp', 'model_metrics')
    op.drop_index('idx_model_metrics_metric_type', 'model_metrics')
    op.drop_index('idx_model_metrics_metric_name', 'model_metrics')
    op.drop_index('idx_model_metrics_model_version_id', 'model_metrics')
    
    op.drop_index('idx_ml_model_versions_created_at', 'ml_model_versions')
    op.drop_index('idx_ml_model_versions_is_deployed', 'ml_model_versions')
    op.drop_index('idx_ml_model_versions_model_type', 'ml_model_versions')
    op.drop_index('idx_ml_model_versions_status', 'ml_model_versions')
    op.drop_index('idx_ml_model_versions_model_name_version', 'ml_model_versions')
    
    op.drop_index('idx_training_jobs_created_at', 'training_jobs')
    op.drop_index('idx_training_jobs_model_type', 'training_jobs')
    op.drop_index('idx_training_jobs_status', 'training_jobs')
    
    # Drop tables
    op.drop_table('model_metrics')
    op.drop_table('ml_model_versions')
    op.drop_table('training_jobs')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS modelstatus')
    op.execute('DROP TYPE IF EXISTS trainingstatus')
    op.execute('DROP TYPE IF EXISTS modeltype')
