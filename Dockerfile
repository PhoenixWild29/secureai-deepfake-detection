# SecureAI DeepFake Detection - Production Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    ffmpeg \
    curl \
    libopencv-dev \
    python3-opencv \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with error handling for optional packages
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch torchvision || echo "PyTorch install issue" && \
    pip install --no-cache-dir tensorflow || echo "TensorFlow install issue (optional for MTCNN)" && \
    pip install --no-cache-dir -r requirements.txt || echo "Some requirements failed" && \
    pip install --no-cache-dir gunicorn gevent

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads results logs run && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
# Use gunicorn with config file for proper logging
CMD ["gunicorn", "--config", "gunicorn_config.py", "api:app"]