from __future__ import annotations

import geopandas as gpd

from .data_loader import METRIC_CRS


def add_estuary_context(
    sites: gpd.GeoDataFrame, estuaries: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    site_cols = [c for c in sites.columns if c != "geometry"]
    est_cols = [c for c in ["estuary_id", "name", "geometry"] if c in estuaries.columns]
    joined = gpd.sjoin(
        sites[site_cols + ["geometry"]],
        estuaries[est_cols],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"], errors="ignore")
    joined = joined.rename(columns={"name": "estuary_name"})
    # If polygons overlap, keep one estuary label per candidate site.
    if "site_id" in joined.columns:
        joined = joined.sort_values("estuary_id", na_position="last").drop_duplicates(
            subset=["site_id"], keep="first"
        )
    joined["in_estuary"] = joined["estuary_id"].notna()
    return joined


def add_distance_features(
    sites: gpd.GeoDataFrame, coastline: gpd.GeoDataFrame, inlets: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    sites_m = sites.to_crs(METRIC_CRS)
    coast_m = coastline.to_crs(METRIC_CRS)
    inlets_m = inlets.to_crs(METRIC_CRS)

    coast_union = coast_m.geometry.union_all()
    inlet_union = inlets_m.geometry.union_all()

    sites_m["dist_to_coast_m"] = sites_m.geometry.distance(coast_union)
    sites_m["dist_to_inlet_m"] = sites_m.geometry.distance(inlet_union)

    out = sites_m.to_crs(sites.crs)
    out["dist_to_coast_km"] = out["dist_to_coast_m"] / 1000.0
    out["dist_to_inlet_km"] = out["dist_to_inlet_m"] / 1000.0
    return out


def prepare_sites_with_features(
    sites: gpd.GeoDataFrame,
    estuaries: gpd.GeoDataFrame,
    coastline: gpd.GeoDataFrame,
    inlets: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    sites = add_estuary_context(sites, estuaries)
    sites = add_distance_features(sites, coastline, inlets)
    return sites
