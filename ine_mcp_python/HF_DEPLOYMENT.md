# 🚀 Hugging Face Spaces Deployment Guide

Este MCP server está optimizado para **Hugging Face Spaces** con 16GB RAM.

## ✅ Pre-requisitos

- Cuenta en [Hugging Face](https://huggingface.co) (gratis)
- Código ya migrado a FastAPI + SSE ✓
- Dockerfile optimizado para HF ✓

## 📋 Paso a Paso

### 1. Crear Space en Hugging Face

1. Ve a https://huggingface.co/spaces
2. Click en **"Create new Space"**
3. Configura:
   - **Name**: `ine-universal-mcp`
   - **License**: MIT
   - **SDK**: **Docker** ⚠️ (CRÍTICO - no Python, no Gradio)
   - **Hardware**: CPU básico (gratis)
   - **Visibility**: Public

### 2. Conectar con GitHub (Opción Recomendada)

```bash
# En tu repo local
git remote add hf https://huggingface.co/spaces/TU_USERNAME/ine-universal-mcp
git push hf claude/add-spanish-readme-01MWYAuzyoZFXDS9JxYgymWb:main
```

**O usar GitHub Actions** (auto-sync):
```yaml
# .github/workflows/deploy-hf.yml
name: Deploy to HF Spaces
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Push to HF
        run: |
          git push --force https://USER:${{secrets.HF_TOKEN}}@huggingface.co/spaces/USER/ine-universal-mcp main
```

### 3. Configurar Variables de Entorno (Opcional)

En el Space settings:
```bash
REDIS_URL=         # Opcional (usa in-memory fallback)
LOG_LEVEL=info
INDEX_DIR=/home/user/app/data
PORT=7860          # HF Spaces standard
```

### 4. Verificar Deployment

El build tardará **15-20 minutos** porque construye el índice FAISS:

```
✓ Installing uv
✓ Installing dependencies (fastembed, pandas, faiss, etc.)
✓ Building FAISS index from INE API (~10 min)
✓ Starting Uvicorn server on port 7860
```

**Logs esperados**:
```
INFO:     INE MCP Server - Starting up
INFO:     ✓ Cache initialized
INFO:     ✓ Semantic search ready: 34336 series indexed
INFO:     INE MCP Server - Ready to accept connections
INFO:     Uvicorn running on http://0.0.0.0:7860
```

### 5. Probar el Servidor

#### Health Check
```bash
curl https://TU_USERNAME-ine-universal-mcp.hf.space/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "service": "INE MCP Server",
  "version": "2.0.0",
  "components": {
    "cache": "ready",
    "search": "ready",
    "aggregator": "ready"
  }
}
```

#### Root Endpoint (Docs)
```bash
curl https://TU_USERNAME-ine-universal-mcp.hf.space/
```

#### Conectar desde Claude Desktop

Añade a tu `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ine-api": {
      "url": "https://TU_USERNAME-ine-universal-mcp.hf.space/sse"
    }
  }
}
```

---

## 🐛 Troubleshooting

### Build falla en "Building FAISS index"

**Síntoma**: Build timeout después de 1 hora.

**Causa**: La API del INE está caída o muy lenta.

**Solución**:
1. El fallback `|| echo "warning"` permite que el build continue
2. El servidor arranca sin índice (usa keyword search)
3. Puedes rebuildar manualmente después:
   ```bash
   # Desde el Space Terminal
   python scripts/build_index.py
   ```

### "No module named 'uvicorn'"

**Causa**: uv.lock desincronizado con pyproject.toml

**Solución**:
```bash
# Local
uv lock
git add uv.lock
git commit -m "Update lockfile"
git push hf
```

### Puerto 7860 no responde

**Causa**: CMD en Dockerfile usa puerto incorrecto.

**Fix** (ya aplicado):
```dockerfile
CMD ["python", "-m", "uvicorn", "ine_mcp.server:app", "--host", "0.0.0.0", "--port", "7860"]
```

### "Permission denied" en /app/data

**Causa**: USER 1000 no tiene permisos de escritura.

**Fix** (ya aplicado):
```dockerfile
COPY --chown=user ...
RUN mkdir -p data
```

---

## 🔄 CI/CD (Auto-deploy desde GitHub)

**Paso 1**: Obtén tu HF Token
- Ve a https://huggingface.co/settings/tokens
- Crea token con scope `write`

**Paso 2**: Añade secret en GitHub
- Repo → Settings → Secrets → New repository secret
- Name: `HF_TOKEN`
- Value: `hf_xxxxx...`

**Paso 3**: Crea workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy to Hugging Face
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          lfs: true

      - name: Push to Hugging Face Spaces
        env:
          HF_USERNAME: TU_USERNAME
          HF_SPACE: ine-universal-mcp
        run: |
          git push --force https://api:${{secrets.HF_TOKEN}}@huggingface.co/spaces/$HF_USERNAME/$HF_SPACE main
```

---

## 📊 Monitoreo

### Logs en Tiempo Real

En el Space UI:
```
Logs → Build → Runtime
```

### Métricas de Uso

HF Spaces **no** tiene métricas integradas. Puedes añadir:

**Opción 1**: Log aggregation
```python
# En server.py, añade middleware
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {time.time()-start:.2f}s")
    return response
```

**Opción 2**: Sentry/PostHog (external)

---

## 💰 Costes

| Recurso | Coste |
|---------|-------|
| **CPU básico** | **$0/mes** |
| Storage (50GB) | $0 |
| Build time | $0 |
| **Total** | **$0/mes** |

**Limitaciones Free Tier**:
- Cold start si inactivo 48h (warm-up: ~30s)
- No GPU (no lo necesitamos, usamos fastembed CPU)
- Sin auto-scaling (1 réplica)

**Upgrade a PRO ($9/mes)** solo si:
- Necesitas 0 cold starts
- Quieres más de 1 réplica
- Necesitas GPU (no aplica aquí)

---

## ✅ Checklist de Deployment

- [ ] Space creado en Hugging Face
- [ ] SDK configurado como **Docker**
- [ ] Puerto 7860 en Dockerfile
- [ ] USER 1000 configurado
- [ ] `uv.lock` actualizado
- [ ] Push al repo del Space
- [ ] Build completado (ver logs)
- [ ] Health check responde 200
- [ ] Index cargado (ver logs: "Semantic search ready")
- [ ] Conectado desde Claude Desktop
- [ ] Test query ejecutada con éxito

---

## 🎯 Próximos Pasos

1. **Deploy en HF** (sigue esta guía)
2. **Prueba local antes**: `uvicorn ine_mcp.server:app --port 7860`
3. **Conecta Claude Desktop** con la URL del Space
4. **Graba demo** mostrando semantic search + correlation

---

**¿Problemas?** Revisa los logs del build en HF Spaces UI.
**¿Funciona?** 🎉 Tienes un MCP server en producción con $0/mes.
