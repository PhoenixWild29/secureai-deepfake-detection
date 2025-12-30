# Database Migration: Initial Schema
# Run with: alembic upgrade head

"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])

    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('file_path', sa.String(1000), nullable=True),
        sa.Column('s3_key', sa.String(1000), nullable=True),
        sa.Column('is_fake', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('fake_probability', sa.Float(), nullable=False),
        sa.Column('authenticity_score', sa.Float(), nullable=True),
        sa.Column('verdict', sa.String(50), nullable=False),
        sa.Column('forensic_metrics', postgresql.JSON, nullable=True),
        sa.Column('spatial_entropy_heatmap', postgresql.JSON, nullable=True),
        sa.Column('blockchain_tx', sa.String(255), nullable=True),
        sa.Column('blockchain_network', sa.String(50), nullable=True),
        sa.Column('blockchain_timestamp', sa.DateTime(), nullable=True),
        sa.Column('video_hash', sa.String(64), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('model_type', sa.String(50), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_analyses_user_id', 'analyses', ['user_id'])
    op.create_index('ix_analyses_is_fake', 'analyses', ['is_fake'])
    op.create_index('ix_analyses_verdict', 'analyses', ['verdict'])
    op.create_index('ix_analyses_blockchain_tx', 'analyses', ['blockchain_tx'])
    op.create_index('ix_analyses_video_hash', 'analyses', ['video_hash'])
    op.create_index('ix_analyses_created_at', 'analyses', ['created_at'])
    op.create_index('idx_analyses_user_created', 'analyses', ['user_id', 'created_at'])
    op.create_index('idx_analyses_verdict_created', 'analyses', ['verdict', 'created_at'])
    op.create_index('idx_analyses_fake_prob', 'analyses', ['fake_probability'])

    # Create processing_stats table
    op.create_table(
        'processing_stats',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('date', sa.DateTime(), nullable=False, unique=True),
        sa.Column('total_analyses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('fake_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('authentic_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('blockchain_proofs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_processing_time', sa.Float(), nullable=True),
        sa.Column('avg_confidence', sa.Float(), nullable=True),
        sa.Column('authenticity_percentage', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_processing_stats_date', 'processing_stats', ['date'])


def downgrade():
    op.drop_table('processing_stats')
    op.drop_table('analyses')
    op.drop_table('users')

