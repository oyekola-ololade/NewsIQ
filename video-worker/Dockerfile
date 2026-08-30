# News IQ Video Worker
# Python 3.11 + FFmpeg + DejaVu fonts

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fontconfig \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Rebuild font cache
RUN fc-cache -fv

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

