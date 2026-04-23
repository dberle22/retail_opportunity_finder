# Cloud Deployment To-Do

## Step 1 — Build the export script
**Claude does this.** Ask Claude to write `scripts/build_export_db.py`.

## Step 2 — Generate `requirements.txt`
**Claude does this.** Claude creates it from `pyproject.toml` dependencies.

## Step 3 — Run the build script
**You do this** in your terminal:
```bash
.venv/bin/python scripts/build_export_db.py
```
Creates `data/exports/jacksonville_rof.duckdb` from `data/processed/rof_app.duckdb`.

## Step 4 — Check the file size
**You do this:**
```bash
du -sh data/exports/jacksonville_rof.duckdb
```
- **Under 50MB** → commit normally, go to Step 5
- **50–100MB** → set up Git LFS first (ask Claude to walk you through it)
- **Over 100MB** → need a different plan (ask Claude)

## Step 5 — Commit and push
**You do this:**
```bash
git add data/exports/jacksonville_rof.duckdb requirements.txt scripts/build_export_db.py
git commit -m "Add cloud export DB and requirements.txt"
git push
```

## Step 6 — Deploy on Streamlit Community Cloud
**You do this** at https://share.streamlit.io:
1. Click **New app**
2. Repo: `dberle22/retail_opportunity_finder`
3. Branch: `main`
4. Main file path: `app/zone_explorer_app.py`
5. Click **Deploy**

Repeat for the other two apps (`retail_parcel_explorer_app.py`, `data_qa_app.py`) if you want all three live.
