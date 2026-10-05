"""
app.py
WHO Health Indicators Dashboard - West Africa
Institutional-style dashboard on top of the WHO Global Health Observatory API.

Run: streamlit run app.py
"""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_module import build_country_report, generate_insight, load_summarizer
from config import WEST_AFRICA_COUNTRIES, INDICATOR_META, INDICATORS
from pipeline import get_country_trend, get_latest_values, load_with_fallback

# ── Design tokens ─────────────────────────────────────────────────────────────

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

NAVY = "#0d366b"          # header band / dark accent
ACCENT = "#1c5cab"        # primary blue
SERIES_BLUE = "#2a78d6"   # main series color
DEEMPH_GRAY = "#c3c2b7"   # de-emphasized bars
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
GOOD = "#006300"
BAD = "#d03b3b"

SEQ_BLUES = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec",
    "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab",
    "#184f95", "#104281", "#0d366b",
]


def style_fig(fig, height=420):
    """Shared institutional chart styling: recessive grid, system sans, no chrome."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK_2),
        margin=dict(l=8, r=16, t=8, b=8),
        height=height,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID,
                        font=dict(family=FONT, size=12, color=INK)),
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE,
                     tickfont=dict(color=MUTED, size=12), title_font=dict(color=MUTED, size=12))
    fig.update_yaxes(gridcolor=GRID, linecolor=BASELINE, zerolinecolor=BASELINE,
                     tickfont=dict(color=MUTED, size=12), title_font=dict(color=MUTED, size=12))
    return fig


def fmt_value(v: float) -> str:
    """Compact number formatting for KPI cards and labels."""
    if abs(v) >= 10000:
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:,.1f}".rstrip("0").rstrip(".")
    return f"{v:,.2f}".rstrip("0").rstrip(".")


# ── Page configuration & CSS ─────────────────────────────────────────────────

st.set_page_config(
    page_title="WHO West Africa Health Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
      #MainMenu, footer {{visibility: hidden;}}
      header[data-testid="stHeader"] {{background: transparent;}}
      .block-container {{padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px;}}

      /* White cards for bordered containers (Power BI-style tiles) */
      div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: #ffffff;
        border: 1px solid rgba(11, 11, 11, 0.08) !important;
        border-radius: 10px;
        box-shadow: 0 1px 2px rgba(13, 54, 107, 0.06);
      }}

      /* Header band */
      .who-header {{
        background: linear-gradient(90deg, {NAVY} 0%, {ACCENT} 100%);
        border-radius: 10px;
        padding: 22px 28px 18px 28px;
        color: #ffffff;
        margin-bottom: 14px;
      }}
      .who-header h1 {{
        font-family: {FONT};
        font-size: 1.45rem; font-weight: 700; margin: 0; color: #ffffff;
      }}
      .who-header .sub {{
        font-size: 0.85rem; color: rgba(255,255,255,0.85); margin-top: 4px;
      }}
      .who-badge {{
        display: inline-block; font-size: 0.75rem; font-weight: 600;
        padding: 3px 10px; border-radius: 999px; margin-top: 10px;
        background: rgba(255,255,255,0.15); color: #ffffff;
      }}

      /* KPI cards */
      .kpi-row {{display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 4px;}}
      .kpi-card {{
        flex: 1 1 200px; background: #ffffff;
        border: 1px solid rgba(11,11,11,0.08); border-left: 4px solid {ACCENT};
        border-radius: 10px; padding: 14px 16px 12px 16px;
        box-shadow: 0 1px 2px rgba(13, 54, 107, 0.06);
        font-family: {FONT};
      }}
      .kpi-label {{
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em;
        text-transform: uppercase; color: {MUTED}; margin-bottom: 6px;
      }}
      .kpi-value {{font-size: 1.7rem; font-weight: 700; color: {INK}; line-height: 1.1;}}
      .kpi-unit {{font-size: 0.72rem; color: {MUTED}; margin-top: 2px;}}
      .kpi-delta {{font-size: 0.78rem; font-weight: 600; margin-top: 8px;}}
      .kpi-delta .year {{font-weight: 400; color: {MUTED};}}

      .card-title {{
        font-family: {FONT}; font-size: 0.95rem; font-weight: 700;
        color: {INK}; margin: 2px 0 0 2px;
      }}
      .card-sub {{font-size: 0.78rem; color: {MUTED}; margin: 0 0 6px 2px;}}

      /* ---- Sidebar ---- */
      section[data-testid="stSidebar"] {{
        background: #ffffff;
        border-right: 1px solid rgba(11,11,11,0.08);
        width: 300px !important;
      }}
      section[data-testid="stSidebar"] > div {{
        padding: 1.2rem 1.1rem 2rem 1.1rem;
        overflow-x: hidden;
      }}
      /* Slider thumb values were clipping outside the sidebar: give them room */
      section[data-testid="stSidebar"] div[data-testid="stSlider"] {{
        padding: 26px 6px 4px 6px;
      }}
      section[data-testid="stSidebar"] div[data-testid="stSliderThumbValue"] {{
        font-size: 0.72rem; color: {INK_2}; white-space: nowrap;
      }}
      section[data-testid="stSidebar"] div[data-testid="stSliderTickBarMin"],
      section[data-testid="stSidebar"] div[data-testid="stSliderTickBarMax"] {{
        font-size: 0.68rem; color: {MUTED};
      }}
      /* Keep long indicator names inside the select boxes */
      section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        font-size: 0.83rem;
      }}
      section[data-testid="stSidebar"] div[data-baseweb="select"] div[title] {{
        white-space: normal; line-height: 1.25; overflow-wrap: anywhere;
      }}
      section[data-testid="stSidebar"] label {{
        font-size: 0.78rem; font-weight: 600; color: {INK_2};
      }}
      .sidebar-title {{
        font-family: {FONT}; font-size: 0.95rem; font-weight: 700;
        color: {INK}; margin: 0 0 10px 0;
        padding-bottom: 8px; border-bottom: 2px solid {ACCENT};
      }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)  # WHO updates a few times a year
def get_data():
    df, meta = load_with_fallback()
    return df, meta


@st.cache_resource(show_spinner=False)
def get_summarizer():
    return load_summarizer()


with st.spinner("Fetching data from WHO Global Health Observatory..."):
    try:
        df, meta = get_data()
        latest_df = get_latest_values(df)
    except RuntimeError as e:
        st.error(str(e))
        st.stop()


# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.markdown('<div class="sidebar-title">Filters</div>', unsafe_allow_html=True)

indicator_labels = list(INDICATORS.values())
indicator_codes = list(INDICATORS.keys())
selected_label = st.sidebar.selectbox("Indicator", indicator_labels)
selected_indicator = indicator_codes[indicator_labels.index(selected_label)]
selected_meta = INDICATOR_META[selected_indicator]

countries = sorted(WEST_AFRICA_COUNTRIES.values())
selected_country = st.sidebar.selectbox("Country", countries, index=countries.index("Niger"))

year_min, year_max = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider("Period", year_min, year_max, (year_min, year_max))

st.sidebar.divider()
st.sidebar.caption(
    "**Source** - WHO Global Health Observatory (GHO OData API). "
    "Data checked weekly; cached snapshot used when the API is unreachable."
)

df_period = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]


# ── Header band ───────────────────────────────────────────────────────────────

updated = datetime.fromisoformat(meta["updated_at"]).strftime("%d %b %Y, %H:%M UTC")
if meta["source"] == "api":
    badge = f"● Live - WHO GHO API · updated {updated}"
elif meta["source"] == "partial":
    badge = f"◑ Partial refresh - some indicators from cache · {updated}"
else:
    badge = f"◐ Offline mode - cached snapshot from {updated}"

st.markdown(
    f"""
    <div class="who-header">
      <h1>Health Indicators - West Africa</h1>
      <div class="sub">Regional health monitoring · 15 member states · 6 core indicators ·
      Data: WHO Global Health Observatory</div>
      <span class="who-badge">{badge}</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── KPI strip: selected country, all indicators ───────────────────────────────

