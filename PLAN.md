# Retail Opportunity Finder — Project Plan

## What We're Building

An interactive Streamlit web app for exploring retail investment opportunities across Southeast US markets. The app combines census tract demographics, cluster-based investment zones, and parcel-level data to help identify and evaluate retail sites.

Three surfaces:
1. **Zone Explorer** — CBSA / tract / zone map with demographic metrics and scoring
2. **Retail Parcel Explorer** — parcel candidate browser with filters, scoring, and a shortlist workflow
3. **Data QA App** — coverage and data health dashboard

---

## Architecture

```
metro_deep_dive.duckdb  ──export──►  rof_app.duckdb  ──reads──►  Streamlit apps
parcel_geom/fl/*.rds    ──ingest──►  rof_app.duckdb
                                          │
                                   rof_gold schema
                                   (all app-facing tables)
```

**Stack:** Python 3.12, Streamlit, PyDeck, DuckDB, GeoPandas, Shapely, Pandas, PyYAML, Pytest, Ruff

**Deployment path:**
- Local: run Streamlit against `data/processed/rof_app.duckdb`
- Cloud sharing: commit `data/exports/jacksonville_rof.duckdb` (Jacksonville-scoped subset), deploy to Streamlit Community Cloud
- Long-term: Render or Railway with full dataset

---

## Repo Structure

```
retail_opportunity_finder/
├── app/
│   ├── zone_explorer_app.py              # Surface 1: CBSA / tract / zone map
│   ├── retail_parcel_explorer_app.py     # Surface 2: parcel candidates
│   └── data_qa_app.py                    # Surface 3: coverage and data health
├── src/
│   └── retail_opportunity_finder/
│       ├── app/
│       │   ├── zone_map.py               # Testable map + metric + color helpers
│       │   ├── parcel_explorer.py        # Testable filter / sort / detail helpers
│       │   └── data_qa.py               # Testable QA summary helpers
│       ├── pipelines/
│       │   ├── export_from_metro.py      # Copy market slice → rof_app.duckdb
│       │   └── ingest_parcel_geom.py     # Parquet parcel geometry → rof_app.duckdb
│       ├── transforms/
│       │   └── scoring.py               # Score display helpers
│       └── utils/
│           ├── config.py                # Settings + data source loader
│           └── geo.py                   # WKT helpers, centroid, area
├── scripts/
│   └── export_parcel_geometry.R         # R: county .rds → WKT Parquet per county
├── data/
│   ├── processed/
│   │   ├── rof_app.duckdb               # Full local dev DB (gitignored)
│   │   └── parcel_geom/                 # Intermediate Parquet files (gitignored)
│   └── exports/
│       └── jacksonville_rof.duckdb      # Committed cloud-deploy subset (built in Phase 5)
├── config/
│   ├── settings.yaml                    # Market defs, DB paths, map centers
│   ├── data_sources.yaml                # Local source paths (gitignored)
│   └── data_sources.example.yaml       # Committed template
├── sql/
│   └── ddl/
│       └── 001_rof_gold_tables.sql      # rof_gold schema DDL
├── tests/
├── docs/
│   ├── retail_opportunity_finder_reuse_spec.md
│   └── rof_frontend_repo_handoff.md
└── pyproject.toml
```

---

## Data

### Source
All analytical data comes from `metro_deep_dive.duckdb` (separate repo). The export pipeline copies a market-scoped slice into `rof_app.duckdb`. Parcel geometry lives in county `.rds` files and is exported via R then ingested via Python.

### rof_gold Tables

