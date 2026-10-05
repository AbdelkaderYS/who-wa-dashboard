"""
pipeline.py
Automated data ingestion and processing from WHO Global Health Observatory API.
Covers 15 West African countries across 6 health indicators.

WHO GHO OData API documentation:
https://www.who.int/data/gho/info/gho-odata-api
"""

import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from config import GHO_API_BASE, WEST_AFRICA_COUNTRIES, INDICATORS

CACHE_PATH = "data/who_wa_indicators.csv"

# Some indicators (e.g. survey-based nutrition series) return tens of thousands
# of rows for 15 countries, so the read timeout has to be generous.
REQUEST_TIMEOUT = 90

# Dim1 values that represent a national total (both sexes, all ages, all groups).
# WHO GHO disaggregates many indicators by sex, age group, wealth quintile, etc.
# Averaging across disaggregations produces invalid national figures, so we keep
# only total rows (or rows with no disaggregation at all).
TOTAL_DIM_VALUES = {
    "SEX_BTSX",
    "AGEGROUP_YEARSALL",
    "RESIDENCEAREATYPE_TOTL",
    "EDUCATIONLEVEL_TOTL",
    "HOUSEHOLDWEALTH_TOTL",
    "WEALTHQUINTILE_TOTL",
    "WEALTHDECILE_TOTL",
    "WEALTHTERCILE_TOTL",
}


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
        for attempt in range(3):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                break
            except requests.exceptions.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch indicator {indicator_code}: {e}")
    except ValueError:
        raise RuntimeError(f"Invalid JSON response for indicator {indicator_code}")

    records = data.get("value", [])
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    return df


def fetch_indicator_resilient(indicator_code: str, country_codes: list[str]) -> pd.DataFrame:
    """
    Fetch an indicator, retrying country by country if the batch request fails.

    Some GHO endpoints return HTTP 504 on a 15-country OData filter but answer
    fine for a single country, so a batch failure must not drop the indicator.
    """
    try:
        return fetch_indicator(indicator_code, country_codes)
    except RuntimeError as e:
        print(f"[pipeline] {indicator_code} : requête groupée échouée ({e}), "
              f"reprise pays par pays")

    frames = []
    for code in country_codes:
        try:
            part = fetch_indicator(indicator_code, [code])
            if not part.empty:
                frames.append(part)
        except RuntimeError:
            continue

    if not frames:
        raise RuntimeError(f"Failed to fetch indicator {indicator_code} for any country")
    return pd.concat(frames, ignore_index=True)


