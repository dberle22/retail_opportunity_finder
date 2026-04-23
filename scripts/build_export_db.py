"""Build the Streamlit Cloud DuckDB artifact.

Creates data/exports/jacksonville_rof.duckdb from the local
data/processed/rof_app.duckdb. The output is intentionally self-contained:
it includes the configured market's rof_gold tables and an empty
user_shortlist table for the cloud app workflow.

Usage:
    python scripts/build_export_db.py
    python scripts/build_export_db.py --market jacksonville_fl
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from retail_opportunity_finder.utils.config import load_settings  # noqa: E402


def _sql_string(value: str) -> str:
    """Return a safely quoted SQL string literal for config-controlled values."""
    return "'" + value.replace("'", "''") + "'"


def _sql_list(values: list[str]) -> str:
    return ", ".join(_sql_string(value) for value in values)


def _remove_existing_db(path: Path) -> None:
    """Remove the previous export DB and any leftover DuckDB sidecar files."""
    for suffix in ("", ".wal"):
        candidate = Path(f"{path}{suffix}")
        if candidate.exists():
            candidate.unlink()


def _table_exists(
    con: duckdb.DuckDBPyConnection,
    catalog: str,
    schema: str,
    table: str,
) -> bool:
    return bool(
        con.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_catalog = ? AND table_schema = ? AND table_name = ?
            """,
            [catalog, schema, table],
        ).fetchone()
    )


def _copy_table(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    select_sql: str | None = None,
) -> int:
    """Copy rows from the attached source DB into the destination table."""
    if select_sql is None:
        select_sql = f"SELECT * FROM src.rof_gold.{table_name}"

    con.execute(f"DELETE FROM rof_gold.{table_name}")
    con.execute(f"INSERT INTO rof_gold.{table_name} {select_sql}")
    return con.execute(f"SELECT COUNT(*) FROM rof_gold.{table_name}").fetchone()[0]


