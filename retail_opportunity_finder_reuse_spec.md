# Retail Opportunity Finder Reuse Spec

Created from the Rental Area Search / NYC Property Finder repo on 2026-04-21.

## Purpose

This document captures the reusable product, data, and app patterns from this
repo that should transfer into a Retail Opportunity Finder product. The target
ROF product starts with Southeast US markets, uses census tract demographics and
market context, dissolves tracts into investment zones, and overlays parcel data
to identify retail land or building opportunities.

The strongest reusable idea is the split between:

1. A foundation explorer for tract and zone intelligence.
2. A candidate explorer for parcel or site-level review.
3. A QA surface that makes missing data, source status, and metric coverage
   visible outside the main product flow.

In ROF terms, the existing `Neighborhood Explorer` becomes a `Market / Zone
Explorer`, and the existing `Property Explorer` becomes a `Retail Parcel
Explorer`.

## Current Repo Patterns Worth Reusing

### Architecture

The current repo uses a lightweight local analytics stack:

| Layer | Current repo | ROF equivalent |
| --- | --- | --- |
| Raw inputs | `data/raw`, local CSV/GeoJSON/KML/Google exports | ACS, tract geometries, county/market definitions, parcel extracts, POI/business data |
| Interim/cache inputs | `data/interim`, geocode and Google Places caches | geocoding caches, parcel standardization artifacts, POI resolution caches |
| Gold app tables | DuckDB schema `property_explorer_gold` | DuckDB schema such as `rof_gold` |
| Spatial processing | GeoPandas/Shapely, WKT in DuckDB for starter persistence | Same, with market CRS choices handled explicitly where needed |
| Frontend | Streamlit plus PyDeck | Same initially, potentially split into reusable modules later |
| Tests | Pytest around helpers and pipelines | Same pattern, especially for geography, scoring, app filters, and QA summaries |

The repo deliberately keeps app-ready facts and dimensions in DuckDB, with
Streamlit reading those tables rather than rebuilding data logic at runtime.
That should remain a core ROF principle.

### Code Organization

Current structure:

| Path | Role |
| --- | --- |
| `app/streamlit_app_v2.py` | Neighborhood Explorer Streamlit entry point |
| `src/nyc_property_finder/app/base_map.py` | Testable geography, metric, POI, and PyDeck helpers |
| `app/streamlit_app.py` | Property Explorer Streamlit entry point |
| `src/nyc_property_finder/app/explorer.py` | Testable candidate filtering, sorting, map, score, and shortlist helpers |
| `app/neighborhood_qa_app.py` | Separate data-readiness QA surface |
| `src/nyc_property_finder/app/neighborhood_qa.py` | Testable source/table/metric coverage summaries |
| `src/nyc_property_finder/pipelines/*` | Deterministic build entry points |
| `src/nyc_property_finder/transforms/*` | Reusable transforms and scoring |
| `src/nyc_property_finder/utils/geo.py` | Spatial joins, nearest neighbor, radius counts |
| `sql/ddl/001_gold_tables.sql` | Executable DuckDB starter schema |
| `docs/data_model.md` | Product-facing table contract |
| `docs/pipeline_plan.md` | Operational build order |

ROF should mirror this layout with names like:

| ROF path | Suggested role |
| --- | --- |
| `app/zone_explorer_app.py` | Market, tract, and investment-zone review |
| `app/retail_parcel_explorer_app.py` | Parcel/site candidate map, list, detail, and shortlist workflow |
| `app/data_qa_app.py` | Table readiness, source status, coverage, and data quality |
| `src/retail_opportunity_finder/app/zone_map.py` | Tract/zone map helper module |
| `src/retail_opportunity_finder/app/parcel_explorer.py` | Parcel filtering, sorting, scoring, and shortlist helper module |
| `src/retail_opportunity_finder/pipelines/` | Build steps for market, tract, zone, parcel, POI, and score tables |
| `src/retail_opportunity_finder/transforms/` | Demographics, geography, parcels, retail classification, scoring |
| `src/retail_opportunity_finder/utils/geo.py` | Shared spatial helpers |

