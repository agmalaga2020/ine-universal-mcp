#!/usr/bin/env python3
"""
Build FAISS index from INE API
Run this once to create the semantic search index
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ine_mcp.api.client import INEClient
from ine_mcp.embeddings.search import build_index_from_api

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Build the semantic search index"""
    logger.info("="*80)
    logger.info("INE SEMANTIC SEARCH INDEX BUILDER")
    logger.info("="*80)
    logger.info("")
    logger.info("This will:")
    logger.info("  1. Fetch all series metadata from INE API")
    logger.info("  2. Generate embeddings using sentence-transformers")
    logger.info("  3. Build FAISS index for fast semantic search")
    logger.info("")
    logger.info("⚠️  This may take 10-30 minutes depending on your connection")
    logger.info("")

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    try:
        async with INEClient(timeout=60.0) as client:
            logger.info("Building index from INE API...")

            engine = await build_index_from_api(
                api_client=client,
                output_dir=output_dir,
                max_operations=None,  # Process all operations
            )

            stats = engine.get_stats()
            logger.info("")
            logger.info("="*80)
            logger.info("✓ INDEX BUILD COMPLETE")
            logger.info("="*80)
            logger.info(f"  Total series indexed: {stats['total_series']}")
            logger.info(f"  Index file: {stats['index_file']}")
            logger.info(f"  Metadata file: {stats['metadata_file']}")
            logger.info("")
            logger.info("You can now run the MCP server with semantic search enabled!")
            logger.info("")

    except KeyboardInterrupt:
        logger.warning("\nIndex building interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error building index: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
