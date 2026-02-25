#!/bin/bash
# Database Setup Script for SecureAI Guardian
# Sets up PostgreSQL database and runs migrations

set -e

echo "🗄️  SecureAI Guardian Database Setup"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Installing PostgreSQL...${NC}"
apt-get update
apt-get install -y postgresql postgresql-contrib python3-psycopg2

echo ""
echo -e "${YELLOW}Step 2: Setting up database and user...${NC}"

# Get database credentials
read -p "Enter database name (default: secureai_db): " DB_NAME
DB_NAME=${DB_NAME:-secureai_db}

read -p "Enter database user (default: secureai): " DB_USER
DB_USER=${DB_USER:-secureai}

read -sp "Enter database password: " DB_PASSWORD
echo ""

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE ${DB_NAME};
CREATE USER ${DB_USER} WITH ENCRYPTED PASSWORD '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
EOF

echo ""
echo -e "${YELLOW}Step 3: Installing Python dependencies...${NC}"
pip3 install sqlalchemy psycopg2-binary alembic

echo ""
echo -e "${YELLOW}Step 4: Setting up environment variable...${NC}"
echo "Add this to your .env file:"
echo "DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"

echo ""
echo -e "${GREEN}✅ Database setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Add DATABASE_URL to your .env file"
echo "2. Run: python database/migrate_from_files.py (to migrate existing data)"
echo "3. Update api.py to use database instead of file storage"
echo ""

