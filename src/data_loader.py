from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SYN_DIR = ROOT / "data" / "synthetic"
TARGET_CRS = "EPSG:4326"
METRIC_CRS = "EPSG:32614"


def _ensure_crs(gdf: gpd.GeoDataFrame, fallback_crs: str = TARGET_CRS) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(fallback_crs)
    return gdf.to_crs(TARGET_CRS)


def load_public_layers() -> dict[str, gpd.GeoDataFrame]:
    estuaries = _ensure_crs(gpd.read_file(RAW_DIR / "estuaries.geojson"))
    coastline = _ensure_crs(gpd.read_file(RAW_DIR / "coastline.geojson"))
    inlets = _ensure_crs(gpd.read_file(RAW_DIR / "inlets.geojson"))
    return {"estuaries": estuaries, "coastline": coastline, "inlets": inlets}


def load_observations() -> gpd.GeoDataFrame:
    df = pd.read_csv(SYN_DIR / "observations.csv")
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs=TARGET_CRS,
    )
    return gdf


def load_survey_sites() -> gpd.GeoDataFrame:
    df = pd.read_csv(SYN_DIR / "survey_sites.csv")
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs=TARGET_CRS,
    )
    return gdf