## Product Surfaces

### 1. Market / Zone Explorer

Current behavior to reuse from `app/streamlit_app_v2.py` and
`src/nyc_property_finder/app/base_map.py`:

- Load tract geometry from configured source paths.
- Join tract attributes from a gold demographic feature table.
- Dissolve tracts into a higher-level geography.
- Let the user switch between tract and dissolved geography.
- Let the user select a demographic metric for color fill.
- Render boundaries even when metric values are missing.
- Show missing values as `Unavailable`, never as zero.
- Keep color ramps null-aware, with muted missing-data fills.
- Overlay points of interest and filter them by source list/type.
- Show a top-25 metric table beneath the map.

ROF translation:

- Tract layer: census tracts in the selected market.
- Dissolved layer: investment zones created from tract groupings.
- Optional higher layers: counties, submarkets, drive-time trade areas, custom
  strategic areas.
- Metric selector: income, population growth, household growth, rent burden,
  median home value, retail leakage, daytime population, traffic counts, parcel
  density, vacancy proxy, or any ROF tract feature.
- POI overlay: anchors, competitors, grocers, restaurants, schools, hospitals,
  shopping centers, user-curated prospects, and Google Places-backed lists.

The key app design is foundation-first. The user should be able to evaluate the
market and zones before looking at individual parcels.

### 2. Retail Parcel Explorer

Current behavior to reuse from `app/streamlit_app.py` and
`src/nyc_property_finder/app/explorer.py`:

- Read a single app-ready fact table for candidate rows.
- Provide sidebar filters for candidate type, geography, numeric ranges, score
  thresholds, POI categories, and shortlist status.
- Show map, list, and detail views together.
- Highlight the selected candidate on the map.
- Sort by best overall fit, component scores, price/cost proxy, geography, or
  candidate attributes.
- Show score status instead of pretending missing components are scored.
- Persist local shortlist state in DuckDB with notes and statuses.
- Join shortlist state back onto current candidate facts.

ROF translation:

- Candidate row: one parcel, assemblage, shopping center, land site, or building.
- Detail panel: owner, land use, zoning, acreage, building area, assessed value,
  sale/transfer recency, flood/wetland flags, frontage, access, nearest anchors,
  nearest competitors, and investment-zone context.
- Filters: market, county, zone, parcel class, retail suitability flag, acreage,
  building area, assessed value, improvement ratio, distance to anchor, distance
  to highway/intersection, score thresholds, and shortlist state.
- Sorts: best retail opportunity, strongest zone, highest parcel readiness,
  nearest anchor, largest site, lowest improvement ratio, newest sale, or custom
  investment priority.
- Shortlist states: `active`, `archived`, `rejected`; consider adding
  `needs_review`, `contacted`, and `watchlist` for ROF.

### 3. Data QA App

The repo now has a separate QA app pattern. ROF should keep this separate from
the main product flow.

Recommended QA panels:

- Configured source paths and whether files/databases exist.
- DuckDB table existence and row counts.
- Metric coverage by table, market, county, tract, and zone.
- Zone build coverage: tracts assigned, unassigned tracts, zone counts.
- Parcel geometry coverage and validity.
- Parcel-to-zone assignment rates.
- Retail classification coverage and unknown land-use codes.
- Candidate score coverage and missing score reasons.
- POI/business geocoding coverage and duplicate resolution groups.
- Date/freshness signals for each source.

## Gold Tables To Port Into ROF

### Current Table Contracts

The current repo uses these app-facing tables:

| Current table | Current grain | ROF equivalent |
| --- | --- | --- |
| `dim_tract_to_nta` | one tract to one NTA | `dim_tract_to_zone`, one tract to one investment zone |
| `fct_tract_features` | one tract feature row | `fct_tract_features`, one tract per metric vintage/source |
| `fct_nta_features` | one NTA summary row | `fct_zone_features`, one investment zone summary |
| `dim_user_poi` / `dim_user_poi_v2` | one POI | `dim_poi`, `dim_business`, or `dim_anchor_place` |
| `dim_subway_stop` | one public transit point | `dim_infrastructure_point` or market-specific mobility/access tables |
| `dim_property_listing` | one listing | `dim_parcel`, `dim_site_candidate`, or separate parcel and candidate dims |
| `fct_property_context` | one listing with geography/context/scores | `fct_retail_parcel_context` |
| `fct_user_shortlist` | one user/candidate state row | `fct_user_shortlist` |