cards_html = []
country_latest = latest_df[latest_df["country"] == selected_country]

for code in indicator_codes:
    m = INDICATOR_META[code]
    row = country_latest[country_latest["indicator_code"] == code]
    if row.empty:
        cards_html.append(
            f'<div class="kpi-card"><div class="kpi-label">{m["short"]}</div>'
            f'<div class="kpi-value" style="color:{MUTED}">-</div>'
            f'<div class="kpi-unit">no data</div></div>'
        )
        continue

    latest_row = row.iloc[0]
    value, year = float(latest_row["value"]), int(latest_row["year"])

    # Delta vs previous available data point
    series = get_country_trend(df, selected_country, code)
    delta_html = '<span class="year">single data point</span>'
    if len(series) >= 2:
        prev = series.iloc[-2]
        prev_val, prev_year = float(prev["value"]), int(prev["year"])
        if prev_val != 0:
            pct = (value - prev_val) / abs(prev_val) * 100
            improved = (pct < 0) != m["higher_is_better"] if pct != 0 else None
            arrow = "▲" if pct > 0 else "▼"
            color = MUTED if improved is None else (GOOD if improved else BAD)
            delta_html = (
                f'<span style="color:{color}">{arrow} {abs(pct):.1f}%</span> '
                f'<span class="year">vs {prev_year}</span>'
            )

    cards_html.append(
        f'<div class="kpi-card"><div class="kpi-label">{m["short"]}</div>'
        f'<div class="kpi-value">{fmt_value(value)}</div>'
        f'<div class="kpi-unit">{m["unit"]} · {year}</div>'
        f'<div class="kpi-delta">{delta_html}</div></div>'
    )

