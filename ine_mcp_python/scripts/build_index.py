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
from ine_mcp.embeddings.search import SemanticSearchEngine

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
    logger.info("  1. Fetch series metadata from main INE operations")
    logger.info("  2. Generate embeddings using sentence-transformers")
    logger.info("  3. Build FAISS index for fast semantic search")
    logger.info("")
    logger.info("⚠️  This may take 10-20 minutes")
    logger.info("")

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    # Use curated list of main operations (INE's /OPERACIONES endpoint is unreliable)
    MAIN_OPERATIONS = [
        {"code": "30", "name": "IPC - Índice de Precios de Consumo"},
        {"code": "45", "name": "EPA - Encuesta de Población Activa"},
        {"code": "31", "name": "IPRI - Índice de Precios Industriales"},
        {"code": "36", "name": "CNE - Contabilidad Nacional"},
        {"code": "56", "name": "Demografía y Población"},
        {"code": "23", "name": "Comercio Exterior"},
        {"code": "50", "name": "Encuesta de Condiciones de Vida"},
        {"code": "24", "name": "Turismo"},
        {"code": "1270", "name": "Hipotecas"},
        {"code": "1259", "name": "Índice de Precios de Vivienda"},
    ]

    all_series = []

    try:
        async with INEClient(timeout=60.0) as client:
            logger.info(f"Fetching series from {len(MAIN_OPERATIONS)} main operations...")

            for i, operation in enumerate(MAIN_OPERATIONS, 1):
                op_code = operation["code"]
                op_name = operation["name"]

                logger.info(f"[{i}/{len(MAIN_OPERATIONS)}] {op_name} (code: {op_code})")

                try:
                    series = await client.get_operation_series(op_code)
                    all_series.extend(series)
                    logger.info(f"  → {len(series)} series found")

                except Exception as e:
                    logger.error(f"  → Error: {e}")
                    continue

            logger.info("")
            logger.info(f"Total series collected: {len(all_series)}")

            if len(all_series) == 0:
                logger.error("No series found. Cannot build index.")
                sys.exit(1)

            # Create search engine and build index
            engine = SemanticSearchEngine(
                index_path=output_dir / "faiss_index.bin",
                metadata_path=output_dir / "series_metadata.pkl",
            )

            num_indexed, size_mb = engine.create_index(all_series)
            engine.save_index()

            logger.info("")
            logger.info("="*80)
            logger.info("✓ INDEX BUILD COMPLETE")
            logger.info("="*80)
            logger.info(f"  Total series indexed: {num_indexed}")
            logger.info(f"  Index file: {engine.index_path}")
            logger.info(f"  Metadata file: {engine.metadata_path}")
            logger.info(f"  Size: {size_mb:.2f}MB")
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