| Table | Rows (JAX) | Purpose |
|---|---|---|
| `market_profiles` | 1 | Market metadata |
| `cbsa_geometry` | 1 | CBSA boundary WKT |
| `county_geometry` | 5 | County boundary WKTs |
| `tract_geometry` | 340 | Tract polygon WKTs |
| `tract_features` | 340 | ACS demographics per tract |
| `tract_scores` | 340 | Composite tract score + eligibility gates |
| `cluster_assignments` | 85 | Tract → cluster zone mapping |
| `cluster_zone_summary` | 8 | Zone-level KPIs (cluster system) |
| `cluster_zone_geometries` | 8 | Cluster zone polygon WKTs |
| `contiguity_zone_summary` | 22 | Zone-level KPIs (contiguity system) |
| `contiguity_zone_geometries` | 22 | Contiguity zone polygon WKTs |
| `parcel_shortlist` | 7,438 | Pre-scored retail parcel serving table |
| `parcel_zone_overlay` | 30 | Zone-level retail context (both systems) |
| `retail_intensity_by_tract` | 334 | Tract-level retail density metrics |
| `retail_parcel_tract_assignment` | 15,276 | Retail parcel → tract mapping |
| `retail_parcels` | 15,276 | Tabular retail parcel attributes |
| `parcel_geometry` | 15,207 | Parcel polygon WKT + centroid + area |
| `user_shortlist` | 0 | User review workflow (never overwritten) |

### Jacksonville Coverage
- **5 counties:** Baker, Clay, Duval, Nassau, St. Johns
- **340 tracts** with geometry, features, and scores
- **8 cluster zones** (primary), **22 contiguity zones** (comparison)
- **15,276 retail parcels** tabular; **15,207 with geometry**
- **7,396 / 7,438** shortlist rows have parcel area filled

### Key Data Findings
- `serving.parcel_shortlist` in metro_deep_dive is pre-built with all scores — the app reads it directly rather than recomputing scores at runtime
- Only one tract score model exists currently (`tract_score` from `scoring.tract_scores`) — the 4-model variant described in the handoff doc is not yet built
- Both cluster zones (8) and contiguity zones (22) are available for Jacksonville; cluster is the primary path

---

## Build Pipeline

Run these in order on a fresh machine or after upstream data changes:

```bash
# 1. Install dependencies
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 2. Export Jacksonville slice from metro_deep_dive.duckdb
.venv/bin/python -m retail_opportunity_finder.pipelines.export_from_metro

# 3a. Write retail join_keys for R filter step
.venv/bin/python -m retail_opportunity_finder.pipelines.ingest_parcel_geom --keys-only

# 3b. Export parcel geometries from .rds → WKT Parquet (requires R + sf + arrow)
Rscript scripts/export_parcel_geometry.R

# 3c. Ingest parcel geometry Parquets into DuckDB
.venv/bin/python -m retail_opportunity_finder.pipelines.ingest_parcel_geom
```

---

## Progress

### ✅ Completed

- [x] **Repo scaffold** — `pyproject.toml`, `.gitignore`, config files, DDL, package init, shared utilities (`config.py`, `geo.py`)
- [x] **GitHub** — public repo at https://github.com/dberle22/retail_opportunity_finder
- [x] **Metro export pipeline** (`export_from_metro.py`) — copies 17 tables from `metro_deep_dive.duckdb` into `rof_gold` schema; re-run safe; Jacksonville running in ~1 second
- [x] **R parcel geometry export** (`export_parcel_geometry.R`) — reads 5 county `.rds` files, filters to retail join_keys, reprojects to EPSG:4326, writes WKT-in-Parquet per county
- [x] **Python parcel geometry ingest** (`ingest_parcel_geom.py`) — reads county Parquets, computes centroids + area, writes to `rof_gold.parcel_geometry`, backfills `parcel_area_sqmi` in shortlist

### 🔲 Remaining

- [ ] **Zone Explorer app** (`app/zone_explorer_app.py` + `src/.../app/zone_map.py`)
- [ ] **Retail Parcel Explorer app** (`app/retail_parcel_explorer_app.py` + `src/.../app/parcel_explorer.py`)
- [ ] **Data QA app** (`app/data_qa_app.py` + `src/.../app/data_qa.py`)
- [ ] **Tests** — schema, geo helpers, metric display, filter/sort logic, score status, shortlist upsert
- [ ] **Cloud deployment** — build `data/exports/jacksonville_rof.duckdb`, deploy to Streamlit Community Cloud

