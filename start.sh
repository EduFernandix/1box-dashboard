#!/bin/bash
# 1BOX Dashboard — Start everything with one command
# Usage: ./start.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "🟢 Starting 1BOX Dashboard..."

# Kill any previous instances
pkill -f "uvicorn app:app" 2>/dev/null || true
pkill -f "dev-server.js" 2>/dev/null || true
sleep 1

# Start backend
echo "   Starting backend (port 8000)..."
cd "$DIR/backend"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd "$DIR"

# Wait for backend to be ready
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   Backend ready"
        break
    fi
    sleep 1
done

# Start frontend + proxy
echo "   Starting frontend (port 3000)..."
node dev-server.js &
FRONTEND_PID=$!
sleep 1

echo ""
echo "✅ Dashboard running at: http://localhost:3000"
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "   Press Ctrl+C to stop"

# Open browser
open "http://localhost:3000" 2>/dev/null || true

# Wait and cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo 'Stopped.'" EXIT
wait