st.markdown(
    f'<div class="card-title" style="margin-bottom:8px">Country profile - {selected_country}</div>'
    f'<div class="kpi-row">{"".join(cards_html)}</div>',
    unsafe_allow_html=True,
)
st.markdown("")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_region, tab_trends, tab_data = st.tabs(
    ["  Where each country stands  ", "  How it changed  ", "  Data  "]
)

region_latest = latest_df[latest_df["indicator_code"] == selected_indicator].copy()


# ── Tab 1: Regional overview (map + ranked bar) ──────────────────────────────

with tab_region:
    if region_latest.empty:
        st.warning(f"No data available for: {selected_label}")
    else:
        col_map, col_bar = st.columns([1.1, 1], gap="small")

        with col_map:
            with st.container(border=True):
                st.markdown(f'<div class="card-title">{selected_label}</div>'
                            f'<div class="card-sub">Latest available year per country</div>',
                            unsafe_allow_html=True)
                fig_map = px.choropleth(
                    region_latest,
                    locations="country_code",
                    color="value",
                    hover_name="country",
                    hover_data={"country_code": False, "value": ":,.1f", "year": True},
                    color_continuous_scale=SEQ_BLUES,
                    labels={"value": selected_meta["short"], "year": "Year"},
                )
                fig_map.update_geos(
                    fitbounds="locations", visible=False,
                    bgcolor="rgba(0,0,0,0)", showframe=False,
                    showcountries=True, countrycolor=GRID,
                )
                style_fig(fig_map, height=430)
                fig_map.update_layout(
                    coloraxis_colorbar=dict(
                        title=None, thickness=10, len=0.7,
                        tickfont=dict(color=MUTED, size=11),
                    ),
                    margin=dict(l=0, r=0, t=0, b=0),
                )
                st.plotly_chart(fig_map, use_container_width=True)

        with col_bar:
            with st.container(border=True):
                mean_val = region_latest["value"].mean()
                st.markdown(f'<div class="card-title">Country ranking</div>'
                            f'<div class="card-sub">{selected_country} highlighted · '
                            f'dashed line = regional mean ({fmt_value(mean_val)})</div>',
                            unsafe_allow_html=True)
                ranked = region_latest.sort_values("value", ascending=True)
                colors = [ACCENT if c == selected_country else DEEMPH_GRAY for c in ranked["country"]]
                fig_bar = go.Figure(go.Bar(
                    x=ranked["value"], y=ranked["country"], orientation="h",
                    marker=dict(color=colors, cornerradius=4),
                    text=[fmt_value(v) for v in ranked["value"]],
                    textposition="outside",
                    textfont=dict(color=INK_2, size=11),
                    hovertemplate="<b>%{y}</b><br>%{x:,.1f} (%{customdata})<extra></extra>",
                    customdata=ranked["year"],
                ))
                fig_bar.add_vline(x=mean_val, line_dash="dash", line_color=MUTED, line_width=1)
                style_fig(fig_bar, height=430)
                fig_bar.update_xaxes(showgrid=True, title=None,
                                     range=[0, ranked["value"].max() * 1.22])
                fig_bar.update_yaxes(showgrid=False, title=None)
                st.plotly_chart(fig_bar, use_container_width=True)

        if selected_meta["absolute_count"]:
            st.caption(
                "This indicator is an absolute count, not population-adjusted: "
                "larger countries naturally rank higher."
            )


# ── Tab 2: Country trends ────────────────────────────────────────────────────

