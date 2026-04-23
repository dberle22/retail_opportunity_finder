"""Zone Explorer — Surface 1: CBSA / tract / zone map with demographics and scoring."""

import pandas as pd
import pydeck as pdk
import streamlit as st
import duckdb

from retail_opportunity_finder.utils.config import get_db_path, load_settings
from retail_opportunity_finder.utils.geo import add_polygon_coords
from retail_opportunity_finder.app.zone_map import (
    apply_color_ramp,
    build_label_layer,
    build_metric_options,
    build_tooltip,
    build_tract_layer,
    build_zone_layer,
    load_tract_data,
    load_zone_data,
)

st.set_page_config(page_title="Zone Explorer", layout="wide")

_settings = load_settings()
_market_key = _settings.get("default_market_key", "jacksonville_fl")
_market = _settings["markets"][_market_key]

# Carto Positron — no API key required.
_MAP_STYLE = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"


@st.cache_resource
def _get_con():
    return duckdb.connect(str(get_db_path()), read_only=True)


@st.cache_data
def _load_tracts(_con, cbsa_code: str) -> pd.DataFrame:
    return load_tract_data(_con, cbsa_code)


@st.cache_data
def _load_zones(_con, market_key: str, zone_system: str) -> pd.DataFrame:
    return load_zone_data(_con, market_key, zone_system)


@st.cache_data
def _load_boundaries(_con, cbsa_code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    cbsa_df = _con.execute(
        "SELECT cbsa_code, geom_wkt FROM rof_gold.cbsa_geometry WHERE cbsa_code = ?",
        [cbsa_code],
    ).df()
    county_df = _con.execute(
        "SELECT county_geoid, geom_wkt FROM rof_gold.county_geometry WHERE cbsa_code = ?",
        [cbsa_code],
    ).df()
    return cbsa_df, county_df


con = _get_con()
cbsa_code = _market["cbsa_code"]

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Zone Explorer")
    st.markdown(f"**Market:** {_market['label']}")
    st.divider()

    layer_mode = st.radio(
        "Layer Mode",
        options=["Tracts", "Cluster Zones", "Contiguity Zones"],
        horizontal=True,
    )

    metric_options = build_metric_options()
    st.markdown("**Metric**")
    metric_label = st.selectbox(
        "Metric",
        options=list(metric_options.keys()),
        label_visibility="collapsed",
    )
    metric_col = metric_options[metric_label]

    st.divider()
    show_eligibility = st.toggle("Dim ineligible tracts", value=False)

# ── Load data ─────────────────────────────────────────────────────────────────

zone_system = "contiguity" if layer_mode == "Contiguity Zones" else "cluster"

tract_df = _load_tracts(con, cbsa_code)
zone_df = _load_zones(con, _market_key, zone_system)
cbsa_df, county_df = _load_boundaries(con, cbsa_code)

# ── Color ramp ────────────────────────────────────────────────────────────────

colored_df = apply_color_ramp(tract_df, metric_col)

if show_eligibility:
    ineligible = colored_df["eligible_v1"].fillna(0) == 0
    colored_df.loc[ineligible, "fill_color"] = colored_df.loc[ineligible, "fill_color"].apply(
        lambda c: [c[0], c[1], c[2], 60]  # 60 keeps hover events firing; 30 suppresses them
    )

# ── Build layers ──────────────────────────────────────────────────────────────

layers: list[pdk.Layer] = [build_tract_layer(colored_df)]

cbsa_coords = add_polygon_coords(cbsa_df)
cbsa_valid = cbsa_coords[cbsa_coords["polygon_coords"].notna()]
if not cbsa_valid.empty:
    layers.append(pdk.Layer(
        "PolygonLayer",
        cbsa_valid,
        id="cbsa",
        get_polygon="polygon_coords",
        get_fill_color=[0, 0, 0, 0],
        get_line_color=[0, 0, 0, 210],
        line_width_min_pixels=2,
        stroked=True,
        filled=False,
    ))

county_coords = add_polygon_coords(county_df)
county_valid = county_coords[county_coords["polygon_coords"].notna()]
if not county_valid.empty:
    layers.append(pdk.Layer(
        "PolygonLayer",
        county_valid,
        id="counties",
        get_polygon="polygon_coords",
        get_fill_color=[0, 0, 0, 0],
        get_line_color=[80, 80, 80, 180],
        line_width_min_pixels=1.5,
        stroked=True,
        filled=False,
    ))

if layer_mode != "Tracts":
    layers.append(build_zone_layer(zone_df))
    layers.append(build_label_layer(zone_df))

# ── Render map ────────────────────────────────────────────────────────────────

view_state = pdk.ViewState(
    latitude=_market["default_map_center"]["lat"],
    longitude=_market["default_map_center"]["lon"],
    zoom=_market["default_map_zoom"],
)

layer_type = "tract" if layer_mode == "Tracts" else "zone"

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    tooltip=build_tooltip(layer_type),
    map_style=_MAP_STYLE,
)

st.pydeck_chart(deck, use_container_width=True)

# ── Below-map table ───────────────────────────────────────────────────────────

st.divider()

if layer_mode != "Tracts":
    st.subheader("Zones")
    sort_col = "mean_tract_score"
    display_cols = [c for c in ["zone_label", "tracts", "total_population", "pop_growth_3yr_wtd", "mean_tract_score"] if c in zone_df.columns]
    st.dataframe(
        zone_df[display_cols].sort_values(sort_col, ascending=False),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.subheader(f"Top Tracts — {metric_label}")
    if metric_col in tract_df.columns:
        display_cols = [c for c in ["tract_geoid", "county_geoid", metric_col, "tract_score", "eligible_v1"] if c in tract_df.columns]
        top_tracts = tract_df[display_cols].dropna(subset=[metric_col]).nlargest(15, metric_col)
        st.dataframe(top_tracts, use_container_width=True, hide_index=True)
