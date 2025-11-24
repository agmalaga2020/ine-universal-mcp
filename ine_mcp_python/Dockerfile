FROM python:3.11-slim

# Hugging Face Spaces requirements:
# - Run as user 1000 (security)
# - Use port 7860 (standard)
# - Write permissions on data directories

# Create non-root user for HF Spaces
RUN useradd -m -u 1000 user
USER user

# Environment setup
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Copy dependency files (leverage Docker cache)
COPY --chown=user pyproject.toml uv.lock* ./

# Install uv and dependencies
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -e .

# Copy application code
COPY --chown=user ine_mcp ./ine_mcp
COPY --chown=user scripts ./scripts

# Create data directory with write permissions
RUN mkdir -p data

# Build FAISS index during Docker build
# HF Spaces has 16GB RAM - this will work!
RUN python scripts/build_index.py || echo "⚠️  Index build failed, will retry at runtime"

# Expose Hugging Face standard port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:7860/health', timeout=5)" || exit 1

# Run FastAPI server with Uvicorn
CMD ["python", "-m", "uvicorn", "ine_mcp.server:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