### Suggested ROF Gold Schema

Use a schema like `rof_gold`. Recommended starter tables:

| Table | Grain | Purpose |
| --- | --- | --- |
| `dim_market` | one market | Market metadata, default center/zoom, target counties, state, CRS |
| `dim_tract` | one tract per market/vintage | Tract geography metadata and optional WKT |
| `fct_tract_features` | one tract per source year | ACS and market features used for zone formation/scoring |
| `dim_investment_zone` | one zone | Zone ID, name, market, method/version, geometry WKT, narrative label |
| `dim_tract_to_zone` | one tract-zone assignment | Zone membership, assignment method, weight/share if partial |
| `fct_zone_features` | one zone per feature vintage | Aggregated demographics, demand, and risk metrics |
| `dim_parcel` | one standardized parcel | Parcel geometry, acreage, land use, owner, zoning, assessed values |
| `dim_retail_candidate` | one candidate parcel/site/assemblage | Candidate identity, candidate type, eligibility flags |
| `fct_retail_parcel_context` | one candidate with context | App-ready parcel, zone, POI, infrastructure, and score fields |
| `dim_poi` | one POI/business/anchor | Google Places, curated lists, public anchors, competitors |
| `fct_user_shortlist` | one user/candidate state | Local review workflow, notes, status |

Keep user-authored tables such as shortlists out of replace-first rebuilds.

## Spatial And Demographic Methods

### Tract To Zone Dissolve

Current repo pattern:

- Load tract polygons.
- Normalize GEOIDs as strings.
- Filter to target geography.
- Join tract-level features.
- Dissolve by higher-level ID/name.
- Attach aggregated metrics to dissolved polygons.

ROF implementation notes:

- Investment zones should be explicit, versioned outputs, not just dynamic map
  dissolves.
- Store zone method/version fields, for example `zone_method`,
  `zone_version`, `created_at`, `market_key`.
- For tract-to-zone assignment, use full tract assignment first if zones are
  tract-built. If using arbitrary zone polygons, store an area or population
  weight for split tracts.
- Keep `dim_tract_to_zone` separate from `dim_investment_zone` so zone features
  can be rebuilt without rewriting zone identity.

### Aggregation Rules

The current repo uses medians across tracts for NTA metrics. That is acceptable
as a starter but should be improved in ROF where possible.

Recommended ROF rules:

- Counts: sum.
- Percentages: weighted average with the correct denominator.
- Rates: weighted average or recompute from numerator and denominator.
- Medians: use a documented approximation if tract medians are the only input,
  and label them as approximate.
- Scores: aggregate component inputs first where possible, then score the zone.
- Coverage: record metric non-null counts and coverage percentages by zone.

### Parcel Assignment

Reuse current point-in-polygon and spatial helper patterns, but adapt for
polygons:

- Assign parcel centroids to tracts/zones for fast first-pass joins.
- For parcels crossing boundaries, consider largest-intersection assignment.
- Keep QA counts for invalid geometries, missing geometries, unassigned parcels,
  and multi-zone overlaps.
- Use projected CRS for area, distance, and frontage-like calculations.

## POI And Place Enrichment

The current Google Places v2 workflow is highly reusable.

Current design:

- Parse Google Maps saved-list CSVs.
- Preserve user metadata: title, note, tags, comment, source URL, source list.
- Resolve place names to Google Place IDs.
- Fetch minimal details only: display name, formatted address, coordinates.
- Cache resolution and details in JSONL files.
- Deduplicate to one row per Google Place ID.
- Preserve multi-list membership as JSON arrays.
- Write `dim_user_poi_v2`.
- Produce summary and QA artifacts, including duplicate-place review groups.

