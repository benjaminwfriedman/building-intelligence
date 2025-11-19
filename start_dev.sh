#!/bin/bash

# Start development servers for the Engineering Scene Graph system

echo "🚀 Starting Engineering Scene Graph Development Environment"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one from .env.example"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your API keys"
    exit 1
fi

# Start backend in background
echo "📡 Starting FastAPI backend (port 8000)..."
source .venv/bin/activate && python main.py &
BACKEND_PID=$!

# Give backend time to start
sleep 3

# Start frontend
echo "🎨 Starting React frontend (port 5173)..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Development servers started:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for Ctrl+C
trap 'echo ""; echo "🛑 Stopping servers..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT
wait