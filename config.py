"""
config.py
West African countries and WHO GHO indicator definitions.
"""

# 15 West African countries: the 12 ECOWAS members, plus Burkina Faso, Mali and Niger,
# which left ECOWAS in January 2025. ISO-3 codes used by the WHO GHO API
WEST_AFRICA_COUNTRIES = {
    "BEN": "Benin",
    "BFA": "Burkina Faso",
    "CPV": "Cape Verde",
    "CIV": "Cote d'Ivoire",
    "GMB": "Gambia",
    "GHA": "Ghana",
    "GIN": "Guinea",
    "GNB": "Guinea-Bissau",
    "LBR": "Liberia",
    "MLI": "Mali",
    "NER": "Niger",
    "NGA": "Nigeria",
    "SEN": "Senegal",
    "SLE": "Sierra Leone",
    "TGO": "Togo",
}

# WHO GHO indicators relevant to West Africa health surveillance
INDICATORS = {
    "MALARIA_EST_DEATHS": "Estimated malaria deaths",
    "MDG_0000000007": "Under-five mortality rate (per 1,000 live births)",
    "MDG_0000000026": "Maternal mortality ratio (per 100,000 live births)",
    "HWF_0006": "Nurses and midwives (per 10,000 population)",
    "MDG_0000000020": "Tuberculosis incidence (per 100,000 population)",
    "NUTRITION_WH_2": "Wasting prevalence in children under 5 (%)",
}

# Compact labels and units for KPI cards
INDICATOR_META = {
    "MALARIA_EST_DEATHS": {
        "short": "Malaria deaths",
        "unit": "estimated deaths",
        "higher_is_better": False,
        "absolute_count": True,  # not population-normalized
    },
    "MDG_0000000007": {
        "short": "Under-5 mortality",
        "unit": "per 1,000 live births",
        "higher_is_better": False,
        "absolute_count": False,
    },
    "MDG_0000000026": {
        "short": "Maternal mortality",
        "unit": "per 100,000 live births",
        "higher_is_better": False,
        "absolute_count": False,
    },
    "HWF_0006": {
        "short": "Nurses & midwives",
        "unit": "per 10,000 population",
        "higher_is_better": True,
        "absolute_count": False,
    },
    "MDG_0000000020": {
        "short": "TB incidence",
        "unit": "per 100,000 population",
        "higher_is_better": False,
        "absolute_count": False,
    },
    "NUTRITION_WH_2": {
        "short": "Child wasting",
        "unit": "% of children under 5",
        "higher_is_better": False,
        "absolute_count": False,
    },
}

# WHO GHO OData API base URL
GHO_API_BASE = "https://ghoapi.azureedge.net/api"