def filter_national_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only rows representing national totals.

    Preference order:
    1. Rows with no disaggregation (Dim1 is null) when the indicator has any.
    2. Otherwise rows whose Dim1 is an explicit total (e.g. SEX_BTSX).

    Prevents averaging across sex/age/wealth disaggregations, which would
    produce invalid national values.
    """
    if "Dim1" not in df.columns:
        return df

    dim1 = df["Dim1"]
    no_dim = df[dim1.isna()]
    if not no_dim.empty:
        return no_dim

    totals = df[dim1.isin(TOTAL_DIM_VALUES)]
    if not totals.empty:
        # An indicator may carry several total dimensions (e.g. SEX_BTSX and
        # AGEGROUP_YEARSALL); keep a single one to avoid duplicate rows.
        first_total = totals["Dim1"].iloc[0]
        return totals[totals["Dim1"] == first_total]

    # No recognizable total: safer to return nothing than to average
    # disaggregated values.
    return df.iloc[0:0]


def clean_indicator(df: pd.DataFrame, indicator_code: str, indicator_label: str) -> pd.DataFrame:
    """
    Select and rename relevant columns from raw GHO response.
    Validates types, keeps national totals only, filters to country-level data.
    """
    required_cols = ["SpatialDimType", "SpatialDim", "TimeDim", "NumericValue"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {indicator_code}: {missing}")

    df = df[df["SpatialDimType"] == "COUNTRY"].copy()
    df = filter_national_totals(df)

    df = df[["SpatialDim", "TimeDim", "NumericValue"]].copy()
    df.columns = ["country_code", "year", "value"]
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["year", "value"])
    df["year"] = df["year"].astype(int)

    df = df[df["year"] >= 1990]

    df = df.groupby(["country_code", "year"], as_index=False)["value"].mean()

    # Map country codes to country names
    df["country"] = df["country_code"].map(WEST_AFRICA_COUNTRIES)
    df = df.dropna(subset=["country"])

    df["indicator_code"] = indicator_code
    df["indicator"] = indicator_label

    return df[["country_code", "country", "year", "value", "indicator_code", "indicator"]]


def load_all_indicators() -> pd.DataFrame:
    """
    Full pipeline: fetch and clean all indicators for all 15 countries.
    Returns a single long-format DataFrame. Raises RuntimeError if nothing
    could be fetched.
    """
    country_codes = list(WEST_AFRICA_COUNTRIES.keys())
    all_frames = []

    for code, label in INDICATORS.items():
        try:
            raw = fetch_indicator_resilient(code, country_codes)
            if raw.empty:
                continue
            clean = clean_indicator(raw, code, label)
            all_frames.append(clean)
        except (RuntimeError, ValueError) as e:
            print(f"[pipeline] {code} ignoré : {e}")
            continue

    if not all_frames:
        raise RuntimeError("No data retrieved from WHO GHO API. Check your internet connection.")

    df = pd.concat(all_frames, ignore_index=True)
    df = df.sort_values(["indicator_code", "country", "year"]).reset_index(drop=True)
    return df


def read_cache(path: str = CACHE_PATH) -> pd.DataFrame:
    """Read the local snapshot, or an empty DataFrame if there is none."""
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def merge_with_cache(df: pd.DataFrame, path: str = CACHE_PATH) -> pd.DataFrame:
    """
    Backfill indicators the API did not return with their cached values.

    A partial fetch (some indicators timing out) must never shrink the dataset:
    without this, one slow endpoint would silently drop an indicator from the
    dashboard and overwrite the good snapshot.
    """
    cached = read_cache(path)
    if cached.empty:
        return df

    missing = set(cached["indicator_code"]) - set(df["indicator_code"])
    if not missing:
        return df

    print(f"[pipeline] indicateurs repris du cache : {sorted(missing)}")
    backfill = cached[cached["indicator_code"].isin(missing)]
    return pd.concat([df, backfill], ignore_index=True)


def load_with_fallback() -> tuple[pd.DataFrame, dict]:
    """
    Load data from the WHO GHO API, falling back to the local CSV cache when
    the API is unreachable, and backfilling any indicator the API dropped.

    Returns (df, meta) where meta contains:
      - source: "api", "partial" or "cache"
      - updated_at: ISO timestamp of the data snapshot
    """
    try:
        df = load_all_indicators()
        complete = set(df["indicator_code"]) >= set(INDICATORS)
        df = merge_with_cache(df)
        save_cache(df)
        meta = {
            "source": "api" if complete else "partial",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return df, meta
    except RuntimeError:
        cached = read_cache()
        if not cached.empty:
            mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_PATH), tz=timezone.utc)
            return cached, {"source": "cache", "updated_at": mtime.isoformat()}
        raise


def save_cache(df: pd.DataFrame, path: str = CACHE_PATH) -> None:
    """Persist the cleaned dataset locally (offline fallback + R analysis input)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


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


def export_for_r(df: pd.DataFrame, path: str = CACHE_PATH) -> None:
    """
    Export the cleaned DataFrame to CSV for R-based statistical analysis.
    Creates the data/ directory if it does not exist.
    """
    save_cache(df, path)
    print(f"Data exported to {path} ({len(df)} records)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true", help="Export data to CSV for R analysis")
    args = parser.parse_args()

    if args.export:
        print("Running pipeline and exporting data for R...")
        data, meta = load_with_fallback()
        export_for_r(data)
        if meta["source"] == "partial":
            print("Warning: some indicators came from the local cache, not the API.")
        print("Done. Run: Rscript r_analysis/analysis.R")
