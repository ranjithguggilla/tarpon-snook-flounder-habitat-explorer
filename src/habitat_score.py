from __future__ import annotations

import geopandas as gpd
import numpy as np


SPECIES_RULES = {
    "Tarpon": {
        "salinity": (12.0, 28.0),
        "temp": (24.0, 32.0),
        "depth": (0.5, 3.0),
        "months": {5, 6, 7, 8, 9},
        "preferred_habitats": {"marsh", "seagrass"},
    },
    "Snook": {
        "salinity": (15.0, 32.0),
        "temp": (22.0, 32.0),
        "depth": (0.8, 4.0),
        "months": {4, 5, 6, 7, 8, 9, 10},
        "preferred_habitats": {"marsh", "shoreline"},
    },
    "Southern Flounder": {
        "salinity": (20.0, 35.0),
        "temp": (14.0, 27.0),
        "depth": (1.5, 6.0),
        "months": {10, 11, 12, 1, 2, 3},
        "preferred_habitats": {"seagrass", "shoreline"},
    },
}


def _range_score(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 1.0
    if value < low:
        span = max(low, 1e-6)
        return max(0.0, 1.0 - (low - value) / span)
    span = max(high, 1e-6)
    return max(0.0, 1.0 - (value - high) / span)


def _distance_score(value_km: float, best_km: float, cutoff_km: float) -> float:
    if value_km <= best_km:
        return 1.0
    if value_km >= cutoff_km:
        return 0.0
    return 1.0 - ((value_km - best_km) / max(cutoff_km - best_km, 1e-6))


def _season_bucket(month: int) -> str:
    if month in {12, 1, 2}:
        return "Winter"
    if month in {3, 4, 5}:
        return "Spring"
    if month in {6, 7, 8}:
        return "Summer"
    return "Fall"


def score_sites(
    sites: gpd.GeoDataFrame,
    species: str,
    month: int,
) -> gpd.GeoDataFrame:
    rules = SPECIES_RULES[species]
    scored = sites.copy()

    habitat_pref = scored["shoreline_habitat"].isin(rules["preferred_habitats"]).astype(float)
    habitat_context = (
        scored["in_estuary"].astype(float) * 0.5
        + habitat_pref * 0.5
    )

    env_sal = scored["salinity_psu"].apply(
        lambda v: _range_score(v, rules["salinity"][0], rules["salinity"][1])
    )
    env_temp = scored["temp_c"].apply(
        lambda v: _range_score(v, rules["temp"][0], rules["temp"][1])
    )
    env_do = scored["dissolved_oxygen_mg_l"].apply(lambda v: _range_score(v, 4.8, 9.0))
    env_depth = scored["depth_m"].apply(
        lambda v: _range_score(v, rules["depth"][0], rules["depth"][1])
    )
    env_component = (env_sal * 0.35) + (env_temp * 0.35) + (env_do * 0.10) + (env_depth * 0.20)

    if species == "Southern Flounder":
        inlet_component = scored["dist_to_inlet_km"].apply(lambda d: _distance_score(d, 2.0, 25.0))
    else:
        inlet_component = scored["dist_to_inlet_km"].apply(lambda d: _distance_score(d, 1.0, 18.0))

    season_match = float(month in rules["months"])
    season_bucket = _season_bucket(month)
    season_window_match = (scored["season_window"] == season_bucket).astype(float)
    seasonal_component = (season_match * 0.7) + (season_window_match * 0.3)

    total_score = (
        habitat_context * 35.0
        + env_component * 35.0
        + inlet_component * 20.0
        + seasonal_component * 10.0
    )

    scored["species"] = species
    scored["month"] = month
    scored["habitat_score"] = np.clip(total_score, 0, 100).round(1)
    scored["priority"] = np.select(
        [scored["habitat_score"] >= 75, scored["habitat_score"] >= 50],
        ["High", "Medium"],
        default="Low",
    )

    reasons = []
    for _, row in scored.iterrows():
        parts = []
        if bool(row["in_estuary"]):
            parts.append("within estuary context")
        if row["shoreline_habitat"] in rules["preferred_habitats"]:
            parts.append(f"near preferred {row['shoreline_habitat']} habitat")
        if row["dist_to_inlet_km"] <= 6:
            parts.append("close to inlet corridor")
        if row["season_window"] == season_bucket:
            parts.append("aligned with seasonal window")
        if not parts:
            parts.append("partial environmental match")
        reasons.append(", ".join(parts[:3]))
    scored["reason"] = reasons

    return scored.sort_values(["habitat_score", "site_id"], ascending=[False, True]).reset_index(drop=True)
