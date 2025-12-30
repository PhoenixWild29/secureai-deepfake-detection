#!/bin/bash
# SecureAI Guardian - Environment Setup Script
# This script creates the .env.local file with default configuration

echo "========================================"
echo "SecureAI Guardian - Environment Setup"
echo "========================================"
echo ""

if [ -f .env.local ]; then
    echo ".env.local already exists!"
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "Creating .env.local file..."
echo ""

cat > .env.local << 'EOF'
# SecureAI Guardian Environment Configuration
# This file contains your local environment variables
# DO NOT commit this file to version control (it's in .gitignore)

# Backend API URL
# For Flask: http://localhost:5000
# For FastAPI: http://localhost:8000
# Update this to match your backend server port
VITE_API_BASE_URL=http://localhost:5000

# Google Gemini API Key (for SecureSage AI consultant)
# Get your API key from: https://makersuite.google.com/app/apikey
# IMPORTANT: Replace 'your_actual_api_key_here' with your actual Gemini API key
GEMINI_API_KEY=your_actual_api_key_here

# WebSocket URL (optional, for real-time progress updates)
# For Flask: ws://localhost:5000/ws
# For FastAPI: ws://localhost:8000/ws
VITE_WS_URL=ws://localhost:5000/ws

# Environment
NODE_ENV=development
EOF

echo ".env.local created successfully!"
echo ""
echo "IMPORTANT: Edit .env.local and add your Gemini API key!"
echo ""
echo "Next steps:"
echo "1. Edit .env.local and replace 'your_actual_api_key_here' with your Gemini API key"
echo "2. Make sure your backend server is running (python api.py)"
echo "3. Run 'npm run dev' to start the frontend"
echo ""

