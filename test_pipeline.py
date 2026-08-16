"""
test_pipeline.py
Tests simples pour le pipeline WHO.
Lancer: python test_pipeline.py
"""

import os
import tempfile

import pandas as pd
from pipeline import clean_indicator, filter_national_totals, get_latest_values, merge_with_cache
from ai_module import detect_regional_outliers


def make_raw_df(rows):
    """Construit un DataFrame brut similaire à la réponse de l'API WHO."""
    return pd.DataFrame(rows, columns=[
        "SpatialDimType", "SpatialDim", "TimeDim", "NumericValue"
    ])


def test_filtre_sexe_btsx():
    """Un indicateur désagrégé par sexe doit garder uniquement SEX_BTSX (total)."""
    raw = pd.DataFrame([
        ("COUNTRY", "NER", 2020, 100.0, "SEX", "SEX_BTSX"),
        ("COUNTRY", "NER", 2020, 120.0, "SEX", "SEX_MLE"),
        ("COUNTRY", "NER", 2020, 80.0, "SEX", "SEX_FMLE"),
    ], columns=["SpatialDimType", "SpatialDim", "TimeDim", "NumericValue", "Dim1Type", "Dim1"])
    clean = clean_indicator(raw, "TEST", "Test indicator")
    assert len(clean) == 1, f"Attendu 1 ligne, obtenu {len(clean)}"
    assert clean["value"].iloc[0] == 100.0, \
        f"Attendu 100.0 (BTSX), obtenu {clean['value'].iloc[0]} (moyenne des sexes = bug)"
    print("[OK] test_filtre_sexe_btsx")


def test_prefere_dim_nulle():
    """Quand des lignes sans désagrégation existent, elles priment sur les totaux Dim1."""
    raw = pd.DataFrame([
        ("COUNTRY", "NER", 2020, 55.0, None, None),
        ("COUNTRY", "NER", 2020, 60.0, "AGEGROUP", "AGEGROUP_MONTHS0-11"),
        ("COUNTRY", "NER", 2020, 58.0, "SEX", "SEX_BTSX"),
    ], columns=["SpatialDimType", "SpatialDim", "TimeDim", "NumericValue", "Dim1Type", "Dim1"])
    filtered = filter_national_totals(raw)
    assert len(filtered) == 1
    assert filtered["NumericValue"].iloc[0] == 55.0
    print("[OK] test_prefere_dim_nulle")


def test_desagregation_sans_total_exclue():
    """Sans total reconnaissable, on ne renvoie rien plutôt que de moyenner."""
    raw = pd.DataFrame([
        ("COUNTRY", "NER", 2020, 120.0, "SEX", "SEX_MLE"),
        ("COUNTRY", "NER", 2020, 80.0, "SEX", "SEX_FMLE"),
    ], columns=["SpatialDimType", "SpatialDim", "TimeDim", "NumericValue", "Dim1Type", "Dim1"])
    filtered = filter_national_totals(raw)
    assert filtered.empty, "Les désagrégations sans total ne doivent pas être moyennées"
    print("[OK] test_desagregation_sans_total_exclue")


def test_clean_deduplique():
    """Quand l'API renvoie plusieurs valeurs pour la même année, on prend la moyenne."""
    raw = make_raw_df([
        ("COUNTRY", "NER", 2020, 100.0),
        ("COUNTRY", "NER", 2020, 120.0),
        ("COUNTRY", "NER", 2021, 90.0),
    ])
    clean = clean_indicator(raw, "TEST", "Test indicator")

    ner_2020 = clean[(clean["country"] == "Niger") & (clean["year"] == 2020)]
    assert len(ner_2020) == 1, f"Attendu 1 ligne, obtenu {len(ner_2020)}"
    assert ner_2020["value"].iloc[0] == 110.0, f"Attendu 110.0, obtenu {ner_2020['value'].iloc[0]}"
    print("[OK] test_clean_deduplique")


def test_clean_filtre_anciennes_annees():
    """Les donnees avant 1990 doivent etre filtrees."""
    raw = make_raw_df([
        ("COUNTRY", "NER", 1985, 300.0),
        ("COUNTRY", "NER", 2020, 100.0),
    ])
    clean = clean_indicator(raw, "TEST", "Test indicator")
    assert len(clean) == 1, f"Attendu 1 ligne, obtenu {len(clean)}"
    assert clean["year"].iloc[0] == 2020
    print("[OK] test_clean_filtre_anciennes_annees")


