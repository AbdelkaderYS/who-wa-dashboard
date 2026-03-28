# WHO Health Indicators Dashboard - West Africa (ECOWAS)

Automated data pipeline and interactive dashboard for WHO health indicators
across the 15 ECOWAS member states.

## What this project does

1. Fetches health indicator data in real-time from the WHO Global Health Observatory API
2. Cleans and validates the data automatically
3. Displays regional comparisons, historical trends, and outlier analysis
4. Generates AI-powered country situation reports using a Hugging Face model

## Indicators covered

- Estimated malaria deaths
- Under-five mortality rate
- Maternal mortality ratio
- Nurses and midwives per 10,000 population
- Tuberculosis incidence
- Wasting prevalence in children under 5

## Countries covered

All 15 ECOWAS member states: Benin, Burkina Faso, Cape Verde, Cote d'Ivoire,
Gambia, Ghana, Guinea, Guinea-Bissau, Liberia, Mali, Niger, Nigeria, Senegal,
Sierra Leone, Togo.

## Setup

```bash
git clone https://github.com/AbdelkaderYS/who-wa-dashboard.git
cd who-wa-dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```
who-wa-dashboard/
├── app.py          # Streamlit dashboard
├── pipeline.py     # WHO GHO API ingestion, cleaning, aggregation
├── ai_module.py    # Situation report generation and outlier detection
├── config.py       # Countries and indicator definitions
├── requirements.txt
└── README.md
```

## Data source

WHO Global Health Observatory OData API:
https://www.who.int/data/gho/info/gho-odata-api

## Technical stack

- Streamlit: interactive dashboard
- Plotly: data visualization
- Pandas: data pipeline and processing
- Requests: automated API ingestion
- Hugging Face Transformers: AI situation report generation
