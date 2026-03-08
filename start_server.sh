#!/bin/bash
# Railway/Render deployment script

echo "🚀 Starting Gateway Application..."

# Initialize database
python3 init_db_postgres.py

# Start backend on internal port 3000
echo "Starting backend server..."
python3 server.py &

# Wait for backend to be ready
sleep 2

# Start proxy server on the public $PORT
echo "Starting proxy server on port ${PORT:-8080}..."
python3 proxy_server.py
