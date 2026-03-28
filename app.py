"""
app.py
WHO Health Indicators Dashboard - West Africa (ECOWAS)
Automated data pipeline from WHO Global Health Observatory API.

Run: streamlit run app.py
"""

import streamlit as st
import plotly.express as px
from pipeline import load_all_indicators, get_latest_values, get_country_trend
from ai_module import load_summarizer, build_country_report, generate_insight, detect_regional_outliers
from config import INDICATORS, ECOWAS_COUNTRIES


# ── Page configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="WHO West Africa Health Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("WHO Health Indicators - West Africa (ECOWAS)")
st.caption(
    "Data source: WHO Global Health Observatory API | "
    "Coverage: 15 ECOWAS member states | "
    "6 core health indicators"
)
st.divider()


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_data():
    return load_all_indicators()


@st.cache_resource(show_spinner=False)
def get_summarizer():
    return load_summarizer()


with st.spinner("Fetching data from WHO Global Health Observatory..."):
    try:
        df = get_data()
        latest_df = get_latest_values(df)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.header("Settings")

indicator_labels = list(INDICATORS.values())
indicator_codes = list(INDICATORS.keys())
selected_label = st.sidebar.selectbox("Indicator", indicator_labels)
selected_indicator = indicator_codes[indicator_labels.index(selected_label)]

countries = sorted(ECOWAS_COUNTRIES.values())
selected_country = st.sidebar.selectbox(
    "Country",
    countries,
    index=countries.index("Niger")
)

st.sidebar.divider()
st.sidebar.caption("Data refreshed every hour from WHO GHO API.")


# ── Section 1: Regional comparison ───────────────────────────────────────────

st.subheader("Regional Comparison - Latest Available Year")

region_data = latest_df[latest_df["indicator_code"] == selected_indicator].copy()

if region_data.empty:
    st.warning(f"No data available for: {selected_label}")
else:
    region_data = region_data.sort_values("value", ascending=True)

    fig_bar = px.bar(
        region_data,
        x="value",
        y="country",
        orientation="h",
        title=f"{selected_label} - ECOWAS Countries",
        labels={"value": selected_label, "country": "Country"},
        color="value",
        color_continuous_scale="Blues",
        text="year"
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(
        coloraxis_showscale=False,
        yaxis_title=None,
        height=500
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()


# ── Section 2: Country time series ───────────────────────────────────────────

st.subheader(f"Historical Trend - {selected_country}")

trend_df = get_country_trend(df, selected_country, selected_indicator)

if trend_df.empty:
    st.warning(f"No historical data for {selected_country} on this indicator.")
else:
    fig_line = px.line(
        trend_df,
        x="year",
        y="value",
        title=f"{selected_label} - {selected_country}",
        labels={"year": "Year", "value": selected_label},
        markers=True
    )
    fig_line.update_traces(line_color="#1f77b4", marker_size=6)
    fig_line.update_layout(xaxis=dict(dtick=2))
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()


# ── Section 3: All indicators summary for selected country ────────────────────

st.subheader(f"All Indicators Summary - {selected_country}")

country_summary = latest_df[latest_df["country"] == selected_country][
    ["indicator", "value", "year"]
].rename(columns={"indicator": "Indicator", "value": "Latest Value", "year": "Year"})

if country_summary.empty:
    st.warning(f"No summary data available for {selected_country}.")
else:
    country_summary["Latest Value"] = country_summary["Latest Value"].round(2)
    st.dataframe(country_summary.reset_index(drop=True), use_container_width=True)

st.divider()


# ── Section 4: Regional outlier detection ────────────────────────────────────

st.subheader(f"Regional Outlier Analysis - {selected_label}")

outlier_df = detect_regional_outliers(df, selected_indicator)

if not outlier_df.empty:
    color_map = {
        "Above average": "#d62728",
        "Below average": "#2ca02c",
        "Within average range": "#1f77b4"
    }
    fig_outlier = px.scatter(
        outlier_df,
        x="country",
        y="value",
        color="regional_status",
        color_discrete_map=color_map,
        title=f"Country performance vs ECOWAS regional mean ({selected_label})",
        labels={"value": selected_label, "country": "Country"},
        hover_data=["year", "regional_mean"]
    )
    fig_outlier.add_hline(
        y=outlier_df["regional_mean"].iloc[0],
        line_dash="dash",
        line_color="gray",
        annotation_text="Regional mean"
    )
    fig_outlier.update_layout(xaxis_tickangle=45)
    st.plotly_chart(fig_outlier, use_container_width=True)

st.divider()


# ── Section 5: AI situation report ───────────────────────────────────────────

st.subheader(f"AI Situation Report - {selected_country}")

if st.button("Generate Situation Report"):
    with st.spinner("Generating report..."):
        try:
            summarizer = get_summarizer()
            report_text = build_country_report(df, selected_country)
            insight = generate_insight(summarizer, report_text)
            st.success(insight)
            with st.expander("View full data report"):
                st.write(report_text)
        except Exception as e:
            st.error(f"Report generation failed: {e}")

st.divider()
st.caption(
    "Built with Streamlit, Plotly, Hugging Face Transformers. "
    "Data: WHO Global Health Observatory (GHO OData API). "
    "Geographic scope: 15 ECOWAS member states."
)
