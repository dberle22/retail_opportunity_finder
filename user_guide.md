# User Guide

This file outlines how to use the application and the data platform that supports it.

## Main Use Cases

### Load the Streamlit dashboard locally
To run locally:
```bash
streamlit run app/retail_parcel_explorer_app.py
```

### Deploy another Streamlit app to Streamlit Community Cloud
Use this process when adding another app entry point, such as `app/retail_parcel_explorer_app.py` or `app/data_qa_app.py`, to the same Streamlit Cloud deployment pattern used for `app/zone_explorer_app.py`.

#### 1. Create or update the app entry point
Place the Streamlit file under `app/`.

Each app should read the DuckDB path through the shared config helper:
```python
from retail_opportunity_finder.utils.config import get_db_path

db_path = get_db_path()
```

This keeps local and cloud behavior consistent:
- Local development uses `data/processed/rof_app.duckdb` when `config/data_sources.yaml` exists.
- Streamlit Cloud uses `data/exports/jacksonville_rof.duckdb` because `config/data_sources.yaml` is gitignored and absent there.

#### 2. Confirm the cloud export contains the app's required tables
The committed cloud database is built by:
```bash
.venv/bin/python scripts/build_export_db.py
```

If the new app needs additional `rof_gold` tables, add those tables to `scripts/build_export_db.py` before rebuilding:
- Include the table in the expected-table check.
- Add a copy step that filters to the configured market where needed.
- Make sure the table DDL exists in `sql/ddl/001_rof_gold_tables.sql`.

Keep the cloud export self-contained. It should not depend on local files, absolute paths, or `config/data_sources.yaml`.

#### 3. Update Python dependencies
If the app imports a new package, add it to `requirements.txt` so Streamlit Cloud installs it during deployment.

#### 4. Rebuild and check the export database
Run:
```bash
.venv/bin/python scripts/build_export_db.py
du -sh data/exports/jacksonville_rof.duckdb
```

Size guidance:
- Under 50MB: commit normally.
- 50-100MB: set up Git LFS before committing.
- Over 100MB: choose a smaller export or another deployment approach.

#### 5. Test the app locally
Run the app from the repo root:
```bash
streamlit run app/<app_file>.py
```

For a cloud-like check, temporarily move `config/data_sources.yaml` out of the way, run the app, and then restore it. With that file absent, `get_db_path()` should fall back to the committed export database.

#### 6. Commit and push
Commit the app, export database, dependency updates, and any export-script changes:
```bash
git add app/<app_file>.py requirements.txt scripts/build_export_db.py data/exports/jacksonville_rof.duckdb
git commit -m "Add Streamlit cloud app"
git push
```

Adjust the `git add` command to include only files that changed.

#### 7. Add the app in Streamlit Community Cloud
Go to https://share.streamlit.io and create a new app:
1. Click **New app**.
2. Repo: `dberle22/retail_opportunity_finder`.
3. Branch: `main`.
4. Main file path: `app/<app_file>.py`.
5. Click **Deploy**.

Each Streamlit entry point is deployed separately unless we later add a multi-page wrapper app.

### Adjust the Scoring Gates

## Follow up questions

### Why is Baker county missing all parcels?

### In app/zone_explorer_app.py the tool tip stops working once we switch to Cluster Zones or Contiguity Zones
In the app the tool tip shows tract demographic data as we hover over each one. When we switch to Cluster Zones and Contiguity Zones layers the tool tip still shows up but it's missing data. The zone label shows like {zone_label} same with {tracts} and all the demographics.
