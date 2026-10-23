# ContextGuard — Production Container
# Multi-stage: install deps first (cached layer), then copy source
FROM python:3.11-slim

WORKDIR /app

# Install system-level build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer — only invalidated when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create persistent data directory
RUN mkdir -p /app/data

# Environment defaults (overridden at runtime)
ENV PORT=5000
ENV DATABASE_TYPE=duckdb
ENV LLM_PROVIDER=mock
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (Render and Railway respect this)
EXPOSE $PORT

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch with Waitress production WSGI server (multi-threaded, no GIL issues)
CMD ["python", "wsgi.py"]
