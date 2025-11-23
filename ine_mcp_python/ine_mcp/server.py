"""
MCP Server - Production-grade Model Context Protocol server for INE API
Integrates semantic search, caching, and intelligent data aggregation
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from ine_mcp.api.client import INEClient, INEAPIError
from ine_mcp.cache.manager import CacheManager
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class INEMCPServer:
    """
    Production MCP Server for Spanish INE API

    Architecture:
    ┌─────────────┐
    │ LLM Client  │
    └──────┬──────┘
           │
    ┌──────▼──────────────────────────────┐
    │ MCP Server (this class)             │
    │  ├─ Semantic Search (FAISS)         │
    │  ├─ Cache Layer (Redis/Memory)      │
    │  └─ Data Aggregation (Pandas)       │
    └──────┬──────────────────────────────┘
           │
    ┌──────▼──────┐
    │  INE API    │
    └─────────────┘
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        index_dir: Path = Path("data"),
    ):
        self.server = Server("ine-mcp")

        # Initialize components
        self.api_client: Optional[INEClient] = None
        self.cache = CacheManager(redis_url=redis_url)
        self.search_engine = SemanticSearchEngine(
            index_path=index_dir / "faiss_index.bin",
            metadata_path=index_dir / "series_metadata.pkl",
        )
        self.aggregator = DataAggregator()

        # Register handlers
        self._register_handlers()

        logger.info("INE MCP Server initialized")

    def _register_handlers(self):
        """Register MCP request handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="search_series_semantic",
                    description=(
                        "Search for INE series using semantic similarity. "
                        "Much better than keyword search - understands meaning. "
                        "Example: 'inflación alimentos' finds 'IPC Alimentos' even without exact match."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum results (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_series_data",
                    description=(
                        "Get time series data with intelligent aggregation. "
                        "Automatically reduces large datasets to prevent context overflow. "
                        "Returns clean, LLM-ready format with statistics."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "series_id": {
                                "type": "string",
                                "description": "Series ID from search results",
                            },
                            "last_n": {
                                "type": "number",
                                "description": "Get last N data points",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Start date (YYYY or YYYYMMDD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date (YYYY or YYYYMMDD)",
                            },
                            "format": {
                                "type": "string",
                                "enum": ["dict", "csv"],
                                "description": "Output format",
                                "default": "dict",
                            },
                        },
                        "required": ["series_id"],
                    },
                ),
                Tool(
                    name="get_series_metadata",
                    description="Get complete metadata for a series (units, frequency, source, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "series_id": {"type": "string", "description": "Series ID"},
                        },
                        "required": ["series_id"],
                    },
                ),
                Tool(
                    name="analyze_correlation",
                    description=(
                        "Analyze correlation between two time series. "
                        "Automatically aligns dates and calculates Pearson correlation."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "series_id_1": {"type": "string"},
                            "series_id_2": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                        },
                        "required": ["series_id_1", "series_id_2"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute tool"""
            logger.info(f"Tool called: {name} with args: {arguments}")

            try:
                if name == "search_series_semantic":
                    result = await self._search_semantic(arguments)
                elif name == "get_series_data":
                    result = await self._get_series_data(arguments)
                elif name == "get_series_metadata":
                    result = await self._get_metadata(arguments)
                elif name == "analyze_correlation":
                    result = await self._analyze_correlation(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=str(result))]

            except Exception as e:
                logger.error(f"Error in tool {name}: {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _search_semantic(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Semantic search using pre-computed embeddings"""
        query = args["query"]
        limit = args.get("limit", 10)

        cache_key = CacheManager.make_key("search", query, limit)

        async def fetch():
            if not self.search_engine.is_ready():
                # Fallback to keyword search if index not ready
                logger.warning("FAISS index not ready, falling back to keyword search")
                async with INEClient() as client:
                    results = await client.search_series(query)
                    return results[:limit]

            # Semantic search
            results = self.search_engine.search(query, top_k=limit)
            return results

        results = await self.cache.get_or_fetch(
            cache_key, fetch, ttl=CacheManager.TTL_SEARCH
        )

        return {
            "query": query,
            "method": "semantic" if self.search_engine.is_ready() else "keyword",
            "count": len(results),
            "results": results,
        }

    async def _get_series_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get series data with intelligent aggregation"""
        series_id = args["series_id"]
        last_n = args.get("last_n")
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        output_format = args.get("format", "dict")

        cache_key = CacheManager.make_key("data", series_id, last_n, start_date, end_date)

        async def fetch():
            async with INEClient() as client:
                raw_data = await client.get_series_data(
                    series_id,
                    last_n=last_n,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Intelligent aggregation
                processed = self.aggregator.process_series_data(
                    raw_data,
                    auto_aggregate=True,
                    output_format=output_format,
                )

                return processed

        result = await self.cache.get_or_fetch(
            cache_key, fetch, ttl=CacheManager.TTL_SERIES_DATA
        )

        return result

    async def _get_metadata(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get series metadata"""
        series_id = args["series_id"]

        cache_key = CacheManager.make_key("metadata", series_id)

        async def fetch():
            async with INEClient() as client:
                metadata = await client.get_series_metadata(series_id)
                return metadata.model_dump()

        return await self.cache.get_or_fetch(
            cache_key, fetch, ttl=CacheManager.TTL_METADATA
        )

    async def _analyze_correlation(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze correlation between two series with SMART FREQUENCY ALIGNMENT

        SENIOR FIX: Detects frequencies and resamples to common frequency
        Before: Monthly + Quarterly → loses 66% of data
        After: Both resampled to Quarterly → robust statistics
        """
        import pandas as pd
        import numpy as np

        series_id_1 = args["series_id_1"]
        series_id_2 = args["series_id_2"]
        start_date = args.get("start_date")
        end_date = args.get("end_date")

        # Fetch both series
        async with INEClient() as client:
            data1 = await client.get_series_data(
                series_id_1, start_date=start_date, end_date=end_date
            )
            data2 = await client.get_series_data(
                series_id_2, start_date=start_date, end_date=end_date
            )

        # Parse into DataFrames
        df1 = self.aggregator.parse_ine_data(data1)
        df2 = self.aggregator.parse_ine_data(data2)

        if df1.empty or df2.empty:
            return {"error": "One or both series have no data"}

        # CRITICAL FIX: Align frequencies before merging
        freq1_before = self.aggregator.detect_frequency(df1)
        freq2_before = self.aggregator.detect_frequency(df2)

        df1_aligned, df2_aligned, common_freq = self.aggregator.align_series_frequencies(
            df1, df2
        )

        # Now merge on aligned frequencies (no data loss!)
        combined = pd.merge(
            df1_aligned, df2_aligned, left_index=True, right_index=True, suffixes=("_1", "_2")
        )

        if len(combined) < 2:
            return {
                "error": "Not enough overlapping data points after alignment",
                "freq_series_1": freq1_before,
                "freq_series_2": freq2_before,
                "common_freq": common_freq,
            }

        # Calculate correlation on properly aligned data
        correlation = combined["value_1"].corr(combined["value_2"])

        return {
            "series_1": series_id_1,
            "series_2": series_id_2,
            "frequency_alignment": {
                "series_1_original": freq1_before,
                "series_2_original": freq2_before,
                "common_frequency": common_freq,
                "resampling_applied": freq1_before != freq2_before,
            },
            "data_points": {
                "series_1_original": len(df1),
                "series_2_original": len(df2),
                "after_alignment": len(combined),
            },
            "date_range": {
                "start": combined.index[0].strftime("%Y-%m-%d"),
                "end": combined.index[-1].strftime("%Y-%m-%d"),
            },
            "correlation": float(correlation),
            "interpretation": self._interpret_correlation(correlation),
        }

    @staticmethod
    def _interpret_correlation(r: float) -> str:
        """Human-readable correlation interpretation"""
        abs_r = abs(r)
        direction = "positive" if r > 0 else "negative"

        if abs_r > 0.8:
            strength = "very strong"
        elif abs_r > 0.6:
            strength = "strong"
        elif abs_r > 0.4:
            strength = "moderate"
        elif abs_r > 0.2:
            strength = "weak"
        else:
            strength = "very weak"

        return f"{strength.capitalize()} {direction} correlation (r={r:.3f})"

    async def run(self):
        """Start the MCP server"""
        logger.info("Starting INE MCP Server...")

        # Initialize cache
        await self.cache.initialize()

        # Try to load search index
        try:
            self.search_engine.load_index()
            logger.info("✓ Semantic search ready")
        except FileNotFoundError:
            logger.warning("⚠ FAISS index not found. Run build_index.py first.")
            logger.warning("  Falling back to keyword search")

        # Run server
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server running on stdio")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Main entry point"""
    redis_url = os.getenv("REDIS_URL")
    index_dir = Path(os.getenv("INDEX_DIR", "data"))

    server = INEMCPServer(redis_url=redis_url, index_dir=index_dir)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
