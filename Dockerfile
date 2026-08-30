FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY python_nodes/ ./python_nodes/
COPY config/ ./config/

# Set working directory to where the API service lives
WORKDIR /app/python_nodes

# Expose port
EXPOSE 8001

# Start the service
CMD ["uvicorn", "api_service:app", "--host", "0.0.0.0", "--port", "8001"]

