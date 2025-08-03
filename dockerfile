# Use Python 3.11 slim base image (more recent, fewer vulnerabilities)
FROM python:3.11-slim-bookworm

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Update system packages and install security updates
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    ca-certificates \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .

# Upgrade pip and install dependencies with security flags
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade -r requirements.txt && \
    pip check

# Copy application code
COPY backend ./backend
COPY frontend ./frontend

# Create necessary directories and set proper permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 700 /app/logs /app/tmp

# Set environment variables
ENV PYTHONPATH=/app \
    BACKEND_URL=http://localhost:8000 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Remove potentially vulnerable files
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Create startup script
COPY start.sh /app/start.sh

# Make the startup script executable and secure
RUN chmod 755 /app/start.sh && \
    chown appuser:appuser /app/start.sh

# Expose ports for FastAPI (backend) and Streamlit (frontend)
EXPOSE 8000
EXPOSE 8501


# Switch to non-root user for security
USER appuser
# Set secure working directory
WORKDIR /app

# Run the startup script
CMD ["/app/start.sh"]