# ROF Frontend Repository Handoff

This document summarizes the Retail Opportunity Finder (ROF) work in this repo that is relevant to starting a separate ROF frontend application repository. It is written for the project owner and a new agent that will propose the new repo architecture, then build an interactive application for exploring CBSAs, zones, tracts, and parcels.

The goal is not to prescribe the final architecture. The goal is to make the current assets, contracts, constraints, and transition points visible enough that the new repo can make clean architecture decisions without rediscovering the existing ROF work.

## Product Intent

ROF identifies retail opportunity geographies by combining metro/tract demographic and economic features, tract-level scoring models, zone construction, and parcel-level context.

The new frontend application should support interactive exploration of:

- CBSAs and market boundaries
- counties and tracts inside each market
- scored tracts and eligibility gates
- cluster-based zones, with contiguity zones retained as a comparison/reference layer
- parcel context and retail-classified parcels where parcel data exists
- QA and coverage status so users understand when a market, zone, or parcel layer is incomplete

The current analytical/reporting product is notebook-oriented. The new app will likely need its own data-serving layer or platform that adapts these inputs into frontend-friendly formats and contracts.

## Current Repository Shape

There are two important ROF areas in this repo:

- `products/rof/`: newer productized ROF data-platform and feature-store assets.
- `notebooks/retail_opportunity_finder/`: legacy and transitional ROF notebook/reporting pipeline, including section modules, integration QMD, generated artifacts, and the original data-platform layer work.

The `products/rof` tree is the better conceptual home for future source-of-truth contracts. The `notebooks/retail_opportunity_finder` tree still contains much of the operational build logic, generated examples, and compatibility outputs.

Important top-level docs and contracts:

- `products/rof/README.md`
- `products/rof/data_platform/contracts/duckdb_schemas.md`
- `products/rof/data_platform/contracts/table_lineage_map.md`
- `products/rof/data_platform/contracts/table_naming_conventions.md`
- `products/rof/docs/rof_tract_models_reference.md`
- `notebooks/retail_opportunity_finder/README.md`
- `notebooks/retail_opportunity_finder/sections/OUTPUT_CONTRACTS.md`

## Current Operating Mode

The active ROF path is cluster-first.

Cluster zones are the primary MVP zone system. Contiguity artifacts are still published and useful for comparison, QA, and historical reference, but they should not be treated as the main narrative path unless the new architecture explicitly decides otherwise.

Current working geography scope:

- Zone-ready multi-market slice: 115 markets/CBSAs across Florida, Georgia, North Carolina, and South Carolina.
- Current zone layer state coverage:
  - FL: 28 markets
  - GA: 36 markets
  - NC: 37 markets
  - SC: 14 markets
- Two scored markets were skipped in the latest zone build because cluster-seed tracts were missing from tract geometry:
  - `cbsa_12260` / `12260` / GA
  - `cbsa_16740` / `16740` / NC
- Parcel work is strongest in Florida and remains operationally county-first.

The frontend repo should start from all available ROF markets, not only Jacksonville. Expansion work should be planned in the new repo, but the current handoff should make the present coverage limits visible.

## Data Platform Schemas

The ROF V2 transition defines the following DuckDB schemas:

- `raw_ext`: externally landed source snapshots and raw extracts.
- `ref`: stable dimensions, market membership tables, and conformed reference mappings.
- `foundation`: tract- and metro-level feature products.
- `scoring`: legacy tract scoring outputs and cluster seed membership.
- `rof_features`: newer ROF feature-store schema used by tract model assets.
- `zones`: tract-to-zone assignments, zone summaries, and zone geometry products.
- `parcel`: canonical parcel attributes and parcel QA products.
- `serving`: future market-serving preparation layer.
- `qa`: validation summaries, coverage checks, lineage checkpoints, and run audit tables.

Relevant contract source:

- `products/rof/data_platform/contracts/duckdb_schemas.md`

## Key Data Products For The App

### Market and Reference Tables

