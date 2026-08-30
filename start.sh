#!/bin/bash
# News IQ - Start Python Service

cd "$(dirname "$0")/python_nodes"

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ../venv
fi

source ../venv/bin/activate

echo "Starting News IQ API Service on port 8001..."
uvicorn api_service:app --host 0.0.0.0 --port 8001 --reload

