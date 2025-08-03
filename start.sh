#!/bin/bash
set -euo pipefail

# Function to handle shutdown gracefully
cleanup() {
    echo "Received shutdown signal, cleaning up..."
    if [ ! -z "${BACKEND_PID:-}" ]; then
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ ! -z "${FRONTEND_PID:-}" ]; then
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi
    
    # Wait for processes to terminate gracefully
    sleep 2
    
    # Force kill if still running
    if [ ! -z "${BACKEND_PID:-}" ]; then
        kill -KILL "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ ! -z "${FRONTEND_PID:-}" ]; then
        kill -KILL "$FRONTEND_PID" 2>/dev/null || true
    fi
    
    echo "Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Validate required directories exist
if [ ! -d "/app/backend" ] || [ ! -d "/app/frontend" ]; then
    echo "Error: Required directories not found"
    exit 1
fi

# Start FastAPI backend with security headers and proper configuration
echo "Starting FastAPI backend..."
cd /app/backend
python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --access-log \
    --use-colors \
    --server-header \
    --date-header &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -f -s --max-time 2 http://localhost:8000/docs >/dev/null 2>&1; then
        echo "Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Backend failed to start within timeout"
        cleanup
        exit 1
    fi
    sleep 1
done

# Start Streamlit frontend with security configuration
echo "Starting Streamlit frontend..."
cd /app/frontend
streamlit run app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection true \
    --server.maxUploadSize 10 \
    --browser.gatherUsageStats false &
FRONTEND_PID=$!

echo "Both services started successfully"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Keep the script running and monitor child processes
while true; do
    # Check if backend is still running
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Backend process died unexpectedly"
        cleanup
        exit 1
    fi
    
    # Check if frontend is still running
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Frontend process died unexpectedly"
        cleanup
        exit 1
    fi
    
    sleep 10
done