The app will need market identity, CBSA membership, county membership, tract identity, and land-use classification.

Important current/reference tables:

- `ref.market_profiles`
- `ref.market_cbsa_membership`
- `ref.market_county_membership`
- `ref.county_dim`
- `ref.tract_dim`
- `ref.land_use_mapping`
- `qa.ref_validation_results`
- `qa.ref_geography_coverage`
- `qa.ref_unmapped_land_use_codes`

Important source paths:

- `notebooks/retail_opportunity_finder/sections/_shared/market_profiles.R`
- `products/rof/data_platform/contracts/table_lineage_map.md`
- `notebooks/retail_opportunity_finder/land_use_code_mapping.csv`

Note: the old shared market profile registry explicitly names seven report markets: Jacksonville, Orlando, Gainesville, Wilmington, Savannah, Raleigh, and Greenville. The newer ROF data-platform path has expanded beyond those manually named report markets into a broader Southeast CBSA slice.

### CBSA Features

`foundation.cbsa_features` / `rof_features.cbsa_features` provide metro-level benchmark context.

Current role:

- one row per `cbsa_code`, `year`
- national CBSA benchmark context
- metrics include population, growth, rent/value, commute, BPS permits, ranks, and percentiles

Important source paths:

- `products/rof/data_platform/feature_store/base_features/rof_features.cbsa_features.sql`
- `products/rof/data_platform/feature_store/base_features/rof_features.cbsa_features.md`
- `notebooks/retail_opportunity_finder/data_platform/layers/01_foundation_features/tables/foundation.cbsa_features.sql`

Current caution:

- The documented live `foundation.cbsa_features` snapshot was national in content but still carried Jacksonville-oriented metadata in places.
- The frontend-serving contract should decide whether metro benchmark data belongs in a global benchmark table, a market-serving table, or both.

### Tract Features

`rof_features.tract_features` is the current productized tract feature spine.

Current role:

- one row per `cbsa_code`, `county_geoid`, `tract_geoid`, `year`
- target year is currently hard-coded/materialized around 2024 in the active SQL
- market-relative percentile logic is partitioned by `cbsa_code`
- downstream consumers filter by `cbsa_code` instead of rebuilding features per market

Important feature fields:

- population total and growth
- median household income and per-capita income
- poverty rate
- median gross rent and home value
- commute/work-from-home metrics
- permits per population via county-level BPS rolling average
- population density
- growth, income, rent, value, and density percentiles
- eligibility gates such as growth, price, and density gate flags

Important source paths:

- `products/rof/data_platform/feature_store/base_features/rof_features.tract_features.sql`
- `products/rof/data_platform/feature_store/base_features/rof_features.tract_features.md`
- `notebooks/retail_opportunity_finder/data_platform/layers/01_foundation_features/tables/foundation.tract_features.sql`
- `docs/gold_layer_dag.md`

Current limitations:

- The tract universe and tract geometry backbone have moved toward national coverage.
- Feature coverage is still limited by upstream ACS tract KPI parents that currently cover tract rows for FL, GA, NC, and SC.
- Expansion should happen upstream in the ACS/Gold tract KPI parents rather than through another ROF-specific workaround.

### Tract Models and Seed Tracts

The newer feature-store scoring path is centered on `rof_features.tract_models`.

Current role:

- canonical wide tract scoring output for the ROF tract-model framework
- one row per `cbsa_code`, `tract_geoid`
- built from `rof_features.tract_features`
- computes model scores and ranks within each CBSA

Current model variants:

- `balanced`
- `growth`
- `value`
- `corridor`

Important output fields:

- raw feature values
- z-scores and inverse z-scores
- eligibility gate flags
- model scores
- CBSA ranks
- national ranks

`rof_features.cluster_seed_tracts` is the model-aware seed table:

- one row per `cbsa_code`, `tract_geoid`, `model_name`
- retains top 25% of eligible tracts for each model
- designed to allow downstream zone workflows to choose a model at runtime

