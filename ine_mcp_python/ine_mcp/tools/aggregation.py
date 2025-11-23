"""
Data Aggregation - Intelligent preprocessing to avoid LLM context overflow
Uses Pandas to aggregate, resample, and format data for optimal LLM consumption
"""

import logging
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Intelligently aggregates time series data to prevent context overflow

    Key insight: Raw API data can be thousands of rows. LLMs have limited context.
    This class automatically downsamples data while preserving statistical properties.
    """

    # Thresholds for auto-aggregation
    MAX_DAILY_POINTS = 365  # More than 1 year daily → aggregate to monthly
    MAX_MONTHLY_POINTS = 120  # More than 10 years monthly → aggregate to yearly

    def __init__(self):
        logger.info("Data aggregator initialized")

    def parse_ine_data(self, raw_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Convert INE API response to pandas DataFrame

        Args:
            raw_data: Raw response from INE API

        Returns:
            DataFrame with datetime index and value column
        """
        if not raw_data or "Data" not in raw_data:
            return pd.DataFrame()

        data_points = raw_data["Data"]

        # Extract dates and values
        dates = []
        values = []

        for point in data_points:
            date_str = point.get("Fecha") or point.get("T3_Periodo")
            value = point.get("Valor")

            if date_str and value is not None:
                dates.append(self._parse_date(date_str))
                values.append(float(value) if isinstance(value, (int, float, str)) else np.nan)

        if not dates:
            return pd.DataFrame()

        df = pd.DataFrame({"date": dates, "value": values})
        df = df.sort_values("date")
        df = df.set_index("date")

        return df

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse INE date formats:
        - YYYYMMDD (daily)
        - YYYYMM (monthly)
        - YYYY (yearly)
        - YYYYQQ (quarterly)
        """
        date_str = str(date_str).strip()

        # Try different formats
        formats = [
            "%Y%m%d",  # 20240315
            "%Y-%m-%d",  # 2024-03-15
            "%Y%m",  # 202403
            "%Y",  # 2024
        ]

        # Handle quarter format (e.g., "2024Q1")
        if "Q" in date_str.upper():
            year = int(date_str[:4])
            quarter = int(date_str[-1])
            month = (quarter - 1) * 3 + 1
            return datetime(year, month, 1)

        # Handle monthly format like "2024M03"
        if "M" in date_str.upper():
            parts = date_str.upper().split("M")
            if len(parts) == 2:
                year = int(parts[0])
                month = int(parts[1])
                return datetime(year, month, 1)

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback: try to parse as integer year
        try:
            year = int(date_str)
            return datetime(year, 1, 1)
        except ValueError:
            raise ValueError(f"Cannot parse date: {date_str}")

    def aggregate(
        self,
        df: pd.DataFrame,
        target_freq: Optional[Literal["D", "W", "M", "Q", "Y"]] = None,
        agg_func: str = "mean",
    ) -> pd.DataFrame:
        """
        Aggregate data to lower frequency

        Args:
            df: DataFrame with datetime index
            target_freq: Target frequency (D=daily, W=weekly, M=monthly, Q=quarterly, Y=yearly)
            agg_func: Aggregation function (mean, sum, first, last)

        Returns:
            Aggregated DataFrame
        """
        if df.empty:
            return df

        if target_freq is None:
            # Auto-detect best frequency
            target_freq = self._auto_detect_frequency(df)

        # Resample
        resampled = df.resample(target_freq).agg(agg_func)

        # Remove NaN values
        resampled = resampled.dropna()

        logger.info(
            f"Aggregated {len(df)} points → {len(resampled)} points (freq={target_freq})"
        )

        return resampled

    def _auto_detect_frequency(self, df: pd.DataFrame) -> str:
        """
        Automatically detect best frequency to avoid context overflow

        Logic:
        - If >365 daily points → monthly
        - If >120 monthly points → yearly
        - Otherwise keep as is
        """
        num_points = len(df)

        # Detect current frequency
        if len(df) < 2:
            return "M"  # Default to monthly

        time_diff = (df.index[-1] - df.index[0]).days / len(df)

        # Daily data (average gap < 5 days)
        if time_diff < 5:
            if num_points > self.MAX_DAILY_POINTS:
                logger.info("Auto-detected: Daily data → Aggregating to Monthly")
                return "M"
            return "D"

        # Monthly data (average gap < 40 days)
        elif time_diff < 40:
            if num_points > self.MAX_MONTHLY_POINTS:
                logger.info("Auto-detected: Monthly data → Aggregating to Yearly")
                return "Y"
            return "M"

        # Quarterly or yearly
        else:
            return "Y"

    def to_dict(
        self,
        df: pd.DataFrame,
        include_stats: bool = True,
    ) -> Dict[str, Any]:
        """
        Convert DataFrame to dict format optimized for LLMs

        Args:
            df: DataFrame to convert
            include_stats: Include summary statistics

        Returns:
            Dictionary with data and optional stats
        """
        if df.empty:
            return {"data": [], "count": 0}

        result = {
            "data": [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "value": float(val) if not pd.isna(val) else None,
                }
                for idx, val in df["value"].items()
            ],
            "count": len(df),
            "first_date": df.index[0].strftime("%Y-%m-%d"),
            "last_date": df.index[-1].strftime("%Y-%m-%d"),
        }

        if include_stats and len(df) > 0:
            result["statistics"] = {
                "mean": float(df["value"].mean()),
                "median": float(df["value"].median()),
                "std": float(df["value"].std()),
                "min": float(df["value"].min()),
                "max": float(df["value"].max()),
                "change_pct": self._calculate_change(df),
            }

        return result

    def to_csv(self, df: pd.DataFrame) -> str:
        """Convert DataFrame to CSV string"""
        if df.empty:
            return "date,value\n"

        df_copy = df.copy()
        df_copy.index.name = "date"
        return df_copy.to_csv()

    def _calculate_change(self, df: pd.DataFrame) -> Optional[float]:
        """Calculate percentage change from first to last value"""
        if len(df) < 2:
            return None

        first_val = df["value"].iloc[0]
        last_val = df["value"].iloc[-1]

        if first_val == 0:
            return None

        return float(((last_val - first_val) / first_val) * 100)

    def process_series_data(
        self,
        raw_data: Dict[str, Any],
        auto_aggregate: bool = True,
        output_format: Literal["dict", "csv"] = "dict",
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Parse → Aggregate → Format

        This is the main function to use. It handles everything:
        1. Parse INE response into DataFrame
        2. Intelligently aggregate if needed
        3. Format for LLM consumption

        Args:
            raw_data: Raw INE API response
            auto_aggregate: Whether to auto-aggregate large datasets
            output_format: Output format (dict or csv)

        Returns:
            Processed data ready for LLM
        """
        # Parse
        df = self.parse_ine_data(raw_data)

        if df.empty:
            return {
                "error": "No data available",
                "count": 0,
            }

        # Aggregate if needed
        if auto_aggregate and len(df) > self.MAX_DAILY_POINTS:
            df = self.aggregate(df)

        # Format
        if output_format == "csv":
            return {
                "format": "csv",
                "data": self.to_csv(df),
                "count": len(df),
            }
        else:
            return self.to_dict(df, include_stats=True)
