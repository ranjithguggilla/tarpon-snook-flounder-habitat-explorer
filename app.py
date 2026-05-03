from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.data_loader import ROOT, load_observations, load_public_layers, load_survey_sites
from src.export_utils import dataframe_to_csv_bytes, geodataframe_to_geojson_bytes, persist_outputs
from src.geospatial_utils import prepare_sites_with_features
from src.habitat_score import score_sites


st.set_page_config(
    page_title="Tarpon, Snook & Southern Flounder Habitat Explorer",
    layout="wide",
)

st.title("Tarpon, Snook & Southern Flounder Habitat Prioritization Demo")
st.caption(
    "Public-data-safe decision-support prototype using boundary-style GIS layers and synthetic observations."
)


@st.cache_data(show_spinner=False)
def build_base_data() -> tuple[dict[str, gpd.GeoDataFrame], gpd.GeoDataFrame, gpd.GeoDataFrame]:
    layers = load_public_layers()
    observations = load_observations()
    sites = load_survey_sites()
    featured_sites = prepare_sites_with_features(
        sites=sites,
        estuaries=layers["estuaries"],
        coastline=layers["coastline"],
        inlets=layers["inlets"],
    )
    return layers, observations, featured_sites


layers, observations, featured_sites = build_base_data()

species_options = ["Tarpon", "Snook", "Southern Flounder"]
month_names = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

left, right = st.columns([1, 3])
with left:
    selected_species = st.selectbox("Species", species_options, index=0)
    selected_month = st.selectbox(
        "Month",
        list(month_names.keys()),
        index=6,
        format_func=lambda m: month_names[m],
    )
    show_observations = st.checkbox("Show observations", value=True)
    priority_filter = st.multiselect(
        "Priority classes",
        ["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
    )
    top_n = st.slider("Show top N sites", min_value=3, max_value=12, value=12, step=1)
    st.markdown("### Survey Priority")
    st.markdown("- High: score >= 75")
    st.markdown("- Medium: 50-74")
    st.markdown("- Low: < 50")

scored_sites = score_sites(featured_sites, selected_species, int(selected_month))
if priority_filter:
    scored_sites = scored_sites[scored_sites["priority"].isin(priority_filter)]
scored_sites = scored_sites.head(top_n).reset_index(drop=True)
obs_filtered = observations[observations["species"] == selected_species]

summary = {
    "sites": int(scored_sites.shape[0]),
    "high": int((scored_sites["priority"] == "High").sum()),
    "medium": int((scored_sites["priority"] == "Medium").sum()),
    "low": int((scored_sites["priority"] == "Low").sum()),
}
metrics = st.columns(4)
metrics[0].metric("Sites Evaluated", summary["sites"])
metrics[1].metric("High Priority", summary["high"])
metrics[2].metric("Medium Priority", summary["medium"])
metrics[3].metric("Low Priority", summary["low"])

with right:
    if scored_sites.empty:
        map_center = [featured_sites["latitude"].mean(), featured_sites["longitude"].mean()]
    else:
        map_center = [scored_sites["latitude"].mean(), scored_sites["longitude"].mean()]
    fmap = folium.Map(location=map_center, zoom_start=8, tiles="CartoDB positron")

    folium.GeoJson(
        layers["estuaries"].to_json(),
        name="Estuaries",
        style_function=lambda _: {"color": "#357ABD", "weight": 2, "fillOpacity": 0.15},
    ).add_to(fmap)
    folium.GeoJson(
        layers["coastline"].to_json(),
        name="Coastline",
        style_function=lambda _: {"color": "#4F4F4F", "weight": 3},
    ).add_to(fmap)

    for _, inlet in layers["inlets"].iterrows():
        folium.CircleMarker(
            location=[inlet.geometry.y, inlet.geometry.x],
            radius=4,
            color="#0D9488",
            fill=True,
            fill_opacity=0.85,
            popup=f"Inlet: {inlet['name']}",
        ).add_to(fmap)

    priority_colors = {"High": "#D62828", "Medium": "#F77F00", "Low": "#2A9D8F"}
    for _, row in scored_sites.iterrows():
        popup = (
            f"{row['site_name']}<br>"
            f"Priority: {row['priority']}<br>"
            f"Score: {row['habitat_score']}<br>"
            f"Reason: {row['reason']}"
        )
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=7,
            color=priority_colors[row["priority"]],
            fill=True,
            fill_opacity=0.9,
            popup=popup,
        ).add_to(fmap)

    if show_observations:
        for _, row in obs_filtered.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=4,
                color="#6A4C93",
                fill=True,
                fill_opacity=0.7,
                popup=f"Obs {row['obs_id']} ({row['species']}, month {row['month']})",
            ).add_to(fmap)

    folium.LayerControl().add_to(fmap)
    st_folium(fmap, use_container_width=True, height=520)

st.subheader("Ranked Survey Sites")
table_cols = [
    "site_id",
    "site_name",
    "species",
    "month",
    "habitat_score",
    "priority",
    "dist_to_inlet_km",
    "dist_to_coast_km",
    "salinity_psu",
    "temp_c",
    "reason",
]
st.dataframe(
    scored_sites[table_cols].round({"dist_to_inlet_km": 2, "dist_to_coast_km": 2}),
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Showing {len(scored_sites)} filtered sites for {selected_species} in {month_names[int(selected_month)]}."
)

st.subheader("Auto-generated Site Summary")
if not scored_sites.empty:
    top = scored_sites.iloc[0]
    st.write(
        f"Top site for **{selected_species}** in **{month_names[int(selected_month)]}** is "
        f"**{top['site_name']}** with score **{top['habitat_score']}** "
        f"({top['priority']} priority) because it is {top['reason']}."
    )

export_left, export_right = st.columns(2)
csv_bytes = dataframe_to_csv_bytes(scored_sites[table_cols])
geojson_bytes = geodataframe_to_geojson_bytes(scored_sites)

export_left.download_button(
    label="Download Ranked Sites CSV",
    data=csv_bytes,
    file_name="ranked_sites.csv",
    mime="text/csv",
)
export_right.download_button(
    label="Download Habitat Priority GeoJSON",
    data=geojson_bytes,
    file_name="habitat_priority.geojson",
    mime="application/geo+json",
)

if st.button("Persist outputs to outputs/ folder"):
    out_dir = Path(ROOT) / "outputs"
    csv_path, geojson_path = persist_outputs(scored_sites, out_dir)
    st.success(f"Saved: {csv_path.name}, {geojson_path.name}")