---

## App Specs

### Zone Explorer (`app/zone_explorer_app.py`)

**Sidebar controls:**
- Market display (Jacksonville — static for MVP; selector when more markets are added)
- Layer mode segmented control: `Tracts` | `Cluster Zones` | `Contiguity Zones`
- Metric selector:
  - Demographics: population, pop growth 3yr, median HH income, per capita income, poverty rate
  - Housing: median gross rent, median home value
  - Activity: population density, building permits per 1k
  - Scores: tract score, eligibility gates (pop/price/density)
  - Retail context: retail parcel count, retail area density, local retail context score
- Null-aware color ramp (muted fill for missing-data tracts, never shows zero for nulls)
- Eligibility gate highlight toggle (dims ineligible tracts)

**Map layers (PyDeck):**
- `PolygonLayer` — tract polygons filled by selected metric
- `PolygonLayer` — zone boundaries (toggled by layer mode)
- `ScatterplotLayer` — zone label centroids
- `PolygonLayer` — CBSA outline
- `PolygonLayer` — county outlines

**Below map:**
- Top zones table sorted by selected metric

**Helper module** (`src/.../app/zone_map.py`):
- `load_tract_data(con, cbsa_code)` → joined tract geometry + features + scores
- `load_zone_data(con, market_key, zone_system)` → zone geometry + summary
- `build_metric_options()` → ordered dict of display label → column name
- `apply_color_ramp(df, metric_col)` → adds RGBA color columns, null-safe
- `build_tract_layer(df)` → PyDeck PolygonLayer
- `build_zone_layer(df)` → PyDeck PolygonLayer
- `build_label_layer(df)` → PyDeck ScatterplotLayer
- `build_tooltip(layer_type)` → tooltip HTML dict

---

### Retail Parcel Explorer (`app/retail_parcel_explorer_app.py`)

**Primary data source:** `rof_gold.parcel_shortlist` joined to `rof_gold.parcel_geometry`

**Sidebar controls:**
- County multiselect (Baker, Clay, Duval, Nassau, St. Johns)
- Zone filter — cluster zone multiselect (Zone A–H with score)
- Zone system toggle: Cluster | Contiguity
- Retail subtype filter
- Assessed value range slider
- Parcel area range slider (sq mi)
- Score threshold sliders: Shortlist score · Zone quality · Parcel characteristics
- Shortlist status filter: All / Active / Needs Review / Watchlist / Rejected / Unreviewed
- Sort selector: Best opportunity · Strongest zone · Best parcel characteristics · Best retail context · Largest site · Newest sale · Lowest assessed value

**Layout:**
- Left column: filtered + sorted parcel list
- Center column: PyDeck map
  - `PolygonLayer` — zone boundaries
  - `PolygonLayer` — retail parcel polygons colored by shortlist score
  - `ScatterplotLayer` — selected parcel highlight
- Right column: detail panel
  - Identity: address, county, zone, retail subtype, land use code
  - Parcel facts: area, assessed value, land value, improvement value, last sale date/price
  - Scores with status badge (scored / partial / unavailable): shortlist score, zone quality score, parcel characteristics score, local retail context score, mean tract score
  - Zone context: label, tract count, population, pop growth, mean tract score
  - Shortlist actions: status selector + notes + Save (upserts to `rof_gold.user_shortlist`)

**Shortlist statuses:** `active` | `needs_review` | `watchlist` | `rejected`

