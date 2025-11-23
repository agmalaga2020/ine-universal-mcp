FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml ./
COPY ine_mcp ./ine_mcp/
COPY scripts ./scripts/

# Install dependencies
RUN uv sync --frozen

# Copy pre-built FAISS index (55MB)
# This includes faiss_index.bin, series_metadata.pkl, and winning_series.json
COPY data ./data/

# Expose port for health check (if needed)
EXPOSE 8000

# Default command (can be overridden)
CMD ["uv", "run", "python", "-m", "ine_mcp.server"]
