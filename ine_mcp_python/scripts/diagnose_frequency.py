#!/usr/bin/env python3
"""
Diagnose why frequency detection is returning 'unknown'
Fetch actual data and show raw date formats
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ine_mcp.api.client import INEClient
from ine_mcp.tools.aggregation import DataAggregator


async def main():
    # Test with one of our known working series
    test_series = [
        "EEEI4154",  # Inflation category
        "IAS1825",   # Tourism category
        "IAS3687",   # Housing category
    ]

    aggregator = DataAggregator()

    async with INEClient() as client:
        for series_id in test_series:
            print(f"\n{'='*80}")
            print(f"Series: {series_id}")
            print(f"{'='*80}")

            # Fetch data
            data = await client.get_series_data(series_id, last_n=20)

            # Show raw structure
            print(f"\nKeys in response: {list(data.keys())}")

            if "Data" in data:
                data_points = data["Data"]
                print(f"Number of data points: {len(data_points)}")

                if data_points:
                    print(f"\nFirst 5 data points (raw):")
                    for i, point in enumerate(data_points[:5], 1):
                        print(f"  {i}. {point}")

                    print(f"\nDate field examples:")
                    for i, point in enumerate(data_points[:5], 1):
                        # Try different possible date field names
                        date_val = (
                            point.get("Fecha")
                            or point.get("fecha")
                            or point.get("T3_Periodo")
                            or point.get("Periodo")
                            or point.get("date")
                            or "NOT FOUND"
                        )
                        value_val = point.get("Valor") or point.get("valor") or point.get("value") or "NOT FOUND"
                        print(f"  {i}. Date field: {date_val}, Value: {value_val}")

            # Try parsing with aggregator
            print(f"\nTrying to parse with aggregator...")
            try:
                df = aggregator.parse_ine_data(data)
                print(f"✓ Parsed successfully: {len(df)} rows")

                if not df.empty:
                    print(f"  Index (dates):")
                    print(f"    First: {df.index[0]}")
                    print(f"    Last: {df.index[-1]}")
                    print(f"    Dtype: {df.index.dtype}")

                    # Calculate frequency manually
                    if len(df) >= 3:
                        diffs = df.index.to_series().diff()[1:4]
                        print(f"  First 3 date differences:")
                        for i, diff in enumerate(diffs, 1):
                            print(f"    {i}. {diff}")

                    # Try detect frequency
                    freq = aggregator.detect_frequency(df)
                    print(f"\n  Detected frequency: {freq}")
                else:
                    print(f"✗ DataFrame is empty!")

            except Exception as e:
                print(f"✗ Error parsing: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