def build_export_db(market_key: str | None = None) -> Path:
    settings = load_settings()
    market_key = market_key or settings.get("default_market_key", "jacksonville_fl")
    market_cfg = settings["markets"][market_key]

    cbsa_code = str(market_cfg["cbsa_code"])
    county_geoids = [str(geoid) for geoid in market_cfg["county_geoids"]]

    source_path = REPO_ROOT / settings["database_path"]
    export_path = REPO_ROOT / settings["export_database_path"]
    ddl_path = REPO_ROOT / "sql" / "ddl" / "001_rof_gold_tables.sql"

    if not source_path.exists():
        raise FileNotFoundError(
            f"Source DB not found: {source_path}\n"
            "Run the local export and parcel geometry pipelines before building the cloud DB."
        )

    export_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_existing_db(export_path)

    print(f"\nBuilding cloud export DB for {market_key}")
    print(f"  Source: {source_path}")
    print(f"  Dest:   {export_path}\n")

    con = duckdb.connect(str(export_path))
    con.execute(f"ATTACH {_sql_string(str(source_path))} AS src (READ_ONLY)")
    con.execute(ddl_path.read_text())

    missing_tables = [
        table
        for table in (
            "market_profiles",
            "cbsa_geometry",
            "county_geometry",
            "tract_geometry",
            "tract_features",
            "tract_scores",
            "cluster_assignments",
            "cluster_zone_summary",
            "cluster_zone_geometries",
            "contiguity_zone_summary",
            "contiguity_zone_geometries",
            "retail_parcels",
            "parcel_geometry",
            "parcel_shortlist",
            "parcel_zone_overlay",
            "retail_intensity_by_tract",
            "retail_parcel_tract_assignment",
            "user_shortlist",
        )
        if not _table_exists(con, "src", "rof_gold", table)
    ]
    if missing_tables:
        raise RuntimeError(
            "Source DB is missing expected rof_gold table(s): "
            + ", ".join(sorted(missing_tables))
        )

    market = _sql_string(market_key)
    cbsa = _sql_string(cbsa_code)
    counties = _sql_list(county_geoids)

    copy_steps: list[tuple[str, str | None]] = [
        (
            "market_profiles",
            f"SELECT * FROM src.rof_gold.market_profiles WHERE market_key = {market}",
        ),
        ("cbsa_geometry", f"SELECT * FROM src.rof_gold.cbsa_geometry WHERE cbsa_code = {cbsa}"),
        (
            "county_geometry",
            f"""
            SELECT *
            FROM src.rof_gold.county_geometry
            WHERE cbsa_code = {cbsa}
              AND county_geoid IN ({counties})
            """,
        ),
        ("tract_geometry", f"SELECT * FROM src.rof_gold.tract_geometry WHERE cbsa_code = {cbsa}"),
        ("tract_features", f"SELECT * FROM src.rof_gold.tract_features WHERE cbsa_code = {cbsa}"),
        ("tract_scores", f"SELECT * FROM src.rof_gold.tract_scores WHERE market_key = {market}"),
        (
            "cluster_assignments",
            f"SELECT * FROM src.rof_gold.cluster_assignments WHERE market_key = {market}",
        ),
        (
            "cluster_zone_summary",
            f"SELECT * FROM src.rof_gold.cluster_zone_summary WHERE market_key = {market}",
        ),
        (
            "cluster_zone_geometries",
            f"SELECT * FROM src.rof_gold.cluster_zone_geometries WHERE market_key = {market}",
        ),
        (
            "contiguity_zone_summary",
            f"SELECT * FROM src.rof_gold.contiguity_zone_summary WHERE market_key = {market}",
        ),
        (
            "contiguity_zone_geometries",
            f"SELECT * FROM src.rof_gold.contiguity_zone_geometries WHERE market_key = {market}",
        ),
        (
            "retail_parcels",
            f"""
            SELECT *
            FROM src.rof_gold.retail_parcels
            WHERE market_key = {market}
              AND county_geoid IN ({counties})
            """,
        ),
        (
            "parcel_geometry",
            f"""
            SELECT pg.*
            FROM src.rof_gold.parcel_geometry pg
            WHERE EXISTS (
                SELECT 1
                FROM src.rof_gold.retail_parcels rp
                WHERE rp.join_key = pg.join_key
                  AND rp.market_key = {market}
                  AND rp.county_geoid IN ({counties})
            )
            """,
        ),
        (
            "parcel_shortlist",
            f"SELECT * FROM src.rof_gold.parcel_shortlist WHERE market_key = {market}",
        ),
        (
            "parcel_zone_overlay",
            f"SELECT * FROM src.rof_gold.parcel_zone_overlay WHERE market_key = {market}",
        ),
        (
            "retail_intensity_by_tract",
            f"SELECT * FROM src.rof_gold.retail_intensity_by_tract WHERE market_key = {market}",
        ),
        (
            "retail_parcel_tract_assignment",
            f"""
            SELECT *
            FROM src.rof_gold.retail_parcel_tract_assignment
            WHERE market_key = {market}
              AND county_geoid IN ({counties})
            """,
        ),
    ]

    total_rows = 0
    started_at = time.time()
    for table_name, select_sql in copy_steps:
        step_started_at = time.time()
        count = _copy_table(con, table_name, select_sql)
        total_rows += count
        elapsed = time.time() - step_started_at
        print(f"  rof_gold.{table_name:<34} {count:>8,} rows ({elapsed:.1f}s)")

    con.execute("DELETE FROM rof_gold.user_shortlist")
    user_rows = con.execute("SELECT COUNT(*) FROM rof_gold.user_shortlist").fetchone()[0]
    print(f"  rof_gold.user_shortlist{'':<29} {user_rows:>8,} rows (empty cloud table)")

    con.execute("CHECKPOINT")
    con.close()

    elapsed = time.time() - started_at
    size_mb = export_path.stat().st_size / 1_048_576
    print(f"\nDone: copied {total_rows:,} rows in {elapsed:.1f}s")
    print(f"Cloud DB: {export_path} ({size_mb:.1f} MB)")
    return export_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the committed Streamlit Cloud DB artifact.")
    parser.add_argument(
        "--market",
        default=None,
        help="Market key to export. Defaults to config/settings.yaml default_market_key.",
    )
    args = parser.parse_args()
    build_export_db(market_key=args.market)


if __name__ == "__main__":
    main()
