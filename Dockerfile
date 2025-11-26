FROM python:3.11-slim

# Hugging Face Spaces deployment - Version 2.0 with get_table_data tool
# Hugging Face Spaces requirements:
# - Run as user 1000 (security)
# - Use port 7860 (standard)
# - Write permissions on data directories

# Set working directory
WORKDIR /app

# Copy application code and dependencies from ine_mcp_python subdirectory
COPY ine_mcp_python/pyproject.toml ine_mcp_python/uv.lock* ./
COPY ine_mcp_python/ine_mcp ./ine_mcp
COPY ine_mcp_python/scripts ./scripts

# Install dependencies as ROOT (before switching to user)
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

# Create non-root user for HF Spaces
RUN useradd -m -u 1000 user && \
    chown -R user:user /app

# Create data directory with write permissions for user
RUN mkdir -p /app/data && chown -R user:user /app/data

# NOW switch to non-root user
USER user

# Environment setup
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    INDEX_DIR=/app/data

# Expose Hugging Face standard port
EXPOSE 7860

# Run FastAPI server with Uvicorn
CMD ["python", "-m", "uvicorn", "ine_mcp.server:app", "--host", "0.0.0.0", "--port", "7860", "--log-level", "info"]
