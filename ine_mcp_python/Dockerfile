FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema minimas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy configuration files
COPY pyproject.toml uv.lock ./

# Instalar dependencias (El paso peligroso para la RAM)
# Usamos --no-cache para intentar reducir el uso de disco/memoria temporal
RUN uv sync --frozen --no-cache

# Copiar el código
COPY ine_mcp ./ine_mcp/
COPY scripts ./scripts/

# Crear directorio de datos
RUN mkdir -p /app/data

# --- SOLUCIÓN A (Build on deploy con fallback robusto) ---
# Intentamos construir el índice durante el build.
# Si falla (por memoria o API), hacemos echo y continuamos (|| true).
# Esto asegura que el deploy NO falle, permitiendo depurar después.
RUN uv run python scripts/build_index.py || echo "⚠️ WARNING: Index build failed during deployment. Server will start in degraded mode."

# Exponer puerto
EXPOSE 8000

# Ejecutar servidor
CMD ["uv", "run", "python", "-m", "ine_mcp.server"]
