#!/bin/bash

# Ensure the database is initialized
echo "Initializing database..."
python3 init_db.py

# Start the FastAPI backend on port 3000 in the background
echo "Starting Backend Server (FastAPI) on port 3000..."
python3 server.py &

# Wait a moment for the backend to initialize
sleep 2

# Start the Proxy server on the Railway-assigned PORT (defaulting to 8080 if not set)
# The proxy will forward /api requests to localhost:3000
echo "Starting Proxy Server on port ${PORT:-8080}..."
python3 proxy_server.py