Important source paths:

- `products/rof/docs/rof_tract_models_reference.md`
- `products/rof/data_platform/feature_store/scores/rof_features.tract_models.sql`
- `products/rof/data_platform/feature_store/scores/rof_features.tract_models.md`
- `products/rof/data_platform/feature_store/scores/rof_features.cluster_seed_tracts.sql`
- `products/rof/data_platform/feature_store/scores/rof_features.cluster_seed_tracts.md`
- `products/rof/data_platform/feature_store/scores/rof_features.tract_model_audit.sql`
- `products/rof/data_platform/feature_store/scores/rof_features.tract_model_audit.md`

Important transition note:

- The newer `rof_features.*` scoring assets are cleaner for a future app.
- The current zone build still consumes the legacy `scoring.*` contract.
- A new app data platform should decide whether to migrate zone building to `rof_features.cluster_seed_tracts` or keep a compatibility bridge from legacy `scoring.*` until zone logic is refactored.

### Geometry Serving Tables

Current geometry is published in DuckDB-friendly `geom_wkt` form for CBSA, county, tract, and zone layers.

Important tables:

- `foundation.market_cbsa_geometry`
  - grain: one row per `cbsa_code`
  - documented live rows: 935
  - source path: `products/rof/data_platform/foundation/foundation.market_cbsa_geometry.md`
- `foundation.market_county_geometry`
  - grain: one row per `cbsa_code`, `county_geoid`
  - documented live rows: 1,915
  - source path: `products/rof/data_platform/foundation/foundation.market_county_geometry.md`
- `foundation.market_tract_geometry`
  - grain: one row per `cbsa_code`, `tract_geoid`
  - documented live rows: 10,020 across 106 CBSAs at the time of profiling
  - source path: `products/rof/data_platform/foundation/foundation.market_tract_geometry.md`

Geometry caveats:

- `geom_wkt` is useful as a compatibility format, but a frontend app will likely want prepared vector tiles, GeoJSON, PMTiles, FlatGeobuf, GeoParquet, or an API that returns clipped/simplified features.
- The new repo should choose its own serving format after evaluating map performance and update patterns.
- Do not assume the current WKT-in-DuckDB format is the final web-serving design.

### Zone Tables

Zone construction currently publishes both cluster and contiguity products.

Cluster products:

- `zones.cluster_assignments`
  - grain: one row per `market_key`, `tract_geoid`
  - role: tract-to-cluster assignment table
  - documented live rows: 2,629 across 115 markets
- `zones.cluster_zone_summary`
  - grain: one row per `market_key`, `cluster_id`
  - role: zone-level KPI summary
  - documented live rows: 447 across 115 markets
- `zones.cluster_zone_geometries`
  - grain: one row per `market_key`, `cluster_id`
  - role: dissolved cluster-zone polygons in `geom_wkt`
  - includes `zone_area_sq_mi`, `label_lon`, and `label_lat`
  - documented live rows: 447 across 115 markets

Contiguity products:

- `zones.contiguity_zone_components`
- `zones.contiguity_zone_summary`
- `zones.contiguity_zone_geometries`

Shared zone input:

- `zones.zone_input_candidates`

Important source paths:

- `products/rof/data_platform/zones/README.md`
- `products/rof/data_platform/zones/zones.zone_input_candidates.md`
- `products/rof/data_platform/zones/clusters/zones.cluster_assignments.md`
- `products/rof/data_platform/zones/clusters/zones.cluster_zone_summary.md`
- `products/rof/data_platform/zones/clusters/zones.cluster_zone_geometries.md`
- `products/rof/data_platform/zones/contiguity/zones.contiguity_zone_components.md`
- `products/rof/data_platform/zones/contiguity/zones.contiguity_zone_summary.md`
- `products/rof/data_platform/zones/contiguity/zones.contiguity_zone_geometries.md`
- `notebooks/retail_opportunity_finder/data_platform/layers/03_zone_build/zone_build_workflow.R`
- `notebooks/retail_opportunity_finder/data_platform/layers/03_zone_build/run_zone_build_layer.R`

