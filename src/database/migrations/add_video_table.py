#!/usr/bin/env python3
"""
Database Migration: Add Video Table
Creates the videos table for storing video metadata and analysis tracking
"""

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, DECIMAL, Boolean
from sqlalchemy.sql import func
from datetime import datetime, timezone


def upgrade(connection):
    """Create videos table"""
    
    # Create videos table
    videos_table = text("""
        CREATE TABLE IF NOT EXISTS videos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename VARCHAR(255) NOT NULL,
            file_hash VARCHAR(64) NOT NULL UNIQUE,
            file_size INTEGER NOT NULL CHECK (file_size >= 0),
            format VARCHAR(10) NOT NULL CHECK (format IN ('mp4', 'avi', 'mov', 'mkv', 'webm')),
            s3_key VARCHAR(512) NOT NULL UNIQUE,
            s3_bucket VARCHAR(128) NOT NULL,
            s3_url VARCHAR(512),
            user_id UUID NOT NULL,
            upload_session_id UUID,
            analysis_id UUID,
            status VARCHAR(20) NOT NULL DEFAULT 'uploading' CHECK (status IN ('uploading', 'uploaded', 'processing', 'analyzed', 'failed')),
            duration FLOAT,
            resolution VARCHAR(20),
            fps FLOAT,
            detection_result JSONB,
            confidence_score DECIMAL(5,4),
            is_fake BOOLEAN,
            processing_time FLOAT,
            error_message VARCHAR(1000),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            uploaded_at TIMESTAMP WITH TIME ZONE,
            analyzed_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB,
            dashboard_context JSONB
        )
    """)
    
    connection.execute(videos_table)
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_videos_filename ON videos(filename)",
        "CREATE INDEX IF NOT EXISTS idx_videos_file_hash ON videos(file_hash)",
        "CREATE INDEX IF NOT EXISTS idx_videos_s3_key ON videos(s3_key)",
        "CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_videos_upload_session_id ON videos(upload_session_id)",
        "CREATE INDEX IF NOT EXISTS idx_videos_analysis_id ON videos(analysis_id)",
        "CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)",
        "CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_videos_user_status ON videos(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_videos_format ON videos(format)"
    ]
    
    for index_sql in indexes:
        connection.execute(text(index_sql))
    
    # Add foreign key constraint to users table (if it exists)
    try:
        fk_constraint = text("""
            ALTER TABLE videos 
            ADD CONSTRAINT fk_videos_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        """)
        connection.execute(fk_constraint)
    except Exception as e:
        # Users table might not exist yet, skip foreign key constraint
        print(f"Warning: Could not add foreign key constraint: {e}")
    
    # Create trigger for updated_at
    trigger_sql = text("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_videos_updated_at ON videos;
        CREATE TRIGGER update_videos_updated_at
            BEFORE UPDATE ON videos
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    connection.execute(trigger_sql)


def downgrade(connection):
    """Drop videos table"""
    connection.execute(text("DROP TABLE IF EXISTS videos CASCADE"))
    connection.execute(text("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE"))


if __name__ == "__main__":
    # For testing the migration
    from sqlalchemy import create_engine
    
    # Example usage
    engine = create_engine("postgresql://user:password@localhost/dbname")
    with engine.connect() as conn:
        upgrade(conn)
        conn.commit()
