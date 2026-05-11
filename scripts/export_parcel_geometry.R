#!/usr/bin/env Rscript
#
# Export parcel polygons from county .rds geometry artifacts → GeoParquet.
#
# Before running this script, run the Python pipeline step that writes
# data/processed/parcel_geom/retail_join_keys.csv — that file controls which
# parcels are kept. Only retail-flagged parcels are exported so the output
# files stay small enough to be useful in the Python app.
#
# Usage (from repo root):
#   Rscript scripts/export_parcel_geometry.R
#
# Requires R packages: sf, arrow, dplyr
# Install once with: install.packages(c("sf", "arrow", "dplyr"))
#
# Output: one GeoParquet file per county in data/processed/parcel_geom/
#   baker_fl_geom.parquet, clay_fl_geom.parquet, ...
#
# The output CRS is EPSG:4326 (WGS84), required by PyDeck and the Python
# geo helpers that compute centroids and areas.

suppressPackageStartupMessages({
  library(sf)
  library(arrow)
  library(dplyr)
})

# ── Config ───────────────────────────────────────────────────────────────────

# Detect repo root whether the script is run via Rscript or source().
# When called as `Rscript scripts/export_parcel_geometry.R`, the script path
# is embedded in commandArgs; we go one directory up from scripts/.
args_full <- commandArgs(trailingOnly = FALSE)
script_flag <- grep("--file=", args_full, value = TRUE)
if (length(script_flag) > 0) {
  script_path <- sub("--file=", "", script_flag[1])
  repo_root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
} else {
  # Fallback when sourced interactively.
  repo_root <- getwd()
}

rds_root     <- file.path(repo_root, "..", "data", "property_taxes", "parcel_geom", "fl")
out_dir      <- file.path(repo_root, "data", "processed", "parcel_geom")
key_csv_path <- file.path(out_dir, "retail_join_keys.csv")

# Jacksonville counties and their .rds file names.
counties <- list(
  list(tag = "baker_fl",   rds = "baker_fl_geom.rds"),
  list(tag = "clay_fl",    rds = "clay_fl_geom.rds"),
  list(tag = "duval_fl",   rds = "duval_fl_geom.rds"),
  list(tag = "nassau_fl",  rds = "nassau_fl_geom.rds"),
  list(tag = "stjohns_fl", rds = "stjohns_fl_geom.rds")
)

# ── Preflight checks ─────────────────────────────────────────────────────────

if (!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE)

if (!file.exists(key_csv_path)) {
  stop(paste0(
    "retail_join_keys.csv not found at:\n  ", key_csv_path, "\n",
    "Run the Python key-export step first:\n",
    "  .venv/bin/python -m retail_opportunity_finder.pipelines.ingest_parcel_geom --keys-only"
  ))
}

# Load the retail join_key filter list written by the Python pipeline.
retail_keys <- read.csv(key_csv_path, stringsAsFactors = FALSE)$join_key
cat(sprintf("Loaded %s retail join keys from CSV\n", format(length(retail_keys), big.mark = ",")))

# ── Export each county ────────────────────────────────────────────────────────

export_county <- function(tag, rds_file) {
  rds_path <- file.path(rds_root, rds_file)
  out_path <- file.path(out_dir, paste0(tag, "_geom.parquet"))

  if (!file.exists(rds_path)) {
    message(sprintf("  SKIP %s — file not found: %s", tag, rds_path))
    return(invisible(NULL))
  }

  cat(sprintf("\nProcessing %s ...\n", tag))
  t0 <- proc.time()["elapsed"]

  # Read the sf object (geometry in source projected CRS).
  gdf <- readRDS(rds_path)
  cat(sprintf("  Read %s parcels\n", format(nrow(gdf), big.mark = ",")))

  # Filter to retail join_keys only before the expensive reprojection.
  gdf_retail <- gdf[gdf$join_key %in% retail_keys, ]
  cat(sprintf("  Filtered to %s retail parcels\n", format(nrow(gdf_retail), big.mark = ",")))

  if (nrow(gdf_retail) == 0) {
    message(sprintf("  SKIP %s — no matching retail join_keys", tag))
    return(invisible(NULL))
  }

  # Reproject from source projected CRS → EPSG:4326 (WGS84).
  # PyDeck and our Python geo helpers expect lon/lat coordinates.
  gdf_wgs84 <- st_transform(gdf_retail, crs = 4326)

  # Convert geometry to WKT and store as a plain data.frame column.
  # This avoids the GDAL Parquet driver requirement and is readable by
  # geopandas via gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkt(df.geom_wkt)).
  df_out <- data.frame(
    join_key     = gdf_wgs84$join_key,
    county_geoid = gdf_wgs84$county_geoid,
    county_tag   = gdf_wgs84$county_tag,
    geom_wkt     = st_as_text(gdf_wgs84$geometry),
    stringsAsFactors = FALSE
  )

  # Write as a plain Parquet file (no spatial metadata needed).
  write_parquet(df_out, out_path)

  elapsed <- round(proc.time()["elapsed"] - t0, 1)
  size_mb <- round(file.size(out_path) / 1024^2, 1)
  cat(sprintf("  Written to %s (%s MB, %ss)\n", basename(out_path), size_mb, elapsed))
}

cat("\n=== Parcel Geometry Export ===\n")
for (county in counties) {
  export_county(county$tag, county$rds)
}

cat("\n✓ Export complete. GeoParquet files written to:\n")
cat(sprintf("  %s\n", out_dir))
