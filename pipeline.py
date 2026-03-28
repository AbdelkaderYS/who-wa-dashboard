"""
pipeline.py
Automated data ingestion and processing from WHO Global Health Observatory API.
Covers 15 ECOWAS member states across 6 health indicators.

WHO GHO OData API documentation:
https://www.who.int/data/gho/info/gho-odata-api
"""

import pandas as pd
import requests
from config import GHO_API_BASE, ECOWAS_COUNTRIES, INDICATORS


def fetch_indicator(indicator_code: str, country_codes: list[str]) -> pd.DataFrame:
    """
    Fetch a single WHO GHO indicator for a list of countries.

    The GHO OData API accepts OData $filter expressions.
    Example endpoint:
    https://ghoapi.azureedge.net/api/MALARIA_EST_DEATHS?$filter=SpatialDim in ('NER','MLI','BFA')

    Returns a clean DataFrame or raises RuntimeError on failure.
    """
    # Build OData filter for multiple countries
    country_list = ", ".join([f"'{code}'" for code in country_codes])
    odata_filter = f"SpatialDim in ({country_list})"

    url = f"{GHO_API_BASE}/{indicator_code}"
    params = {"$filter": odata_filter}

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch indicator {indicator_code}: {e}")
    except ValueError:
        raise RuntimeError(f"Invalid JSON response for indicator {indicator_code}")

    records = data.get("value", [])
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    return df


def clean_indicator(df: pd.DataFrame, indicator_code: str, indicator_label: str) -> pd.DataFrame:
    """
    Select and rename relevant columns from raw GHO response.
    Validates types and filters to country-level data only.
    """
    required_cols = ["SpatialDim", "TimeDim", "NumericValue"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {indicator_code}: {missing}")

    df = df[df["SpatialDimType"] == "COUNTRY"].copy()
    df = df[required_cols].copy()

    df.columns = ["country_code", "year", "value"]
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["year", "value"])
    df["year"] = df["year"].astype(int)

    # Map country codes to country names
    df["country"] = df["country_code"].map(ECOWAS_COUNTRIES)
    df = df.dropna(subset=["country"])

    df["indicator_code"] = indicator_code
    df["indicator"] = indicator_label

    return df[["country_code", "country", "year", "value", "indicator_code", "indicator"]]


def load_all_indicators() -> pd.DataFrame:
    """
    Full pipeline: fetch and clean all indicators for all ECOWAS countries.
    Returns a single long-format DataFrame.
    """
    country_codes = list(ECOWAS_COUNTRIES.keys())
    all_frames = []

    for code, label in INDICATORS.items():
        try:
            raw = fetch_indicator(code, country_codes)
            if raw.empty:
                continue
            clean = clean_indicator(raw, code, label)
            all_frames.append(clean)
        except (RuntimeError, ValueError):
            continue

    if not all_frames:
        raise RuntimeError("No data retrieved from WHO GHO API. Check your internet connection.")

    df = pd.concat(all_frames, ignore_index=True)
    df = df.sort_values(["indicator_code", "country", "year"]).reset_index(drop=True)
    return df


def get_latest_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each country/indicator combination, keep only the most recent year.
    Used for cross-country comparison charts.
    """
    latest = (
        df.sort_values("year", ascending=False)
        .groupby(["country_code", "country", "indicator_code", "indicator"], as_index=False)
        .first()
    )
    return latest


def get_country_trend(df: pd.DataFrame, country: str, indicator_code: str) -> pd.DataFrame:
    """
    Extract the full time series for one country and one indicator.
    """
    mask = (df["country"] == country) & (df["indicator_code"] == indicator_code)
    trend = df[mask].sort_values("year").reset_index(drop=True)
    return trend


def export_for_r(df: pd.DataFrame, path: str = "data/who_wa_indicators.csv") -> None:
    """
    Export the cleaned DataFrame to CSV for R-based statistical analysis.
    Creates the data/ directory if it does not exist.
    """
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Data exported to {path} ({len(df)} records)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true", help="Export data to CSV for R analysis")
    args = parser.parse_args()

    if args.export:
        print("Running pipeline and exporting data for R...")
        data = load_all_indicators()
        export_for_r(data)
        print("Done. Run: Rscript r_analysis/analysis.R")