**Helper module** (`src/.../app/parcel_explorer.py`):
- `load_shortlist(con, market_key, zone_system)` → parcel shortlist joined to geometry
- `apply_filters(df, filters)` → filtered DataFrame
- `apply_sort(df, sort_key)` → sorted DataFrame
- `score_status(value)` → `"scored"` / `"partial"` / `"unavailable"`
- `build_parcel_layer(df)` → PyDeck PolygonLayer
- `build_selected_layer(row)` → PyDeck ScatterplotLayer
- `upsert_shortlist(con, parcel_uid, market_key, user_id, status, notes)` → writes to `user_shortlist`

---

### Data QA App (`app/data_qa_app.py`)

**Panels:**
1. Source connections — is `metro_deep_dive.duckdb` reachable? Are parcel Parquet files present?
2. Table inventory — row counts for all `rof_gold` tables, flagging empty or missing
3. Tract coverage — % with score, % with each feature metric, null rate by field
4. Zone build coverage — tracts assigned vs. unassigned, both cluster and contiguity
5. Parcel geometry coverage — county-by-county match rate, null geometry count
6. Score coverage — % of shortlist rows with each score component vs. NULL
7. Eligibility gate summary — % of tracts passing each gate and all three combined
8. Build freshness — `run_timestamp` values from key source tables

**Helper module** (`src/.../app/data_qa.py`):
- `table_inventory(con)` → DataFrame of table name, row count, status
- `tract_coverage(con, cbsa_code)` → null rate per metric column
- `zone_build_coverage(con, market_key)` → assigned/unassigned counts
- `parcel_geometry_coverage(con)` → county-level geometry match rates
- `score_coverage(con, market_key)` → score null rates

---

## Tests (`tests/`)

Categories to cover:

| File | What it tests |
|---|---|
| `test_schema.py` | All rof_gold tables exist with expected columns and row counts |
| `test_geo_utils.py` | WKT → polygon coords, centroid extraction, area calculation, null handling |
| `test_zone_map.py` | Metric options, color ramp (null-safe), layer building |
| `test_parcel_explorer.py` | Filter logic, sort logic, score status formatter |
| `test_shortlist.py` | Upsert creates row, upsert updates existing row, status values |
| `test_data_qa.py` | Table inventory, coverage summaries |

---

## Cloud Deployment (Phase 5)

```bash
# Build the committed cloud artifact (Jacksonville-scoped, no local paths)
.venv/bin/python scripts/build_export_db.py  # (to be written in Phase 5)

# Deploy: connect GitHub repo to Streamlit Community Cloud
# https://streamlit.io/cloud → New app → dberle22/retail_opportunity_finder → app/zone_explorer_app.py
```

App detects cloud mode: if `config/data_sources.yaml` is absent (not committed), falls back to `data/exports/jacksonville_rof.duckdb`.

Each app surface is a separate Streamlit entry point — deploy them individually or use a multi-page app wrapper.

---

## Adding More Markets (Post-MVP)

To add Orlando or Gainesville:

1. Add the market to `config/settings.yaml` under `markets:`
2. Re-run the export pipeline with `--market orlando_fl`
3. Re-run the geometry pipeline for the new market's counties
4. The apps read `market_key` from config — they'll pick up the new market automatically

Both Orlando and Gainesville already exist in `serving.parcel_shortlist` in `metro_deep_dive.duckdb`, so the export step is the main gate.

---

## Known Gaps / Future Work

| Item | Notes |
|---|---|
| 4-model tract scoring | `rof_features.tract_models` (balanced/growth/value/corridor) is documented in the handoff but not yet built in metro_deep_dive; currently only `tract_score` exists |
| POI overlay | No POI/anchor data in current DuckDB; would need a separate ingest (Google Places or curated lists) |
| Parcel ingest speed | `ingest_parcel_geom.py` takes ~2 min for 15k parcels due to per-row CRS reprojection; batch with GeoPandas for a 10x speedup |
| Port R zone build to Python | Zone construction is currently R-based; plan to port after frontend is stable |
| Expand to GA, NC, SC markets | Requires upstream ACS tract coverage expansion in metro_deep_dive |