Important transition note:

- Current zone logic is procedural R because it contains spatial clustering and geometry handling.
- The new repo should be free to decide whether zone building remains an offline batch process, becomes a parameterized data-platform job, or is split into precomputed defaults plus interactive model/threshold variants.

### Parcel Tables and Parcel Geometry

Parcel standardization is intentionally split:

- canonical parcel attributes are in DuckDB
- parcel geometries remain in existing county `.RDS` analysis artifacts

Current DuckDB parcel products:

- `parcel.parcels_canonical`
  - grain: one row per `parcel_uid`
  - no geometry
  - market-aware canonical parcel table with normalized fields
  - includes retail classification fields from `ref.land_use_mapping`
- `parcel.parcel_lineage`
  - grain: one row per parcel-backed market county
  - operational lineage and published parcel counts
- `parcel.parcel_join_qa`
  - compatibility county-grain QA projection
- `parcel.retail_parcels`
  - deprecated compatibility subset
  - use `parcel.parcels_canonical` with `retail_flag = TRUE`
- `qa.parcel_validation_results`
- `qa.parcel_unmapped_use_codes`

Important source paths:

- `products/rof/data_platform/parcels/README.md`
- `products/rof/data_platform/parcels/build_parcel_standardization_layer.sql`
- `products/rof/data_platform/parcels/state_scripts/fl_parcel_etl_manual_county.R`
- `products/rof/data_platform/parcels/state_scripts/README.md`
- `notebooks/retail_opportunity_finder/sections/05_parcels/final_pipeline_strategy_and_approach.md`
- `notebooks/retail_opportunity_finder/sections/05_parcels/parcel_standardization/README.md`
- `notebooks/retail_opportunity_finder/data_platform/layers/04_parcel_standardization/parcel_standardization_workflow.R`
- `notebooks/retail_opportunity_finder/data_platform/layers/04_parcel_standardization/run_parcel_standardization_layer.R`

Parcel geometry handoff contract:

- `ROF_PARCEL_STANDARDIZED_ROOT` may override the parcel standardized root.
- County analysis geometry artifacts are expected at:
  - `county_outputs/<county_tag>/parcel_geometries_analysis.rds`
- Manifest-driven paths may come from:
  - `parcel_ingest_manifest.rds`
- Required geometry artifact columns include:
  - `join_key`
  - `parcel_id`
  - `county`
  - `county_name`
  - `use_code`
  - `land_value`
  - `total_value`
  - `sale_price1`
  - `sale_yr1`
  - `sale_mo1`
  - `qa_missing_join_key`
  - `qa_zero_county`
  - `geometry`
- Storage CRS should be EPSG:4326.

Important guidance for the new repo:

- Treat the existing `.RDS` parcel geometry artifacts as MVP-ready inputs where they exist.
- Do not restart the old loop of trying to automatically read every source parcel geometry into a database as an early priority.
- The valuable pattern is county-first, manual-operational parcel geometry processing with explicit QA.
- A safer improvement path is to create a controlled export step from reviewed `.RDS` county artifacts into web-serving artifacts for only the counties/markets that are already QA-ready.
- If the new app needs parcel polygons, prefer a deliberate frontend-serving export from known-good county artifacts over a broad automated raw-geometry ingestion system.
- Preserve the county as the unit of parcel geometry QA, rerun, and replacement.

## Current Notebook/Report Artifacts Worth Knowing

The notebook pipeline is organized as:

`01_setup -> 02_market_overview -> 03_eligibility_scoring -> 04_zones -> 05_parcels -> 06_conclusion_appendix`

Important paths:

- `notebooks/retail_opportunity_finder/integration/qmd/retail_opportunity_finder_mvp.qmd`
- `notebooks/retail_opportunity_finder/sections/`
- `notebooks/retail_opportunity_finder/sections/OUTPUT_CONTRACTS.md`
- `notebooks/retail_opportunity_finder/notebook_build/sections/`

