-- Initialize Database Schema for SecureAI Guardian
-- Run this in pgAdmin Query Tool for secureai_db database

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Create analyses table
CREATE TABLE IF NOT EXISTS analyses (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    filename VARCHAR(500) NOT NULL,
    source_url VARCHAR(1000),
    file_path VARCHAR(1000),
    s3_key VARCHAR(1000),
    is_fake BOOLEAN NOT NULL,
    confidence FLOAT NOT NULL,
    fake_probability FLOAT NOT NULL,
    authenticity_score FLOAT,
    verdict VARCHAR(50) NOT NULL,
    forensic_metrics JSONB,
    spatial_entropy_heatmap JSONB,
    blockchain_tx VARCHAR(255),
    blockchain_network VARCHAR(50),
    blockchain_timestamp TIMESTAMP,
    video_hash VARCHAR(64),
    file_size INTEGER,
    duration FLOAT,
    model_type VARCHAR(50),
    processing_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_is_fake ON analyses(is_fake);
CREATE INDEX IF NOT EXISTS idx_analyses_verdict ON analyses(verdict);
CREATE INDEX IF NOT EXISTS idx_analyses_blockchain_tx ON analyses(blockchain_tx);
CREATE INDEX IF NOT EXISTS idx_analyses_video_hash ON analyses(video_hash);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_user_created ON analyses(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_verdict_created ON analyses(verdict, created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_fake_prob ON analyses(fake_probability);

-- Create processing_stats table
CREATE TABLE IF NOT EXISTS processing_stats (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP UNIQUE NOT NULL,
    total_analyses INTEGER DEFAULT 0 NOT NULL,
    fake_detected INTEGER DEFAULT 0 NOT NULL,
    authentic_detected INTEGER DEFAULT 0 NOT NULL,
    blockchain_proofs INTEGER DEFAULT 0 NOT NULL,
    avg_processing_time FLOAT,
    avg_confidence FLOAT,
    authenticity_percentage FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_processing_stats_date ON processing_stats(date);

-- Grant permissions to secureai user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;

-- Success message
SELECT 'Database schema initialized successfully!' AS status;

