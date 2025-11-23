#!/usr/bin/env python3
"""
SMOKE TEST: Direct test with hardcoded working series
Tests frequency alignment with known good data
"""

import asyncio
import json
import logging

from ine_mcp.api.client import INEClient
from ine_mcp.tools.aggregation import DataAggregator

logging.basicConfig(level=logging.WARNING)  # Suppress noise


async def main():
    """Test frequency alignment with two hardcoded series"""

    print("=" * 80)
    print("SMOKE TEST: Frequency Alignment")
    print("=" * 80)
    print()

    # Use verified working series IDs from find_working_series.py
    # These have excellent overlap: 45 points from 2021-2025
    series_1 = "IAS3643"   # Publishing: Cifra de negocio Edición - Monthly
    series_2 = "IAS3687"   # Housing: Cifra de negocio inmobiliarias - Monthly

    print(f"Testing with verified working series:")
    print(f"  Series 1: {series_1} (Publishing/Editing - Monthly)")
    print(f"  Series 2: {series_2} (Real Estate - Monthly)")
    print(f"  Expected overlap: 45 months (2021-2025)")
    print()

    aggregator = DataAggregator()

    async with INEClient() as client:
        print("Fetching data...")

        try:
            # Fetch data
            data1 = await client.get_series_data(series_1, last_n=60)
            data2 = await client.get_series_data(series_2, last_n=20)

            # Parse
            df1 = aggregator.parse_ine_data(data1)
            df2 = aggregator.parse_ine_data(data2)

            if df1.empty or df2.empty:
                print(f"✗ Empty data (series may have been removed from API):")
                print(f"  Series 1: {len(df1)} points")
                print(f"  Series 2: {len(df2)} points")
                return

            print(f"✓ Data fetched:")
            print(f"  Series 1: {len(df1)} points")
            print(f"  Series 2: {len(df2)} points")
            print()

            # Detect frequencies
            freq1 = aggregator.detect_frequency(df1)
            freq2 = aggregator.detect_frequency(df2)

            print(f"Frequencies detected:")
            print(f"  Series 1: {freq1}")
            print(f"  Series 2: {freq2}")
            print()

            # Align
            df1_aligned, df2_aligned, common_freq = aggregator.align_series_frequencies(
                df1, df2
            )

            print(f"After alignment:")
            print(f"  Common frequency: {common_freq}")
            print(f"  Series 1: {len(df1_aligned)} points")
            print(f"  Series 2: {len(df2_aligned)} points")
            print()

            # Merge
            import pandas as pd

            combined = pd.merge(
                df1_aligned,
                df2_aligned,
                left_index=True,
                right_index=True,
                suffixes=("_1", "_2"),
            )

            if len(combined) < 2:
                print(f"✗ Not enough overlap: {len(combined)} points")
                return

            # Correlation
            correlation = combined["value_1"].corr(combined["value_2"])

            result = {
                "series_1": {
                    "id": series_1,
                    "original_points": len(df1),
                    "original_frequency": freq1,
                },
                "series_2": {
                    "id": series_2,
                    "original_points": len(df2),
                    "original_frequency": freq2,
                },
                "frequency_alignment": {
                    "series_1_original": freq1,
                    "series_2_original": freq2,
                    "common_frequency": common_freq,
                    "resampling_applied": freq1 != freq2,
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
            }

            print("=" * 80)
            print("RESULT JSON")
            print("=" * 80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()

            print("=" * 80)
            print("VALIDATION")
            print("=" * 80)

            if freq1 != freq2:
                print("✓ Frequency mismatch detected and handled")
            else:
                print("⚠ Both series have same frequency (no alignment needed)")

            if len(combined) > 10:
                print(f"✓ Sufficient overlapping points: {len(combined)}")
            else:
                print(f"✗ Too few overlapping points: {len(combined)}")

            data_preservation = len(combined) / min(len(df1_aligned), len(df2_aligned))
            if data_preservation > 0.5:
                print(f"✓ Data preservation: {data_preservation:.1%}")
            else:
                print(f"✗ Excessive data loss: {1-data_preservation:.1%}")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