def test_clean_colonnes_manquantes():
    """Doit lever une ValueError si les colonnes requises manquent."""
    raw = pd.DataFrame([{"SpatialDim": "NER", "TimeDim": 2020}])
    try:
        clean_indicator(raw, "TEST", "Test indicator")
        assert False, "Devrait avoir leve une ValueError"
    except ValueError:
        print("[OK] test_clean_colonnes_manquantes")


def test_latest_values():
    """get_latest_values doit garder uniquement la derniere annee par pays/indicateur."""
    df = pd.DataFrame([
        ("NER", "Niger", 2019, 110.0, "TEST", "Test"),
        ("NER", "Niger", 2021, 90.0, "TEST", "Test"),
        ("NER", "Niger", 2020, 100.0, "TEST", "Test"),
    ], columns=["country_code", "country", "year", "value", "indicator_code", "indicator"])
    latest = get_latest_values(df)
    assert len(latest) == 1
    assert latest["year"].iloc[0] == 2021
    assert latest["value"].iloc[0] == 90.0
    print("[OK] test_latest_values")


def test_outliers():
    """detect_regional_outliers doit classer les pays par rapport a la moyenne."""
    rows = []
    values = [10, 12, 11, 13, 9, 50]  # 50 est un outlier
    countries = ["Benin", "Burkina Faso", "Cape Verde", "Gambia", "Ghana", "Nigeria"]
    for country, val in zip(countries, values):
        code = {"Benin": "BEN", "Burkina Faso": "BFA", "Cape Verde": "CPV",
                "Gambia": "GMB", "Ghana": "GHA", "Nigeria": "NGA"}[country]
        rows.append((code, country, 2023, float(val), "TEST", "Test"))
    df = pd.DataFrame(rows, columns=[
        "country_code", "country", "year", "value", "indicator_code", "indicator"
    ])
    result = detect_regional_outliers(df, "TEST")
    nigeria = result[result["country"] == "Nigeria"]
    assert nigeria["regional_status"].iloc[0] == "Above average"
    print("[OK] test_outliers")


def test_merge_cache_backfill():
    """Un fetch partiel ne doit pas faire disparaitre un indicateur du cache."""
    cols = ["country_code", "country", "year", "value", "indicator_code", "indicator"]
    cached = pd.DataFrame([
        ("NER", "Niger", 2020, 100.0, "A", "Indic A"),
        ("NER", "Niger", 2020, 50.0, "B", "Indic B"),
    ], columns=cols)
    fetched = pd.DataFrame([
        ("NER", "Niger", 2021, 90.0, "A", "Indic A"),
    ], columns=cols)

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cache.csv")
        cached.to_csv(path, index=False)
        merged = merge_with_cache(fetched, path)

    assert set(merged["indicator_code"]) == {"A", "B"}, "B doit etre repris du cache"
    a_rows = merged[merged["indicator_code"] == "A"]
    assert len(a_rows) == 1 and a_rows["year"].iloc[0] == 2021, "A doit venir de l'API"
    print("[OK] test_merge_cache_backfill")


def test_outliers_pays_unique():
    """Avec un seul pays, std est NaN : tout doit être 'Within average range'."""
    df = pd.DataFrame(
        [("NER", "Niger", 2023, 100.0, "TEST", "Test")],
        columns=["country_code", "country", "year", "value", "indicator_code", "indicator"],
    )
    result = detect_regional_outliers(df, "TEST")
    assert result["regional_status"].iloc[0] == "Within average range"
    print("[OK] test_outliers_pays_unique")


if __name__ == "__main__":
    test_filtre_sexe_btsx()
    test_prefere_dim_nulle()
    test_desagregation_sans_total_exclue()
    test_merge_cache_backfill()
    test_outliers_pays_unique()
    test_clean_deduplique()
    test_clean_filtre_anciennes_annees()
    test_clean_colonnes_manquantes()
    test_latest_values()
    test_outliers()
    print("\nTous les tests sont passes.")
