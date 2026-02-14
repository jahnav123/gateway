#!/bin/bash
# Render deployment script

echo "🚀 Starting Gateway Application..."

# Initialize database
python3 init_db.py

# Start backend and proxy server
python3 server.py &
python3 proxy_server.py