Useful generated map examples exist under:

- `notebooks/retail_opportunity_finder/sections/04_zones/outputs/*/section_04_cluster_zone_map.png`
- `notebooks/retail_opportunity_finder/sections/04_zones/outputs/*/section_04_zone_map.png`
- `notebooks/retail_opportunity_finder/sections/05_parcels/outputs/*/section_05_market_parcel_context_map.png`
- `notebooks/retail_opportunity_finder/sections/05_parcels/outputs/*/section_05_cluster_parcel_overlay_map.png`
- `notebooks/retail_opportunity_finder/sections/05_parcels/outputs/*/section_05_shortlist_map_cluster.png`

These images are not data-platform source-of-truth, but they are useful design references for layer semantics and map intent.

## Expansion Needs

The new app should begin with all available ROF markets, while clearly tracking what prevents broader coverage.

Known expansion needs:

- Expand upstream ACS tract KPI coverage beyond FL, GA, NC, and SC.
- Rebuild the Gold/Silver parents that feed `rof_features.tract_features` after coverage expands.
- Confirm `gold.population_demographics`, `silver.income_kpi`, `silver.housing_kpi`, and `silver.transport_kpi` have tract coverage for desired states.
- Ensure `silver.xwalk_tract_county`, `silver.xwalk_cbsa_county`, and geometry backbones are current for target geographies.
- Resolve the skipped zone markets where cluster-seed tracts are missing from tract geometry.
- Decide whether zone generation should continue to use legacy `scoring.*` or migrate to `rof_features.*`.
- Expand parcel availability state by state, but keep the manual county-first geometry QA model unless there is a very strong reason to change it.
- Create explicit coverage/QA outputs that the app can show or use to disable incomplete layers.

Useful source path for tract coverage:

- `docs/gold_layer_dag.md`

## What To Migrate Or Copy Into The New Repo

The new repo should not blindly copy the whole notebook pipeline. It should selectively migrate contracts, build logic, sample data, and visual references.

Recommended context/docs to copy or port:

- `products/rof/docs/rof_frontend_repo_handoff.md`
- `products/rof/docs/rof_tract_models_reference.md`
- `products/rof/data_platform/contracts/duckdb_schemas.md`
- `products/rof/data_platform/contracts/table_lineage_map.md`
- `products/rof/data_platform/contracts/table_naming_conventions.md`
- `notebooks/retail_opportunity_finder/sections/OUTPUT_CONTRACTS.md`
- `notebooks/retail_opportunity_finder/sections/05_parcels/final_pipeline_strategy_and_approach.md`
- `docs/gold_layer_dag.md`

Recommended SQL/R build assets to inspect and possibly port:

- `products/rof/data_platform/feature_store/base_features/rof_features.tract_features.sql`
- `products/rof/data_platform/feature_store/base_features/rof_features.cbsa_features.sql`
- `products/rof/data_platform/feature_store/scores/rof_features.tract_models.sql`
- `products/rof/data_platform/feature_store/scores/rof_features.cluster_seed_tracts.sql`
- `products/rof/data_platform/feature_store/scores/rof_features.tract_model_audit.sql`
- `products/rof/data_platform/parcels/build_parcel_standardization_layer.sql`
- `notebooks/retail_opportunity_finder/data_platform/layers/03_zone_build/zone_build_workflow.R`
- `notebooks/retail_opportunity_finder/data_platform/layers/03_zone_build/run_zone_build_layer.R`
- `notebooks/retail_opportunity_finder/data_platform/layers/04_parcel_standardization/parcel_standardization_workflow.R`
- `products/rof/data_platform/parcels/state_scripts/fl_parcel_etl_manual_county.R`

Recommended table docs to copy or use as source contracts:

