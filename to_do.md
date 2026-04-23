# To-Do

Tasks are ordered by stream priority. See PLAN.md for background and wave-level detail.

---

## MVP Fixes (do before expanding)

- [ ] Deploy `app/retail_parcel_explorer_app.py` on Streamlit Community Cloud
- [ ] Deploy `app/data_qa_app.py` on Streamlit Community Cloud
- [ ] After each deploy, confirm app loads from `data/exports/jacksonville_rof.duckdb` and does not require local paths from `config/data_sources.yaml`
- [ ] Fix `app/zone_explorer_app.py` tooltip data for Cluster Zones and Contiguity Zones
- [ ] Investigate why Baker County is missing all parcels

---

## Stream 1 — Cloud Infrastructure

### Wave 1A — Evaluate MotherDuck
- [ ] Create MotherDuck account, review free tier limits
- [ ] Estimate projected data size: 7 markets × ~15k parcels + tract/zone tables
- [ ] Decide: MotherDuck vs Hugging Face file approach (document decision in PLAN.md)

### Wave 1B — Migrate Jacksonville to MotherDuck
- [ ] Update `src/retail_opportunity_finder/utils/config.py` to support MotherDuck connection string
- [ ] Update `export_from_metro.py` to write to MotherDuck (in addition to local DuckDB)
- [ ] Update `ingest_parcel_geom.py` to write to MotherDuck
- [ ] Migrate Jacksonville data to MotherDuck
- [ ] Add MotherDuck token to Streamlit Community Cloud secrets
- [ ] Redeploy Jacksonville Zone Explorer and Parcel Explorer against MotherDuck — confirm parity

### Wave 1C — Multi-market schema audit
- [ ] Audit all `rof_gold` tables to confirm `market_key` is present and used as a partition key
- [ ] Confirm `user_shortlist` is keyed per user + market (no cross-market shortlist collisions)

---

## Stream 2 — Add Orlando & Gainesville

- [ ] Add `orlando_fl` to `config/settings.yaml` (county GEOIDs, map center)
- [ ] Add `gainesville_fl` to `config/settings.yaml` (county GEOIDs, map center)
- [ ] Run `export_from_metro.py` for Orlando
- [ ] Run `export_parcel_geometry.R` for Orlando counties
- [ ] Run `ingest_parcel_geom.py` for Orlando
- [ ] Run `export_from_metro.py` for Gainesville
- [ ] Run `export_parcel_geometry.R` for Gainesville counties
- [ ] Run `ingest_parcel_geom.py` for Gainesville
- [ ] Write Orlando and Gainesville data to MotherDuck
- [ ] Deploy Zone Explorer for Orlando on Streamlit Community Cloud
- [ ] Deploy Parcel Explorer for Orlando on Streamlit Community Cloud
- [ ] Deploy Zone Explorer for Gainesville on Streamlit Community Cloud
- [ ] Deploy Parcel Explorer for Gainesville on Streamlit Community Cloud
- [ ] Smoke test both markets: geometry, scores, shortlist

---

## Stream 3 — Market Selection UI

### Wave 3A — Market selector in Zone Explorer
- [ ] Add market dropdown to Zone Explorer sidebar (populated from `config/settings.yaml`)
- [ ] Update `load_tract_data()` and `load_zone_data()` to accept `market_key`
- [ ] Update map center on market change
- [ ] Add `?market=<market_key>` URL param persistence

### Wave 3B — Market selector in Parcel Explorer
- [ ] Add market dropdown to Parcel Explorer sidebar (bridge step before market-agnostic view)

### Wave 3C — Market-agnostic Parcel Explorer (medium term)
- [ ] Research PyDeck viewport-based loading approach for 105k+ parcels
- [ ] Build pre-aggregated cluster/dot layer for low-zoom Southeast US view
- [ ] Implement zoom-triggered switch from cluster dots → parcel polygons
- [ ] Update sidebar filters to cross-market hierarchy (state → market → county)

### Wave 3D — Unified single app (long term)
- [ ] Merge Zone Explorer and Parcel Explorer into one multi-page Streamlit app
- [ ] Single deployment URL with market state persisted across pages

---

## Stream 4 — GA, SC, NC Markets

### Wave 4A — Source research
- [ ] Download and inspect NC OneMap statewide parcel layer (Wilmington = New Hanover Co., Raleigh = Wake Co.)
- [ ] Download and inspect SC Revenue and Fiscal Affairs parcel data (Greenville Co.)
- [ ] Download and inspect Chatham County GIS parcel data (Savannah, GA)
- [ ] Map each state's fields to FL FDOR normalized schema — identify gaps
- [ ] Decide: shared R normalization script with state configs vs. separate scripts per state

### Wave 4B — Build state pipelines
- [ ] Write R normalization script for NC parcels
- [ ] Write R normalization script for GA parcels (Chatham Co.)
- [ ] Write R normalization script for SC parcels
- [ ] Extend or replicate `ingest_parcel_geom.py` for each state
- [ ] Test one county per state end-to-end before full run

### Wave 4C — Run pipelines and deploy
- [ ] Add Wilmington NC to `config/settings.yaml`
- [ ] Add Savannah GA to `config/settings.yaml`
- [ ] Add Raleigh NC to `config/settings.yaml`
- [ ] Add Greenville SC to `config/settings.yaml`
- [ ] Run export + geometry pipelines for all four markets
- [ ] Write all four markets to MotherDuck
- [ ] Deploy apps for each market (or update unified app)
- [ ] QA each market: geometry coverage, score coverage, zone build

---

## Documentation

- [ ] Keep `user_guide.md` updated when the cloud deployment process changes
- [ ] Update PLAN.md architecture diagram after MotherDuck migration is complete
