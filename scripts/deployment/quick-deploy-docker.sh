#!/bin/bash
# Quick Docker Deployment Script for SecureAI
# This script automates the quick deployment process

set -e

echo "🚀 SecureAI Quick Docker Deployment"
echo "===================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "Please install Docker Compose first"
    exit 1
fi

# Use docker compose (newer) or docker-compose (older)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Step 1: Build Frontend
echo "📦 Step 1: Building frontend..."
if [ ! -d "secureai-guardian" ]; then
    echo "❌ secureai-guardian directory not found!"
    exit 1
fi

cd secureai-guardian
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi

echo "Building frontend..."
npm run build
cd ..
echo "✅ Frontend built successfully"
echo ""

# Step 2: Create .env file if it doesn't exist
echo "⚙️  Step 2: Setting up environment..."
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        # Create minimal .env file
        cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
FLASK_ENV=production
DATABASE_URL=postgresql://secureai:SecureAI2024!DB@postgres:5432/secureai_db
REDIS_URL=redis://redis:6379/0
USE_LOCAL_STORAGE=true
CORS_ORIGINS=http://localhost:8000,http://localhost:3000
EOF
    fi
    echo "✅ .env file created"
    echo "⚠️  Please review and update .env file with your settings"
else
    echo "✅ .env file already exists"
fi
echo ""

# Step 3: Generate secret key if not set
if ! grep -q "SECRET_KEY=" .env || grep -q "SECRET_KEY=change-this" .env; then
    echo "Generating secure SECRET_KEY..."
    SECRET_KEY=$(openssl rand -hex 32)
    if grep -q "SECRET_KEY=" .env; then
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    else
        echo "SECRET_KEY=$SECRET_KEY" >> .env
    fi
    echo "✅ SECRET_KEY generated"
fi
echo ""

# Step 4: Deploy with Docker Compose
echo "🐳 Step 3: Deploying with Docker Compose..."
echo "This may take a few minutes on first run..."
echo ""

$DOCKER_COMPOSE -f docker-compose.quick.yml up -d --build

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Step 5: Check service status
echo ""
echo "📊 Step 4: Checking service status..."
$DOCKER_COMPOSE -f docker-compose.quick.yml ps

echo ""
echo "🔍 Checking health endpoint..."
sleep 5

# Try health check
if curl -f http://localhost:8000/api/health &> /dev/null; then
    echo "✅ Health check passed!"
    curl http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || curl http://localhost:8000/api/health
else
    echo "⚠️  Health check failed, but services may still be starting..."
    echo "Check logs with: $DOCKER_COMPOSE -f docker-compose.quick.yml logs -f"
fi

echo ""
echo "===================================="
echo "✅ Deployment Complete!"
echo "===================================="
echo ""
echo "Your app is running at:"
echo "  🌐 Backend API: http://localhost:8000"
echo "  ❤️  Health Check: http://localhost:8000/api/health"
echo ""
echo "Useful commands:"
echo "  View logs:     $DOCKER_COMPOSE -f docker-compose.quick.yml logs -f"
echo "  Stop services: $DOCKER_COMPOSE -f docker-compose.quick.yml down"
echo "  Restart:       $DOCKER_COMPOSE -f docker-compose.quick.yml restart"
echo "  Status:        $DOCKER_COMPOSE -f docker-compose.quick.yml ps"
echo ""
echo "Next steps:"
echo "  1. Configure firewall: sudo ufw allow 8000/tcp"
echo "  2. Set up domain (optional)"
echo "  3. Configure SSL (optional)"
echo ""

