FROM python:3.11-slim

# System dependencies: gcc/g++ for numpy, libhdf5 for anndata/scanpy, curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ libhdf5-dev curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (maximizes layer caching)
# requirements.docker.txt excludes rpy2 (requires R on host; ambient_rna.py has graceful fallback)
COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy application source and tests
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml .

# Copy pre-cached showcase data (required for validation tests)
COPY data/showcase_scenarios/ ./data/showcase_scenarios/

# Copy hook scripts (needed if pre-commit is run inside container)
COPY scripts/ ./scripts/

# Ensure runtime directories exist
RUN mkdir -p data/db data/cache data/projects results

# Streamlit server on standard port 8501
EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
ENV STREAMLIT_SERVER_HEADLESS=true

# Health check: poll Streamlit's built-in health endpoint
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/app.py"]
