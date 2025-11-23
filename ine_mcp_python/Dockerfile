FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema minimas
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copiar SOLO los archivos de configuración primero (aprovecha cache de Docker)
COPY pyproject.toml ./

# Instalar dependencias (El paso peligroso para la RAM)
# Usamos uv pip install en lugar de uv sync (más apropiado para Docker)
RUN uv pip install --system --no-cache -e .

# Ahora copiar el código fuente
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
CMD ["python", "-m", "ine_mcp.server"]
