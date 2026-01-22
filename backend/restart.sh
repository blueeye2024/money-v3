#!/bin/bash

PORT=9100
PID_FILE="gunicorn.pid"

echo "🔄 Backend Restart Initiated..."

# 1. Kill existing process by Port
PID=$(lsof -t -i:$PORT)
if [ -n "$PID" ]; then
    echo "⚠️  Found process $PID on port $PORT. Killing..."
    kill -15 $PID
    
    # Wait loop
    for i in {1..10}; do
        if kill -0 $PID 2>/dev/null; then
            echo "   Waiting for shutdown... ($i)"
            sleep 1
        else
            echo "✅ Process stopped."
            break
        fi
    done
    
    # Force kill if still alive
    if kill -0 $PID 2>/dev/null; then
        echo "🚨 Process frozen. Force killing..."
        kill -9 $PID
    fi
fi

# 2. Kill by name (cleanup zombies)
pkill -f "gunicorn.*main:app.*9100"
sleep 1

# 3. Start New Process
echo "🚀 Starting Gunicorn on Port $PORT..."
nohup /home/blue/blue/my_project/money/backend/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT --workers 2 > backend.log 2>&1 &

NEW_PID=$!
echo $NEW_PID > $PID_FILE
echo "✅ Server started with PID $NEW_PID"

# 4. Verification
sleep 3
if ps -p $NEW_PID > /dev/null; then
    echo "🎉 Health Check Passed. Backend is Running."
else
    echo "❌ Server failed to start. Check backend.log"
    tail -n 10 backend.log
fi
