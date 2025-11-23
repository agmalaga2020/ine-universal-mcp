#!/usr/bin/env python3
"""
Find "Silver Bullet" Series IDs for Demo

Systematically tests series from the FAISS index to find ones that:
1. Actually return data from INE API (not empty responses)
2. Come in meaningful pairs (e.g., inflation vs tourism)
3. Have different frequencies (to demo frequency alignment)

Output: winning_series.json with verified working IDs
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ine_mcp.api.client import INEClient
from ine_mcp.embeddings.search import SemanticSearchEngine
from ine_mcp.tools.aggregation import DataAggregator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_series_has_data(client: INEClient, series_id: str) -> bool:
    """Test if a series actually returns data"""
    try:
        data = await client.get_series_data(series_id, last_n=5)
        if not data:
            return False

        # Check if Data key exists and has content
        if "Data" not in data:
            return False

        data_points = data.get("Data", [])
        return len(data_points) > 0

    except Exception as e:
        logger.debug(f"  Error testing {series_id}: {e}")
        return False


async def find_working_series_in_category(
    client: INEClient,
    search_engine: SemanticSearchEngine,
    query: str,
    category_name: str,
    max_test: int = 30,
) -> List[Dict[str, Any]]:
    """
    Search for series by semantic query and test which ones have data

    Returns list of working series with metadata
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Category: {category_name}")
    logger.info(f"Query: '{query}'")
    logger.info(f"{'='*80}")

    # Semantic search
    results = search_engine.search(query, top_k=max_test, score_threshold=0.3)
    logger.info(f"Found {len(results)} candidates from semantic search")

    working_series = []

    for i, result in enumerate(results, 1):
        series_id = result["id"]
        series_name = result["name"]

        logger.info(f"[{i}/{len(results)}] Testing {series_id}: {series_name[:60]}...")

        has_data = await test_series_has_data(client, series_id)

        if has_data:
            logger.info(f"  ✓ HAS DATA!")
            working_series.append({
                "id": series_id,
                "name": series_name,
                "description": result.get("description", ""),
                "similarity_score": result["similarity_score"],
                "category": category_name,
                "query": query,
            })

            # Stop after finding 3 working series per category
            if len(working_series) >= 3:
                logger.info(f"  Found 3 working series in this category, moving on...")
                break
        else:
            logger.info(f"  ✗ No data")

        # Small delay to avoid overwhelming API
        await asyncio.sleep(0.5)

    logger.info(f"\nCategory '{category_name}' results: {len(working_series)} working series found")
    return working_series


async def detect_frequency_for_series(
    client: INEClient,
    aggregator: DataAggregator,
    series_id: str,
) -> str:
    """Fetch data and detect its frequency"""
    try:
        data = await client.get_series_data(series_id, last_n=20)
        df = aggregator.parse_ine_data(data)

        if df.empty:
            return "unknown"

        return aggregator.detect_frequency(df)

    except Exception as e:
        logger.error(f"Error detecting frequency for {series_id}: {e}")
        return "unknown"


