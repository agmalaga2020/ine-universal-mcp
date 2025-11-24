import asyncio
import os
import logging
import sys
from pathlib import Path
from mcp.server.stdio import stdio_server
from ine_mcp.server import mcp_server, ine_components, build_index_background
from ine_mcp.cache.manager import CacheManager
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator

# Configure logging to write to stderr
# CRITICAL: stdout must be reserved for MCP JSON-RPC messages
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting INE MCP Server (Stdio Mode)")

    # Initialize components (logic adapted from server.py lifespan)
    redis_url = os.getenv("REDIS_URL")
    # In Docker, WORKDIR is /app, so data is at /app/data
    index_dir = Path(os.getenv("INDEX_DIR", "/app/data"))

    logger.info(f"Initializing components... (Index dir: {index_dir})")
    
    ine_components["cache"] = CacheManager(redis_url=redis_url)
    ine_components["search"] = SemanticSearchEngine(
        index_path=index_dir / "faiss_index.bin",
        metadata_path=index_dir / "series_metadata.pkl",
    )
    ine_components["aggregator"] = DataAggregator()

    # Start cache
    try:
        await ine_components["cache"].initialize()
        logger.info("✓ Cache initialized")
    except Exception as e:
        logger.error(f"Failed to init cache: {e}")

    # Try to load FAISS index
    try:
        ine_components["search"].load_index()
        stats = ine_components["search"].get_stats()
        logger.info(f"✓ Semantic search ready: {stats['total_series']} series indexed")
    except Exception as e:
        logger.warning(f"⚠️  Search index not available: {e}")
        logger.warning("Server will use keyword search fallback")
        # Launch background task
        asyncio.create_task(build_index_background())

    # Run Stdio Server
    logger.info("MCP Server ready on Stdio")
    
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
