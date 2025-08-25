FROM python:3.11-slim

WORKDIR /app

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

# Create a script to check for documents at startup
RUN echo '#!/bin/bash\n\
    if [ -z "$(ls -A /app/documents 2>/dev/null)" ]; then\n\
    echo "Warning: No documents found in /app/documents"\n\
    echo "Please mount your PDF documents to /app/documents"\n\
    echo "Starting server with empty document store..."\n\
    else\n\
    echo "Found documents in /app/documents:"\n\
    ls -la /app/documents\n\
    fi\n\
    exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Set environment variables
ENV DOCUMENTS_DIR=/app/documents
ENV CHROMA_PERSIST_DIR=/app/chroma_db
ENV PYTHONPATH=/app

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Health check using the dedicated endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]