async def main():
    """Find working series across key categories"""

    logger.info("="*80)
    logger.info("FINDING SILVER BULLET SERIES FOR DEMO")
    logger.info("="*80)
    logger.info("")
    logger.info("Strategy:")
    logger.info("  1. Search key categories with semantic search")
    logger.info("  2. Test each series to see if it returns data")
    logger.info("  3. Detect frequencies for meaningful pairs")
    logger.info("  4. Save winning IDs to winning_series.json")
    logger.info("")

    # Load search engine
    search_engine = SemanticSearchEngine(
        index_path=Path("data/faiss_index.bin"),
        metadata_path=Path("data/series_metadata.pkl"),
    )

    try:
        search_engine.load_index()
        logger.info(f"✓ Index loaded: {len(search_engine._metadata):,} series")
    except FileNotFoundError as e:
        logger.error(f"✗ Index not found: {e}")
        logger.error("Run: uv run python scripts/build_index.py")
        sys.exit(1)

    aggregator = DataAggregator()

    # Key categories to search
    # These are diverse and likely to have different frequencies
    categories = [
        ("inflación precios consumo", "Inflation (IPC)"),
        ("paro desempleo EPA", "Unemployment (EPA)"),
        ("turismo pernoctaciones hoteles", "Tourism"),
        ("PIB producto interior bruto", "GDP"),
        ("vivienda precios hipotecas", "Housing"),
        ("salarios sueldos remuneración", "Wages"),
        ("comercio exterior exportaciones", "Foreign Trade"),
    ]

    all_working_series = []

    async with INEClient(timeout=60.0) as client:

        for query, category_name in categories:
            working = await find_working_series_in_category(
                client,
                search_engine,
                query,
                category_name,
                max_test=30,  # Test up to 30 per category
            )
            all_working_series.extend(working)

            # If we already have enough, stop early
            if len(all_working_series) >= 15:
                logger.info(f"\nFound {len(all_working_series)} working series, stopping search...")
                break

        logger.info("\n" + "="*80)
        logger.info("DETECTING FREQUENCIES")
        logger.info("="*80)

        # Detect frequencies for all working series
        for series in all_working_series:
            series_id = series["id"]
            logger.info(f"Detecting frequency for {series_id}...")
            freq = await detect_frequency_for_series(client, aggregator, series_id)
            series["frequency"] = freq
            logger.info(f"  → {freq}")

    # Save results
    output_file = Path("data/winning_series.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_found": len(all_working_series),
                "categories_searched": len(categories),
                "series": all_working_series,
                "note": "These series have been verified to return actual data from INE API",
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total working series found: {len(all_working_series)}")
    logger.info(f"Saved to: {output_file}")
    logger.info("")

    # Group by frequency
    freq_groups = {}
    for series in all_working_series:
        freq = series.get("frequency", "unknown")
        if freq not in freq_groups:
            freq_groups[freq] = []
        freq_groups[freq].append(series)

    logger.info("Breakdown by frequency:")
    for freq, series_list in sorted(freq_groups.items()):
        logger.info(f"  {freq}: {len(series_list)} series")

    logger.info("")
    logger.info("="*80)
    logger.info("DEMO PAIR RECOMMENDATIONS")
    logger.info("="*80)

    # Find good pairs with different frequencies
    monthly = [s for s in all_working_series if s.get("frequency") == "M"]
    quarterly = [s for s in all_working_series if s.get("frequency") == "Q"]

    if monthly and quarterly:
        logger.info("\n✓ PAIR 1: Monthly vs Quarterly (demonstrates frequency alignment)")
        logger.info(f"  Series 1 (Monthly): {monthly[0]['id']} - {monthly[0]['name'][:50]}")
        logger.info(f"  Series 2 (Quarterly): {quarterly[0]['id']} - {quarterly[0]['name'][:50]}")

    # Find semantically related pairs
    inflation_series = [s for s in all_working_series if "IPC" in s["name"] or "inflación" in s["category"].lower()]
    tourism_series = [s for s in all_working_series if "turismo" in s["category"].lower() or "hotel" in s["name"].lower()]

    if inflation_series and tourism_series:
        logger.info("\n✓ PAIR 2: Inflation vs Tourism (semantically interesting)")
        logger.info(f"  Series 1 (Inflation): {inflation_series[0]['id']} - {inflation_series[0]['name'][:50]}")
        logger.info(f"  Series 2 (Tourism): {tourism_series[0]['id']} - {tourism_series[0]['name'][:50]}")

    logger.info("\n" + "="*80)
    logger.info("Next steps:")
    logger.info("  1. Review data/winning_series.json")
    logger.info("  2. Pick 2 pairs for demo")
    logger.info("  3. Test with: python test_smoke.py (update with winning IDs)")
    logger.info("="*80)
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
