"""
config.py
ECOWAS countries and WHO GHO indicator definitions.
"""

# 15 ECOWAS member states with ISO-3 codes used by WHO GHO API
ECOWAS_COUNTRIES = {
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
    "WHS4_100": "Nurses and midwives (per 10,000 population)",
    "WHS6_102": "Tuberculosis incidence (per 100,000 population)",
    "NUTRITION_ANT_WHZ_NE2": "Wasting prevalence in children under 5 (%)",
}

# WHO GHO OData API base URL
GHO_API_BASE = "https://ghoapi.azureedge.net/api"
