# Data Sources and Provenance

This prototype is public-data-safe and combines:

- **Boundary-style demo layers** in `data/raw/*.geojson` (coastline, estuaries, inlets) created for demonstration and inspired by publicly available coastal mapping concepts.
- **Synthetic observations and survey sites** in `data/synthetic/*.csv`.

It does **not** include private telemetry records, confidential field sites, or institute-provided data.

If you want to replace the boundary layers with external public sources, recommended starting points are:

- NOAA Office for Coastal Management datasets.
- USGS shoreline and estuary boundary products.
- State agency public GIS portals for inlets/passes and habitat classes.

Keep coordinate reference systems in EPSG:4326 for display and project into a metric CRS for distance calculations.
