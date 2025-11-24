"""
MCP Server - Production-grade Model Context Protocol server for INE API
Exposes SSE (Server-Sent Events) endpoints for remote LLM connection.

Architecture optimized for cloud deployment (Hugging Face Spaces, Railway, etc.)
"""

import json
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent

from ine_mcp.api.client import INEClient, INEAPIError
from ine_mcp.cache.manager import CacheManager
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global MCP server and components
mcp_server = Server("ine-mcp")
ine_components = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: Initialize components on startup, cleanup on shutdown"""
    logger.info("=" * 80)
    logger.info("INE MCP Server - Starting up")
    logger.info("=" * 80)

    redis_url = os.getenv("REDIS_URL")
    index_dir = Path(os.getenv("INDEX_DIR", "data"))

    # Initialize components
    logger.info("Initializing components...")
    ine_components["cache"] = CacheManager(redis_url=redis_url)
    ine_components["search"] = SemanticSearchEngine(
        index_path=index_dir / "faiss_index.bin",
        metadata_path=index_dir / "series_metadata.pkl",
    )
    ine_components["aggregator"] = DataAggregator()

    # Start cache
    await ine_components["cache"].initialize()
    logger.info("✓ Cache initialized")

    # Try to load FAISS index
    try:
        ine_components["search"].load_index()
        stats = ine_components["search"].get_stats()
        logger.info(f"✓ Semantic search ready: {stats['total_series']} series indexed")
    except Exception as e:
        logger.warning(f"⚠️  Search index not available: {e}")
        logger.warning("Server will use keyword search fallback")

    logger.info("=" * 80)
    logger.info("INE MCP Server - Ready to accept connections")
    logger.info("=" * 80)

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
    await ine_components["cache"].close()
    logger.info("✓ Shutdown complete")


# Create FastAPI app with lifespan
app = FastAPI(
    title="INE MCP Server",
    description="Production-grade MCP server for Spanish INE API with semantic search",
    version="2.0.0",
    lifespan=lifespan,
)


# ============================================================================
# MCP TOOL DEFINITIONS
# ============================================================================

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools"""
    return [
        Tool(
            name="search_series_semantic",
            description=(
                "Search for INE series using semantic similarity (understands meaning, not just keywords). "
                "Example: 'inflación alimentos' finds 'IPC Alimentos' even without exact match. "
                "Returns series IDs, names, and similarity scores."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query in Spanish or English",
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_series_data",
            description=(
                "Fetch time series data with intelligent aggregation. "
                "Automatically detects frequency and can aggregate to prevent context overflow. "
                "Returns formatted data ready for analysis."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "string",
                        "description": "INE series ID (e.g., 'IPC86')",
                    },
                    "last_n": {
                        "type": "number",
                        "description": "Number of most recent observations to fetch",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD format)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format)",
                    },
                    "aggregate_to": {
                        "type": "string",
                        "enum": ["D", "W", "M", "Q", "Y"],
                        "description": "Target frequency for aggregation (D=daily, M=monthly, Q=quarterly, Y=yearly)",
                    },
                },
                "required": ["series_id"],
            },
        ),
        Tool(
            name="analyze_correlation",
            description=(
                "Analyze correlation between two time series with automatic frequency alignment. "
                "CRITICAL: Prevents data loss by resampling to common frequency before correlation. "
                "Returns correlation coefficient, p-value, and alignment metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id_1": {
                        "type": "string",
                        "description": "First series ID",
                    },
                    "series_id_2": {
                        "type": "string",
                        "description": "Second series ID",
                    },
                },
                "required": ["series_id_1", "series_id_2"],
            },
        ),
        Tool(
            name="get_operations",
            description=(
                "List all available INE operations (statistical surveys/datasets). "
                "Operations group related series (e.g., 'IPC', 'EPA', 'CNE')."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Central tool dispatcher - routes requests to appropriate handlers"""
    logger.info(f"Tool call: {name} with args: {arguments}")

    cache = ine_components["cache"]
    search = ine_components["search"]
    aggregator = ine_components["aggregator"]

    try:
        # ===== SEMANTIC SEARCH =====
        if name == "search_series_semantic":
            query = arguments["query"]
            limit = arguments.get("limit", 10)

            # Check cache
            cache_key = f"search:{query}:{limit}"
            cached = await cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for search: {query}")
                return [TextContent(type="text", text=cached)]

            # Execute search
            if search.is_ready():
                results = search.search(query, top_k=limit, score_threshold=0.3)
                method = "semantic"
                logger.info(f"Semantic search: {len(results)} results")
            else:
                # Fallback to keyword search via API
                async with INEClient() as client:
                    results = await client.search_series(query)
                    results = results[:limit]
                method = "keyword_fallback"
                logger.warning("Using keyword fallback (index not loaded)")

            response = {
                "method": method,
                "query": query,
                "results_count": len(results),
                "results": results,
            }

            # Cache for 30 minutes
            await cache.set(cache_key, json.dumps(response), ttl=1800)
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        # ===== GET SERIES DATA =====
        elif name == "get_series_data":
            series_id = arguments["series_id"]
            last_n = arguments.get("last_n")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            aggregate_to = arguments.get("aggregate_to")

            # Check cache
            cache_key = f"series:{series_id}:{last_n}:{start_date}:{end_date}:{aggregate_to}"
            cached = await cache.get(cache_key)
            if cached:
                return [TextContent(type="text", text=cached)]

            # Fetch data
            async with INEClient() as client:
                raw_data = await client.get_series_data(
                    series_id,
                    last_n=last_n,
                    start_date=start_date,
                    end_date=end_date,
                )

            # Parse and process
            df = aggregator.parse_ine_data(raw_data)

            if df.empty:
                return [TextContent(type="text", text=json.dumps({
                    "error": "No data available for this series",
                    "series_id": series_id,
                }))]

            # Detect frequency
            original_freq = aggregator.detect_frequency(df)

            # Aggregate if requested
            if aggregate_to and aggregate_to != original_freq:
                df = aggregator.aggregate(df, target_freq=aggregate_to)
                applied_aggregation = True
            else:
                applied_aggregation = False

            # Format response
            response = {
                "series_id": series_id,
                "data_points": len(df),
                "date_range": {
                    "start": str(df.index[0].date()),
                    "end": str(df.index[-1].date()),
                },
                "frequency": {
                    "original": original_freq,
                    "output": aggregate_to or original_freq,
                    "aggregation_applied": applied_aggregation,
                },
                "data": df.to_dict(orient="index"),
            }

            # Cache for 1 hour
            result = json.dumps(response, indent=2, default=str)
            await cache.set(cache_key, result, ttl=3600)
            return [TextContent(type="text", text=result)]

        # ===== CORRELATION ANALYSIS =====
        elif name == "analyze_correlation":
            series_id_1 = arguments["series_id_1"]
            series_id_2 = arguments["series_id_2"]

            # Fetch both series
            async with INEClient() as client:
                data1 = await client.get_series_data(series_id_1)
                data2 = await client.get_series_data(series_id_2)

            # Parse
            df1 = aggregator.parse_ine_data(data1)
            df2 = aggregator.parse_ine_data(data2)

            if df1.empty or df2.empty:
                return [TextContent(type="text", text=json.dumps({
                    "error": "One or both series have no data",
                    "series_1_points": len(df1),
                    "series_2_points": len(df2),
                }))]

            # Detect original frequencies
            freq1_original = aggregator.detect_frequency(df1)
            freq2_original = aggregator.detect_frequency(df2)

            # CRITICAL: Align frequencies (prevents data loss)
            df1_aligned, df2_aligned, common_freq = aggregator.align_series_frequencies(df1, df2)

            # Merge on aligned frequencies
            combined = pd.merge(
                df1_aligned,
                df2_aligned,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )

            if len(combined) < 3:
                return [TextContent(type="text", text=json.dumps({
                    "error": "Insufficient overlapping data points",
                    "overlapping_points": len(combined),
                    "minimum_required": 3,
                }))]

            # Calculate correlation
            correlation = combined["value_1"].corr(combined["value_2"])

            # Build response
            response = {
                "series_1": {
                    "id": series_id_1,
                    "original_points": len(df1),
                    "original_frequency": freq1_original,
                },
                "series_2": {
                    "id": series_id_2,
                    "original_points": len(df2),
                    "original_frequency": freq2_original,
                },
                "frequency_alignment": {
                    "series_1_original": freq1_original,
                    "series_2_original": freq2_original,
                    "common_frequency": common_freq,
                    "resampling_applied": freq1_original != freq2_original,
                },
                "data_points": {
                    "series_1_original": len(df1),
                    "series_2_original": len(df2),
                    "after_alignment": len(combined),
                    "data_preservation_pct": (len(combined) / min(len(df1), len(df2))) * 100,
                },
                "date_range": {
                    "start": str(combined.index[0].date()),
                    "end": str(combined.index[-1].date()),
                },
                "correlation": float(correlation),
                "interpretation": (
                    "strong positive" if correlation > 0.7
                    else "moderate positive" if correlation > 0.4
                    else "weak positive" if correlation > 0
                    else "weak negative" if correlation > -0.4
                    else "moderate negative" if correlation > -0.7
                    else "strong negative"
                ),
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        # ===== LIST OPERATIONS =====
        elif name == "get_operations":
            # Check cache
            cache_key = "operations:list"
            cached = await cache.get(cache_key)
            if cached:
                return [TextContent(type="text", text=cached)]

            async with INEClient() as client:
                operations = await client.get_operations()

            response = {
                "total_operations": len(operations),
                "operations": operations[:50],  # Limit to first 50 to avoid context overflow
            }

            result = json.dumps(response, indent=2)
            await cache.set(cache_key, result, ttl=86400)  # Cache for 24 hours
            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Unknown tool: {name}",
                "available_tools": ["search_series_semantic", "get_series_data", "analyze_correlation", "get_operations"],
            }))]

    except INEAPIError as e:
        logger.error(f"INE API error in {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": "INE API error",
            "message": str(e),
            "tool": name,
        }))]

    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=json.dumps({
            "error": "Internal server error",
            "message": str(e),
            "tool": name,
        }))]


# ============================================================================
# SSE ENDPOINTS FOR MCP
# ============================================================================

sse = SseServerTransport("/messages")


@app.get("/sse")
async def handle_sse(request: Request):
    """SSE endpoint for MCP client connections"""
    logger.info("SSE connection established")
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


@app.post("/messages")
async def handle_messages(request: Request):
    """POST endpoint for MCP messages"""
    await sse.handle_post_message(request.scope, request.receive, request._send)


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return JSONResponse({
        "status": "healthy",
        "service": "INE MCP Server",
        "version": "2.0.0",
        "components": {
            "cache": "ready" if ine_components.get("cache") else "not_initialized",
            "search": "ready" if ine_components.get("search") and ine_components["search"].is_ready() else "degraded",
            "aggregator": "ready" if ine_components.get("aggregator") else "not_initialized",
        },
    })


@app.get("/")
async def root():
    """Root endpoint with server info"""
    search = ine_components.get("search")
    stats = search.get_stats() if search and search.is_ready() else {"status": "not_ready"}

    return JSONResponse({
        "service": "INE MCP Server",
        "version": "2.0.0",
        "description": "Production-grade MCP server for Spanish INE API",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages",
            "health": "/health",
        },
        "features": [
            "Semantic search with FAISS",
            "Intelligent data aggregation",
            "Frequency alignment for correlation",
            "Redis caching with fallback",
        ],
        "search_index": stats,
    })


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting server on port {port}...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
