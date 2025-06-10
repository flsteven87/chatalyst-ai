FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest version and suppress root user warning
RUN pip install --upgrade pip --root-user-action=ignore

# Create a non-root user for security (optional, can run as root if needed)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with root user action suppressed
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
# Make directories world-writable to handle both root and non-root execution
RUN mkdir -p /app/data /app/logs /app/data/vanna_embeddings && \
    chmod -R 777 /app/data /app/logs

# Expose Streamlit port
EXPOSE 8501

# Health check for Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Default command - run Streamlit (will use user specified in docker-compose)
CMD ["streamlit", "run", "ui/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"] 