with tab_trends:
    trend_df = get_country_trend(df_period, selected_country, selected_indicator)

    with st.container(border=True):
        st.markdown(f'<div class="card-title">{selected_label} - {selected_country}</div>'
                    f'<div class="card-sub">{year_range[0]}-{year_range[1]}</div>',
                    unsafe_allow_html=True)
        if trend_df.empty:
            st.warning(f"No historical data for {selected_country} on this indicator.")
        else:
            fig_line = go.Figure(go.Scatter(
                x=trend_df["year"], y=trend_df["value"],
                mode="lines+markers",
                line=dict(color=SERIES_BLUE, width=2),
                marker=dict(size=7, color=SERIES_BLUE),
                hovertemplate="<b>%{x}</b><br>%{y:,.1f}<extra></extra>",
            ))
            style_fig(fig_line, height=380)
            fig_line.update_xaxes(dtick=2, title=None)
            fig_line.update_yaxes(title=None, rangemode="tozero")
            st.plotly_chart(fig_line, use_container_width=True)

    st.markdown('<div class="card-title" style="margin:10px 0 8px 2px">All indicators - '
                f'{selected_country}</div>', unsafe_allow_html=True)

    small_cols = st.columns(3, gap="small")
    for i, code in enumerate(indicator_codes):
        m = INDICATOR_META[code]
        s = get_country_trend(df_period, selected_country, code)
        with small_cols[i % 3]:
            with st.container(border=True):
                if s.empty:
                    st.markdown(f'<div class="card-title">{m["short"]}</div>'
                                f'<div class="card-sub">no data</div>', unsafe_allow_html=True)
                    continue
                last = s.iloc[-1]
                st.markdown(
                    f'<div class="card-title">{m["short"]} · '
                    f'{fmt_value(float(last["value"]))}</div>'
                    f'<div class="card-sub">{m["unit"]} · {int(last["year"])}</div>',
                    unsafe_allow_html=True)
                fig_s = go.Figure(go.Scatter(
                    x=s["year"], y=s["value"], mode="lines",
                    line=dict(color=SERIES_BLUE, width=2),
                    fill="tozeroy", fillcolor="rgba(42, 120, 214, 0.08)",
                    hovertemplate="<b>%{x}</b><br>%{y:,.1f}<extra></extra>",
                ))
                style_fig(fig_s, height=150)
                fig_s.update_xaxes(showgrid=False, title=None, nticks=5)
                fig_s.update_yaxes(showgrid=False, title=None, nticks=4)
                st.plotly_chart(fig_s, use_container_width=True)


# ── Tab 3: Data ──────────────────────────────────────────────────────────────

with tab_data:
    col_left, col_right = st.columns([1.2, 1], gap="small")

    with col_left:
        with st.container(border=True):
            st.markdown('<div class="card-title">Dataset</div>'
                        f'<div class="card-sub">{len(df):,} records · '
                        f'{df["country"].nunique()} countries · '
                        f'{df["indicator_code"].nunique()} indicators</div>',
                        unsafe_allow_html=True)
            st.dataframe(
                df_period[["country", "year", "indicator", "value"]]
                .sort_values(["indicator", "country", "year"]),
                use_container_width=True, hide_index=True, height=340,
            )
            st.download_button(
                "Download CSV",
                df.to_csv(index=False).encode("utf-8"),
                file_name="who_wa_indicators.csv",
                mime="text/csv",
            )

    with col_right:
        with st.container(border=True):
            st.markdown(f'<div class="card-title">Situation report - {selected_country}</div>'
                        '<div class="card-sub">Summary of the latest values across '
                        'all indicators</div>', unsafe_allow_html=True)
            if st.button("Generate report"):
                with st.spinner("Generating report..."):
                    try:
                        report_text = build_country_report(df, selected_country)
                        summarizer = get_summarizer()
                        insight = generate_insight(summarizer, report_text)
                        st.success(insight)
                    except Exception as e:
                        st.error(f"Report generation failed: {e}")

        with st.container(border=True):
            if os.path.exists("outputs/correlation_matrix.png"):
                st.image("outputs/correlation_matrix.png",
                         caption="How the indicators move together (R analysis)")
            else:
                st.info("Run: Rscript r_analysis/analysis.R to generate this chart.")



# ── Footer ────────────────────────────────────────────────────────────────────

st.caption(
    "WHO Global Health Observatory (GHO OData API) · 15 West African countries · "
    "Built with Streamlit, Plotly and R · National totals only (disaggregated "
    "series excluded at ingestion)."
)
