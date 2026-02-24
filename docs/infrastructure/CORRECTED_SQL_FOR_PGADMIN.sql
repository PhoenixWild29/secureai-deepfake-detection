-- Corrected SQL Commands for pgAdmin Query Tool
-- Run these commands in the Query Tool for secureai_db database
-- DO NOT include \c command - you're already connected!

-- Grant database privileges
GRANT ALL PRIVILEGES ON DATABASE secureai_db TO secureai;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO secureai;

-- Grant privileges on existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO secureai;

-- Grant privileges on existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO secureai;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO secureai;

-- Set default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO secureai;

