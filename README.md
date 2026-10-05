# WHO Health Indicators Dashboard - West Africa

### Which West African countries are falling behind on child mortality, malaria or maternal health, and is the gap closing?

Answering that today means opening the WHO Global Health Observatory, picking an
indicator, downloading a country at a time, and rebuilding the comparison by hand.

This project does it for you.

It pulls six core health indicators for 15 West African countries straight from
the WHO GHO API, cleans them, and shows where each country stands, how it got
there, and how far it sits from the regional average.

## What it does

1. **Fetches** the data from the WHO GHO API once a week, since WHO updates these
   estimates only a few times a year, with an offline fallback to the last good snapshot
2. **Cleans** it: national totals only (series broken down by sex, age or wealth
   are excluded so country figures stay valid), type checks, deduplication
3. **Shows** a country KPI profile, a regional map, a country ranking, historical
   trends and deviation from the regional mean
4. **Reports** a country situation summary, optionally condensed by a Hugging
   Face model
5. **Exports** to CSV for the R analysis: correlations, trend models, regional summary

## Indicators covered

| Indicator | WHO GHO code |
|---|---|
| Estimated malaria deaths (absolute count) | `MALARIA_EST_DEATHS` |
| Under-five mortality rate (per 1,000 live births) | `MDG_0000000007` |
| Maternal mortality ratio (per 100,000 live births) | `MDG_0000000026` |
| Nurses and midwives (per 10,000 population) | `HWF_0006` |
| Tuberculosis incidence (per 100,000 population) | `MDG_0000000020` |
| Wasting prevalence in children under 5 (%) | `NUTRITION_WH_2` |

## Countries covered

15 West African countries: the 12 ECOWAS members, plus Burkina Faso, Mali and Niger,
which left ECOWAS in January 2025. Benin, Burkina Faso, Cape Verde, Cote d'Ivoire,
Gambia, Ghana, Guinea, Guinea-Bissau, Liberia, Mali, Niger, Nigeria, Senegal,
Sierra Leone, Togo.

## Setup

```bash
git clone https://github.com/AbdelkaderYS/who-wa-dashboard.git
cd who-wa-dashboard
pip install -r requirements.txt
streamlit run app.py
```

Run the tests:

```bash
python test_pipeline.py
```

R analysis (optional):

```bash
python pipeline.py --export
Rscript r_analysis/analysis.R
```

## Project structure

```
who-wa-dashboard/
├── app.py              # Streamlit dashboard
├── pipeline.py         # WHO GHO API ingestion, cleaning, cache fallback
├── ai_module.py        # Situation reports and regional outlier detection
├── config.py           # Countries, indicators, KPI metadata
├── test_pipeline.py    # Pipeline unit tests
├── r_analysis/         # R statistical analysis (correlation, trends)
├── .streamlit/         # Dashboard theme
├── requirements.txt
└── README.md
```

## Data source

WHO Global Health Observatory OData API:
https://www.who.int/data/gho/info/gho-odata-api

## Technical stack

Streamlit, Plotly, Pandas, Requests, R (ggplot2, broom), and optionally
Hugging Face Transformers for report summarization.
