# SecureAI DeepFake Detection - Production Dockerfile

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
# Force CPU mode (disable CUDA) for CPU-only servers
ENV CUDA_VISIBLE_DEVICES=""
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV TF_FORCE_GPU_ALLOW_GROWTH=false
ENV TF_ENABLE_ONEDNN_OPTS=0

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
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn gevent && \
    pip install --no-cache-dir solana solders base58 && \
    python -c "import solana; import solders; print('Solana packages verified')" || echo "Solana packages verification failed" && \
    pip install --no-cache-dir git+https://github.com/NVIDIA/aistore.git || echo "AIStore install failed (optional - will use S3/local storage)"

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p uploads results logs run test_videos && \
    chmod 755 uploads results logs run test_videos && \
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