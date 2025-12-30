#!/bin/bash
# SecureAI Guardian - Start Servers Script
# This script helps you start both backend and frontend servers

echo "========================================"
echo "SecureAI Guardian - Server Startup"
echo "========================================"
echo ""

echo "[1/2] Starting Backend Server..."
echo ""
echo "Backend will run on: http://localhost:5000"
echo ""

# Start backend in background
cd ..
python api.py &
BACKEND_PID=$!

sleep 3

echo ""
echo "[2/2] Starting Frontend Server..."
echo ""
echo "Frontend will run on: http://localhost:3000"
echo ""

# Start frontend
cd secureai-guardian
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo "Both servers are starting!"
echo "========================================"
echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

