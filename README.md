---
title: INE Universal MCP Server
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# INE Universal MCP Server

**[🇪🇸 Versión en Español](./README.es.md)** | 🇬🇧 English

A production-grade Model Context Protocol (MCP) server providing universal access to the Spanish INE (Instituto Nacional de Estadística) API with advanced semantic search and intelligent data aggregation.

## 🚀 Features

- 🔍 **Semantic Search**: FAISS-powered vector search with 34K+ indexed series
- 📊 **Smart Data Retrieval**: Automatic frequency detection and aggregation
- 🔗 **Correlation Analysis**: Automatic frequency alignment for time series correlation
- ⚡ **High Performance**: Redis caching with async background index building
- 🐳 **Cloud-Ready**: Deployed on Hugging Face Spaces with Docker
- 🛡️ **Production-Grade**: Robust error handling, logging, and timeout management

## 📡 API Endpoints

- **SSE Endpoint**: `/sse` - Server-Sent Events for MCP client connections
- **Messages**: `/messages` - POST endpoint for MCP protocol messages
- **Health Check**: `/health` - Service health and component status
- **Root**: `/` - Server info and search index statistics

## 🔧 MCP Tools Available

1. **search_series_semantic**: Semantic search across INE series
2. **get_series_data**: Fetch time series with intelligent aggregation
3. **analyze_correlation**: Correlation analysis with frequency alignment
4. **get_operations**: List available INE operations
5. **get_table_data**: Access INE tables directly (e.g., Housing Price Index - IPV)

## 🏗️ Architecture

- **FastAPI + SSE**: Web server with Server-Sent Events for MCP
- **FAISS**: Vector similarity search for semantic queries
- **FastEmbed**: Lightweight ONNX embeddings (150MB vs 1.5GB)
- **Pandas**: Vectorized operations for time series processing
- **Redis**: Caching layer with in-memory fallback
- **Docker**: Multi-stage build optimized for HF Spaces

## 📚 Examples

Check the `ine_mcp_python/examples/` folder for complete usage examples:

- `simple_search.py` - Basic semantic search
- `ipc_analysis.py` - Consumer Price Index analysis
- `tourism_rental_correlation.py` - Tourism and rental price correlation
- `final_malaga_analysis.py` - Provincial demographic analysis

## 🔗 Connect with Claude

Add this configuration to your Claude Desktop config:

```json
{
  "mcpServers": {
    "ine-universal": {
      "url": "https://Blbllbbdkdjbdjf-ine-universal-mcp.hf.space/sse"
    }
  }
}
```

## 📊 Data Source

Data provided by [INE (Instituto Nacional de Estadística)](https://www.ine.es) - Spain's official statistical agency.

## 🛠️ Development

Built with:
- Python 3.11
- FastAPI + Uvicorn
- FAISS (CPU)
- FastEmbed
- Pandas + NumPy
- Redis (optional)
- MCP SDK 0.9.0

## 📝 License

MIT License - See LICENSE file for details

---

**Status**: 🟢 Running on Hugging Face Spaces | **Index**: 34,390 series | **Version**: 2.0.0
