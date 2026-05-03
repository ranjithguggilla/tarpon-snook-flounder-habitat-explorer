from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    export_cols = [c for c in df.columns if c != "geometry"]
    return df[export_cols].to_csv(index=False).encode("utf-8")


def geodataframe_to_geojson_bytes(gdf: gpd.GeoDataFrame) -> bytes:
    return gdf.to_json().encode("utf-8")


def persist_outputs(gdf: gpd.GeoDataFrame, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ranked_sites.csv"
    geojson_path = out_dir / "habitat_priority.geojson"

    export_cols = [c for c in gdf.columns if c != "geometry"]
    gdf[export_cols].to_csv(csv_path, index=False)
    gdf.to_file(geojson_path, driver="GeoJSON")
    return csv_path, geojson_path
