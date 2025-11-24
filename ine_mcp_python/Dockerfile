FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema minimas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copiar TODO el código PRIMERO (necesario para -e . install)
COPY pyproject.toml ./
COPY ine_mcp ./ine_mcp/
COPY scripts ./scripts/

# Instalar el paquete con sus dependencias
# -e . = editable install desde directorio actual
# --system = instalar en Python del sistema (no venv)
# --no-cache = reducir uso de memoria
RUN uv pip install --system --no-cache -e .

# Crear directorio de datos
RUN mkdir -p /app/data

# Intentar construir índice FAISS durante build
# Si falla (OOM/API down), continuar sin romper el deploy
RUN python scripts/build_index.py || echo "⚠️ WARNING: Index build failed. Server will start in degraded mode."

# Exponer puerto
EXPOSE 8000

# Ejecutar servidor (sin uv run, ya instalamos system-wide)
CMD ["python", "-m", "ine_mcp.server"]