ROF translation:

- Use the same pattern for anchor lists, competitor lists, tenant lists,
  shopping centers, restaurants, grocers, fitness, medical, schools, and civic
  anchors.
- Treat Google Places as enrichment, not the source of user intent. The source
  list and notes remain important.
- Use call caps and cache-first reruns.
- Keep manual override support for false matches.
- Expose POI source and freshness in the app.

Recommended ROF POI fields:

| Field | Notes |
| --- | --- |
| `poi_id` | Stable internal ID |
| `source_system` | `google_places`, `manual`, `public_dataset`, etc. |
| `source_record_id` | Source-native ID where available |
| `source_list_names` | JSON array for curated list membership |
| `categories` | JSON array |
| `primary_category` | Main display/filter category |
| `name` | Enriched display name |
| `input_title` | Original user/source title |
| `address` | Formatted address |
| `lat`, `lon` | WGS84 coordinates |
| `google_place_id` | When available |
| `match_status` | `exact_match`, `likely_match`, `ambiguous`, `no_match`, `manual_override` |
| `details_fetched_at` | Freshness |

## Scoring Pattern

The current repo uses transparent 0-100 component scores:

- `neighborhood_score`
- `mobility_score`
- `personal_fit_score`
- `property_fit_score`
- status columns for each score where missingness matters
- reweighting when some components are missing

Current default weights:

| Component | Weight |
| --- | ---: |
| neighborhood | 0.40 |
| mobility | 0.25 |
| personal fit | 0.35 |

ROF should keep the same component-score pattern but rename the components:

| ROF component | Example inputs |
| --- | --- |
| `zone_score` | income, household growth, retail demand, education, daytime population, growth trend |
| `parcel_readiness_score` | acreage, zoning/land use fit, improvement ratio, geometry validity, access/frontage proxy |
| `retail_context_score` | anchors, competitors, complementary POIs, traffic/access, shopping node proximity |
| `risk_score` | flood/wetland flags, vacancy/risk proxies, poor access, ownership fragmentation |
| `opportunity_score` | weighted total across available components |

Keep status fields:

- `zone_score_status`
- `parcel_readiness_score_status`
- `retail_context_score_status`
- `risk_score_status`
- `opportunity_score_status`

Never turn missing inputs into zero-quality candidates. Show `unavailable`,
`partial`, or `reweighted_missing_components`.

## Frontend Technical Specs

### Core Stack

- Python 3.11+
- Streamlit
- PyDeck
- DuckDB
- Pandas
- GeoPandas
- Shapely
- PyYAML
- Pytest
- Ruff

### App Controls To Reuse

Market / Zone Explorer:

- market selector
- layer mode segmented control: `Tracts`, `Investment Zones`, possibly `Counties`
- metric selectbox
- demographic colors toggle
- POI/anchor overlay toggle
- POI type multiselect
- zone method/version selector when multiple builds exist
- top zones table sorted by selected metric

Retail Parcel Explorer:

- market, county, zone filters
- candidate type filter
- land-use/retail eligibility filter
- acreage/building area/value sliders
- score threshold sliders
- POI category filters
- shortlist status filter
- map layer toggles for parcels, POIs, anchors, competitors, infrastructure
- sort selector
- map/list/detail layout
- persisted notes and status actions

### Map Layers

Reuse the PyDeck pattern:

- `PolygonLayer` for tract fills.
- `PolygonLayer` for investment-zone boundaries.
- `PolygonLayer` for parcel polygons where geometry size is manageable.
- `ScatterplotLayer` for centroids, POIs, anchors, and selected candidates.
- Separate selected-candidate layer with larger radius or stronger color.
- Tooltip HTML prepared in data helper functions, not assembled inline in the
  app body.

For parcels at large scale, use centroids or simplified geometries in the app
contract and keep full parcel geometry in source or analysis tables.

## Config Pattern

Current `config/settings.yaml` stores:

- database path
- local default user
- target geography
- default map center
- default map zoom

ROF should use:

