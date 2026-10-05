"""
ai_module.py
Automated situation reports and rule-based regional benchmarking
for West African health indicators.

The Hugging Face summarizer is optional: transformers/torch are imported
lazily so the dashboard runs without them installed.
"""

import pandas as pd


def load_summarizer():
    """
    Load a lightweight Hugging Face summarization model.
    sshleifer/distilbart-cnn-12-6 runs on CPU, no GPU required.

    Returns None if transformers/torch are not installed.
    """
    try:
        from transformers import pipeline
    except ImportError:
        return None

    summarizer = pipeline(
        "summarization",
        model="sshleifer/distilbart-cnn-12-6",
        device=-1
    )
    return summarizer


def build_country_report(df: pd.DataFrame, country: str) -> str:
    """
    Build a structured text situation report for a given country
    from all available indicators. This text feeds the AI summarizer.
    """
    country_df = df[df["country"] == country]
    if country_df.empty:
        return f"No health data available for {country}."

    lines = [f"Health situation report for {country} based on WHO Global Health Observatory data."]

    for indicator_code in country_df["indicator_code"].unique():
        ind_df = country_df[country_df["indicator_code"] == indicator_code].sort_values("year")
        if ind_df.empty:
            continue

        latest = ind_df.iloc[-1]
        indicator_label = latest["indicator"]
        latest_year = int(latest["year"])
        latest_value = round(float(latest["value"]), 2)

        line = (
            f"The {indicator_label} in {country} was {latest_value} in {latest_year}."
        )

        # Add trend if at least 2 data points
        if len(ind_df) >= 2:
            previous = ind_df.iloc[-2]
            prev_value = round(float(previous["value"]), 2)
            prev_year = int(previous["year"])
            change = round(latest_value - prev_value, 2)
            direction = "increased" if change > 0 else "decreased"
            line += f" This {direction} from {prev_value} in {prev_year}."

        lines.append(line)

    return " ".join(lines)


def generate_insight(summarizer, report_text: str) -> str:
    """
    Generate a concise AI summary from a situation report.
    Falls back gracefully for short texts or when no model is available.
    """
    if summarizer is None or len(report_text.split()) < 40:
        return report_text

    result = summarizer(
        report_text,
        max_length=100,
        min_length=40,
        do_sample=False
    )
    return result[0]["summary_text"]


def detect_regional_outliers(df: pd.DataFrame, indicator_code: str) -> pd.DataFrame:
    """
    Identify countries performing significantly above or below
    the regional average for a given indicator (latest year).

    Returns a DataFrame flagging each country as Above, Below, or Average.
    """
    ind_df = (
        df[df["indicator_code"] == indicator_code]
        .sort_values("year", ascending=False)
        .groupby(["country_code", "country"], as_index=False)
        .first()
    )

    if ind_df.empty:
        return pd.DataFrame()

    regional_mean = ind_df["value"].mean()
    regional_std = ind_df["value"].std()

    def classify(val):
        # std() is NaN with a single country and 0 with identical values:
        # no meaningful deviation in either case.
        if pd.isna(regional_std) or regional_std == 0:
            return "Within average range"
        z = (val - regional_mean) / regional_std
        if z > 1:
            return "Above average"
        elif z < -1:
            return "Below average"
        return "Within average range"

    ind_df["regional_status"] = ind_df["value"].apply(classify)
    ind_df["regional_mean"] = round(regional_mean, 2)
    return ind_df[["country", "value", "year", "regional_status", "regional_mean"]]