- `products/rof/data_platform/feature_store/base_features/*.md`
- `products/rof/data_platform/feature_store/scores/*.md`
- `products/rof/data_platform/foundation/*.md`
- `products/rof/data_platform/zones/**/*.md`
- `products/rof/data_platform/parcels/README.md`

Recommended generated references to copy selectively:

- market-level PNG examples from `notebooks/retail_opportunity_finder/sections/04_zones/outputs/`
- parcel map PNG examples from `notebooks/retail_opportunity_finder/sections/05_parcels/outputs/`
- integrated report reference from `notebooks/retail_opportunity_finder/integration/qmd/retail_opportunity_finder_mvp.qmd`

Recommended data exports to create rather than copy raw:

- all available CBSA boundary features
- all available county boundary features
- all available tract geometry/features for ROF markets
- cluster zone geometries and summaries
- cluster assignments
- parcel canonical attributes for parcel-backed counties
- reviewed parcel geometry exports for QA-ready counties
- QA/coverage manifests for every layer

The export format should be chosen in the new repo. Candidates include GeoParquet, FlatGeobuf, GeoJSON for small samples, PMTiles/vector tiles for map rendering, or an API-backed format.

## Architecture Questions For The New Agent

The new agent should propose the architecture rather than inherit one from this handoff. It should explicitly decide:

- whether the app data platform lives fully inside the new repo or consumes built artifacts from this repo
- whether DuckDB remains the local analytical build engine
- what the app-serving geometry format should be
- whether to precompute vector tiles or serve features dynamically
- whether zone generation is offline-only or parameterized by selected tract model
- whether the default model is `balanced` or user-selectable among `balanced`, `growth`, `value`, and `corridor`
- how to represent coverage and QA states in the UI
- how parcel geometry should be exported from reviewed `.RDS` artifacts without recreating an automated raw parcel ingestion project
- how much of the R-based spatial workflow should be retained versus ported
- whether current `geom_wkt` tables are source tables, intermediate tables, or serving tables in the new architecture

## Recommended Non-Binding Design Principles

These are recommendations, not final architecture decisions.

- Keep all currently available ROF markets visible from the start, with per-layer coverage indicators.
- Treat cluster zones as the default map layer, with contiguity zones as a comparison layer.
- Make score model and eligibility gates inspectable at the tract level.
- Keep parcel geometry processing county-first and QA-first.
- Avoid broad automated parcel geometry ingestion until there is a specific, tested reason to revisit it.
- Separate analytical source-of-truth tables from frontend-serving artifacts.
- Build small, deterministic data export jobs before building a complex application backend.
- Carry lineage fields such as `build_source`, `run_timestamp`, market keys, CBSA codes, and QA status into the app-serving layer.
- Make coverage gaps first-class data, not tribal knowledge.

## Known Risk Areas

- Two scoring generations coexist: legacy `scoring.*` feeds current zones, while newer `rof_features.*` is the cleaner future scoring surface.
- Some documented live table snapshots are transition snapshots and may lag the newest SQL asset paths.
- The notebook/report pipeline still has generated artifacts and compatibility outputs that are useful but should not be mistaken for durable source-of-truth.
- Parcel geometry is not in DuckDB and should not be forced there as a first step.
- Tract feature expansion depends on upstream Silver/Gold ACS coverage, not just ROF SQL.
- Web map performance will likely require a serving format beyond raw WKT.

## Practical First Context For The New Repo

Start by reading these files in order:

1. `products/rof/docs/rof_frontend_repo_handoff.md`
2. `products/rof/data_platform/contracts/table_lineage_map.md`
3. `products/rof/data_platform/contracts/duckdb_schemas.md`
4. `products/rof/docs/rof_tract_models_reference.md`
5. `products/rof/data_platform/zones/README.md`
6. `products/rof/data_platform/parcels/README.md`
7. `notebooks/retail_opportunity_finder/sections/OUTPUT_CONTRACTS.md`
8. `docs/gold_layer_dag.md`

Then inspect the SQL/R assets only as needed for the chosen architecture.