```yaml
database_path: data/processed/retail_opportunity_finder.duckdb
local_user:
  default_user_id: local_default
default_market_key: jacksonville_fl
markets:
  jacksonville_fl:
    label: Jacksonville, FL
    state: FL
    county_geoids:
      - "12031"
    default_map_center:
      lat: 30.3322
      lon: -81.6557
    default_map_zoom: 9
```

Keep private/local source paths in `config/data_sources.yaml`, with a committed
`config/data_sources.example.yaml`.

## Build Order

Recommended ROF build order:

1. Initialize DuckDB schemas and starter tables.
2. Load market definitions and target counties.
3. Load tract geometries.
4. Build tract features from ACS, Metro Deep Dive, or ROF feature tables.
5. Build or load investment-zone definitions.
6. Build `dim_tract_to_zone` and `fct_zone_features`.
7. Load and standardize parcel geometries/attributes.
8. Classify retail parcel candidates.
9. Ingest or enrich POI/anchor/competitor data.
10. Assign parcels to tracts/zones and compute spatial context.
11. Build `fct_retail_parcel_context` and score fields.
12. Run QA tests and launch apps.

The main app should read only app-ready gold tables. Any cache fallback should
be visible to the user and treated as a development convenience.

## Test Coverage To Bring Over

Port these current test categories:

- Schema tests for expected gold tables and columns.
- Geography tests for GEOID normalization and target market filtering.
- Tract-to-zone assignment tests.
- Zone dissolve tests.
- Missing metric display and color tests.
- POI parsing, JSON array parsing, and source-list filtering tests.
- Candidate filter and sort tests.
- Score formatting, score status, and reweighting tests.
- Shortlist upsert and join tests.
- QA summary tests for table readiness and metric coverage.
- Spatial helper tests for point-in-polygon, nearest neighbor, and radius counts.

## Product Principles To Preserve

- The app is a decision-support surface, not just a map.
- Missing data should be honest and visible.
- App tables are product contracts.
- Streamlit should compose UI, not own pipeline logic.
- User-authored data should survive rebuilds.
- Cached API enrichment should be idempotent and reviewable.
- Tract, zone, parcel, and POI layers should be inspectable independently.
- Scoring should be transparent enough to debug from the detail panel.
- QA should be a first-class app, not an afterthought.

## Current Local Snapshot From This Repo

As of the 2026-04-21 review:

| Artifact | Current local state |
| --- | --- |
| `property_explorer_gold.fct_tract_features` | 1,115 rows; high but incomplete metric coverage |
| `property_explorer_gold.fct_nta_features` | 108 rows; moderate metric coverage |
| `property_explorer_gold.fct_property_context` | 22 listing-context rows |
| `property_explorer_gold.dim_user_poi_v2` | 91 Google Places-backed POIs, all with coordinates |
| Google Places cache | 97 source rows resolved to 91 unique Google Place IDs |
| Raw Google Maps CSVs | additional saved-list files exist beyond the current built v2 categories |

This snapshot matters less for ROF than the pattern: build app-ready gold tables,
surface coverage honestly, and use focused QA before trusting scores.

## First ROF Implementation Slice

A practical first slice should be:

1. Create the ROF repo scaffold with the same package/app/docs/test shape.
2. Define `rof_gold` DDL for markets, tracts, zones, parcels, POIs, context,
   and shortlist.
3. Build one market, preferably a Southeast pilot such as Jacksonville, Orlando,
   Tampa, Gainesville, or another known data-rich market.
4. Load tract features and tract geometry.
5. Create a first deterministic investment-zone build.
6. Launch `zone_explorer_app.py` with tract/zone toggles and metric coloring.
7. Load standardized parcels for that market and classify retail candidates.
8. Build `fct_retail_parcel_context`.
9. Launch `retail_parcel_explorer_app.py` with filters, scores, detail, and
   shortlist.
10. Add `data_qa_app.py` before scaling to more markets.

That gives ROF the same foundation/candidate/QA shape that is now working well
in this repo, but aimed at investment-zone and retail-parcel decisions instead
of apartment search.
