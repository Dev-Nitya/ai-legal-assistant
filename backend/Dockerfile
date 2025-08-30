FROM python:3.11-slim

WORKDIR /app

# Keep Python logs unbuffered for CloudWatch
ENV PYTHONUNBUFFERED=1

# Disable chroma telemetry (avoids posthog capture signature errors)
ENV CHROMA_TELEMETRY=false
# Local defaults (can be overridden by ECS task definition)
ENV CHROMA_PERSIST_DIR=/app/chroma_db
ENV DOCUMENTS_DIR=/app/docs

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories
RUN mkdir -p /app/chroma_db /app/docs /app/logs

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check using the dedicated endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]