"""UrbanPulse Nepal interactive dashboard.

Launch at the repository root with ``streamlit run dashboard.py``.
The app reads saved notebook artifacts; it does not fetch data or refit models.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import folium
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
PROCESSED_ROOT = DATA_ROOT / "processed"
GREEN = "#176447"
FOREST = "#103b2c"
MINT = "#74aa8c"
INK = "#1c2c23"
MUTED = "#68786e"
PALE = "#eef4ef"
GOLD = "#cf9c3f"

st.set_page_config(
    page_title="UrbanPulse Nepal",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
      :root {{ --forest: {FOREST}; --green: {GREEN}; --mint: {MINT}; --ink: {INK}; --muted: {MUTED}; }}
      .stApp {{ background: #f4f7f3; color: var(--ink); }}
      [data-testid="stHeader"] {{ background: rgba(244,247,243,.94); }}
      [data-testid="stToolbar"] {{ right: 1rem; }}
      .block-container {{ max-width: 1680px; padding: 1.1rem 1.8rem 2.5rem; }}
      div[data-testid="stColumn"] {{ min-width: 0; }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) {{
        background: linear-gradient(160deg, #123b2c 0%, #174b36 100%);
        border-radius: 18px; padding: 1.25rem 1rem 1.4rem; min-height: 78vh;
        box-shadow: 0 12px 28px rgba(17,54,39,.12);
      }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) h1,
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) h2,
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) h3,
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) p,
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) label {{ color: #edf5ef !important; }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) [data-testid="stCaptionContainer"] {{ color: #c5d8ca !important; }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) [data-testid="stWidgetLabel"] p {{ color: #d8e8dc !important; }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) [data-testid="stRadio"] label {{
        padding: .45rem .55rem; border-radius: 9px; transition: background .18s ease, transform .18s ease;
      }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) [data-testid="stRadio"] label:hover {{
        background: rgba(255,255,255,.10); transform: translateX(2px);
      }}
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) [data-baseweb="select"] > div,
      div[data-testid="stColumn"]:has([data-testid="stRadio"]) input {{ background: #fbfdfb; }}
      .brand-mark {{ width: 40px; height: 40px; border-radius: 12px; background: #d8eddf; color: #123b2c;
        display: inline-flex; align-items: center; justify-content: center; font-size: 1.3rem; margin-bottom: .7rem; }}
      .eyebrow {{ text-transform: uppercase; letter-spacing: .13em; font-size: .68rem; color: #809086; font-weight: 700; }}
      .page-title {{ font-size: 1.8rem; line-height: 1.15; font-weight: 750; color: #18382a; margin: .1rem 0 .2rem; }}
      .page-subtitle {{ color: #718077; font-size: .94rem; margin-bottom: .9rem; }}
      .coverage-pill {{ display: inline-block; background: #fff2d7; color: #70531c; border: 1px solid #ead6a6;
        border-radius: 999px; font-size: .72rem; font-weight: 700; padding: .3rem .65rem; }}
      .section-label {{ color: #748278; font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .09em; }}
      div[data-testid="stMetric"] {{ background: white; border: 1px solid #e2e9e2; border-radius: 14px; padding: .85rem 1rem; box-shadow: 0 2px 8px rgba(31,53,40,.035); transition: transform .18s ease, box-shadow .18s ease; }}
      div[data-testid="stMetric"]:hover {{ transform: translateY(-2px); box-shadow: 0 8px 18px rgba(31,53,40,.08); }}
      div[data-testid="stMetricLabel"] p {{ color: #718077; font-size: .78rem; }}
      div[data-testid="stMetricValue"] {{ color: #173d2b; font-size: 1.55rem; }}
      div[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: #e2e9e2; border-radius: 15px; background: white; }}
      .stButton button, .stDownloadButton button {{ border-radius: 10px; font-weight: 650; transition: all .18s ease; }}
      .stButton button:hover, .stDownloadButton button:hover {{ border-color: #176447; color: #176447; transform: translateY(-1px); }}
      h2, h3 {{ color: #1a3c2b; }}
      [data-testid="stDataFrame"] {{ border: 1px solid #e3eae3; border-radius: 12px; overflow: hidden; }}
      @media (max-width: 900px) {{ .block-container {{ padding-left: .8rem; padding-right: .8rem; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading saved analysis…")
def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


@st.cache_data(show_spinner=False)
def read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_artifact_dir(parent: Path, required_file: str) -> Path | None:
    if not parent.exists():
        return None
    options = sorted(
        (path for path in parent.iterdir() if (path / required_file).is_file()),
        key=lambda path: path.name,
    )
    return options[-1] if options else None


def parse_wards(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value) if value.lstrip().startswith("[") else ast.literal_eval(value)
            return list(result) if isinstance(result, (list, tuple)) else []
        except (ValueError, SyntaxError, json.JSONDecodeError):
            return []
    return []


@st.cache_data(show_spinner="Connecting incident points to BIPAD municipalities…")
def load_incidents(snapshot_path: str, municipality_lookup_path: str | None) -> pd.DataFrame:
    frame = pd.read_csv(snapshot_path, low_memory=False)
    frame["id"] = frame["id"].astype("string")
    frame["incident_datetime"] = pd.to_datetime(
        frame.get("incidentOn_nepal"), errors="coerce", utc=True
    ).dt.tz_convert("Asia/Kathmandu")
    for coordinate in ("latitude", "longitude"):
        frame[coordinate] = pd.to_numeric(frame.get(coordinate), errors="coerce")
    frame["hazard_id"] = frame.get("hazard_id", pd.Series(index=frame.index, dtype="string")).astype("string")
    frame["incident_season"] = frame.get("incident_season", pd.Series(index=frame.index, dtype="string")).astype("string")
    frame["municipality_name"] = "Not mapped"
    frame["municipality_id"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    if municipality_lookup_path and "wards" in frame:
        lookup = pd.read_csv(
            municipality_lookup_path,
            dtype={"ward_id": "string", "municipality_id": "string"},
            usecols=["ward_id", "municipality_id", "municipality_name"],
        ).drop_duplicates("ward_id")
        ward_to_municipality = lookup.set_index("ward_id")[["municipality_id", "municipality_name"]]
        long = frame[["id", "wards"]].copy()
        long["ward_id"] = long["wards"].map(parse_wards)
        long = long.explode("ward_id")
        long["ward_id"] = long["ward_id"].astype("string")
        long = long.join(ward_to_municipality, on="ward_id").dropna(subset=["municipality_id"])
        long = long.drop_duplicates("id").set_index("id")
        municipalities = long[["municipality_id", "municipality_name"]]
        frame = frame.set_index("id")
        frame.loc[municipalities.index, "municipality_id"] = municipalities["municipality_id"]
        frame.loc[municipalities.index, "municipality_name"] = municipalities["municipality_name"]
        frame = frame.reset_index()
    return frame


SNAPSHOT_DIR = latest_artifact_dir(PROCESSED_ROOT / "bipad_incidents", "incidents_processed.csv")
if SNAPSHOT_DIR is None:
    st.error("Processed BIPAD records were not found. Run notebooks 01 and 02 first.")
    st.stop()

SNAPSHOT_ID = SNAPSHOT_DIR.name
LOOKUP_DIR = latest_artifact_dir(DATA_ROOT / "raw" / "bipad_admin_lookup", "ward_to_municipality.csv")
quality = read_json(str(SNAPSHOT_DIR / "data_quality_report.json")) if (SNAPSHOT_DIR / "data_quality_report.json").is_file() else {}
quality_audit = quality.get("quality_audit", {})
incidents = load_incidents(
    str(SNAPSHOT_DIR / "incidents_processed.csv"),
    str(LOOKUP_DIR / "ward_to_municipality.csv") if LOOKUP_DIR else None,
)

NAV_ITEMS = ["Overview", "Nepal map", "Trends", "Municipalities", "Anomalies", "Model lab", "Data quality"]
valid_dates = incidents["incident_datetime"].dropna()
if valid_dates.empty:
    st.error("No parseable incident dates are available in this snapshot.")
    st.stop()

min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
hazard_options = sorted(incidents["hazard_id"].dropna().astype(str).unique())
municipality_options = sorted(incidents.loc[incidents["municipality_name"] != "Not mapped", "municipality_name"].dropna().unique())

left, main = st.columns([0.235, 0.765], gap="large")
with left:
    with st.container(border=True):
        st.markdown('<div class="brand-mark">✦</div>', unsafe_allow_html=True)
        st.markdown("### URBANPULSE")
        st.caption("NEPAL · DISASTER INTELLIGENCE")
        st.markdown("<div class='section-label'>Workspace</div>", unsafe_allow_html=True)
        page = st.radio("Workspace", NAV_ITEMS, index=1, label_visibility="collapsed", key="page_nav")
        st.divider()
        st.markdown("<div class='section-label'>Filters</div>", unsafe_allow_html=True)
        selected_dates = st.date_input(
            "Incident date",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="global_date_filter",
        )
        if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
            date_start, date_end = selected_dates
        else:
            date_start = date_end = selected_dates
        selected_hazards = st.multiselect(
            "Hazard ID",
            hazard_options,
            default=hazard_options,
            placeholder="All hazard IDs",
            help="Numeric BIPAD IDs are shown until a verified label lookup is added.",
            key="global_hazard_filter",
        )
        selected_municipality = st.selectbox(
            "Municipality",
            ["All municipalities"] + municipality_options,
            index=0,
            key="global_municipality_filter",
        )
        if st.button("Reset filters", use_container_width=True):
            for key in ("global_date_filter", "global_hazard_filter", "global_municipality_filter"):
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()
        st.caption(f"Snapshot  ·  {SNAPSHOT_ID}")
        st.caption("Source  ·  BIPAD Portal API")
        st.markdown(
            "<span class='coverage-pill'>Historical coverage unverified</span>",
            unsafe_allow_html=True,
        )

filtered = incidents.copy()
local_days = filtered["incident_datetime"].dt.date
filtered = filtered.loc[local_days.between(date_start, date_end)]
if selected_hazards:
    filtered = filtered.loc[filtered["hazard_id"].astype(str).isin(selected_hazards)]
else:
    filtered = filtered.iloc[0:0]
if selected_municipality != "All municipalities":
    filtered = filtered.loc[filtered["municipality_name"] == selected_municipality]
filtered = filtered.copy()

period_text = "No matching dates"
if not filtered.empty:
    period_text = f"{filtered['incident_datetime'].min():%Y} — {filtered['incident_datetime'].max():%Y}"


def header(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='page-title'>{title}</div><div class='page-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def metrics() -> None:
    cols = st.columns(4)
    values = [
        ("INCIDENT RECORDS", f"{len(filtered):,}"),
        ("MUNICIPALITIES", f"{filtered.loc[filtered['municipality_name'] != 'Not mapped', 'municipality_id'].nunique():,}"),
        ("HAZARD IDS", f"{filtered['hazard_id'].nunique():,}"),
        ("DATE WINDOW", period_text),
    ]
    for col, (label, value) in zip(cols, values):
        col.metric(label, value)


def chart_theme(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=25, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=INK, size=12),
        hoverlabel=dict(bgcolor=FOREST, font_color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e3eae3")
    fig.update_yaxes(gridcolor="#edf1ed", zeroline=False)
    return fig


def panel_title(title: str, meta: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if meta:
        st.caption(meta)


with main:
    st.markdown(
        f"<div class='eyebrow'>BIPAD PORTAL · HISTORICAL ANALYSIS</div>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;gap:1rem'>"
        f"<div><div class='page-title'>{page}</div><div class='page-subtitle'>Explore recorded disaster patterns across Nepal</div></div>"
        f"<span class='coverage-pill'>Coverage not verified</span></div>",
        unsafe_allow_html=True,
    )
    metrics()

    if page == "Overview":
        c1, c2 = st.columns([1.45, 1], gap="medium")
        with c1:
            with st.container(border=True):
                panel_title("Incident activity", "Monthly reports in the selected window")
                if filtered.empty:
                    st.info("No records match the current filters.")
                else:
                    series = filtered.assign(month=filtered["incident_datetime"].dt.to_period("M").astype(str)).groupby("month").size().reset_index(name="Records")
                    fig = px.area(series, x="month", y="Records", color_discrete_sequence=[GREEN])
                    fig.update_traces(line=dict(width=2), fillcolor="rgba(23,100,71,.12)")
                    st.plotly_chart(chart_theme(fig, 330), use_container_width=True)
        with c2:
            with st.container(border=True):
                panel_title("Hazard mix", "Numeric IDs from BIPAD")
                if filtered.empty:
                    st.info("No records match the current filters.")
                else:
                    hazards = filtered["hazard_id"].astype(str).value_counts().head(8).rename_axis("Hazard ID").reset_index(name="Records")
                    fig = px.bar(hazards.sort_values("Records"), x="Records", y="Hazard ID", orientation="h", color_discrete_sequence=[GREEN])
                    st.plotly_chart(chart_theme(fig, 330), use_container_width=True)
        c3, c4 = st.columns([1, 1], gap="medium")
        with c3:
            with st.container(border=True):
                panel_title("Seasonality", "Descriptive share of filtered records")
                if not filtered.empty:
                    order = ["Pre-monsoon", "Monsoon", "Post-monsoon", "Winter"]
                    season = filtered["incident_season"].value_counts().reindex(order, fill_value=0).rename_axis("Season").reset_index(name="Records")
                    fig = px.bar(season, x="Season", y="Records", color_discrete_sequence=[MINT])
                    st.plotly_chart(chart_theme(fig, 280), use_container_width=True)
        with c4:
            with st.container(border=True):
                panel_title("Frequently reporting municipalities", "Record counts, not population-adjusted rates")
                if not filtered.empty:
                    places = filtered.loc[filtered["municipality_name"] != "Not mapped", "municipality_name"].value_counts().head(8).rename_axis("Municipality").reset_index(name="Records")
                    fig = px.bar(places.sort_values("Records"), x="Records", y="Municipality", orientation="h", color_discrete_sequence=["#91b6a1"])
                    st.plotly_chart(chart_theme(fig, 280), use_container_width=True)
        st.download_button("Download filtered records", filtered.to_csv(index=False).encode("utf-8-sig"), "urbanpulse_filtered_incidents.csv", "text/csv")

    elif page == "Nepal map":
        with st.container(border=True):
            panel_title("Incident map", "Pan, zoom, switch layers, and click near a point to inspect nearby reports")
            mode = st.radio("Map layer", ["Density heatmap", "DBSCAN groups", "Incident points"], horizontal=True, label_visibility="collapsed")
            label_file = PROCESSED_ROOT / "dbscan" / SNAPSHOT_ID / "dbscan_labels.csv"
            labels = read_csv(str(label_file)) if label_file.is_file() else None
            label_column = None
            if mode == "DBSCAN groups" and labels is not None:
                labels["id"] = labels["id"].astype("string")
                choices = [column for column in labels.columns if column.startswith("labels_eps")]
                label_column = st.selectbox("DBSCAN setting", choices, index=choices.index("labels_eps1km_min5") if "labels_eps1km_min5" in choices else 0)
            points = filtered.dropna(subset=["latitude", "longitude"]).copy()
            if label_column:
                points = points.merge(labels[["id", label_column]], on="id", how="left")
            folium_map = folium.Map(
                location=[28.25, 84.0],
                zoom_start=6,
                min_zoom=5,
                max_bounds=True,
                tiles=None,
                control_scale=True,
                prefer_canvas=True,
            )
            folium.TileLayer("CartoDB positron", name="Light basemap", control=True, show=True).add_to(folium_map)
            folium.TileLayer("OpenStreetMap", name="Street basemap", control=True, show=False).add_to(folium_map)
            coordinates = points[["latitude", "longitude"]].to_numpy().tolist()
            if mode == "Density heatmap" and coordinates:
                heat_layer = folium.FeatureGroup(name="Incident density", show=True)
                HeatMap(coordinates, radius=13, blur=17, min_opacity=0.22, max_zoom=10).add_to(heat_layer)
                heat_layer.add_to(folium_map)
            elif mode == "DBSCAN groups" and label_column:
                point_layer = folium.FeatureGroup(name="Sampled DBSCAN points", show=True)
                display_points = points.sample(n=min(1800, len(points)), random_state=42) if len(points) else points
                palette = ["#176447", "#287b59", "#65a67d", "#a1c5a4", "#d49e3f", "#bd6b4d", "#4b7994", "#7d6c9b"]
                for _, row in display_points.iterrows():
                    cluster = row[label_column]
                    if pd.isna(cluster):
                        color, cluster_text = "#888f8a", "Not labeled"
                    elif int(cluster) == -1:
                        color, cluster_text = "#9aa19d", "Noise"
                    else:
                        color, cluster_text = palette[int(cluster) % len(palette)], f"Cluster {int(cluster)}"
                    tooltip = f"{row.get('title', 'Incident')} · {cluster_text} · hazard {row.get('hazard_id', 'unknown')}"
                    folium.CircleMarker([row['latitude'], row['longitude']], radius=3, color=color, fill=True, fill_opacity=.72, weight=1, tooltip=tooltip).add_to(point_layer)
                point_layer.add_to(folium_map)
            elif mode == "Incident points" and coordinates:
                display_points = points.sample(n=min(2200, len(points)), random_state=42) if len(points) else points
                marker_layer = MarkerCluster(name="Incident points (sample)", show=True, disableClusteringAtZoom=10)
                for row in display_points.itertuples(index=False):
                    title = row.title if hasattr(row, "title") else "Incident"
                    hazard = row.hazard_id if hasattr(row, "hazard_id") else "unknown"
                    date = row.incidentOn if hasattr(row, "incidentOn") else "date unavailable"
                    popup = folium.Popup(f"<b>{title}</b><br>Hazard ID: {hazard}<br>Date: {date}", max_width=320)
                    folium.Marker([row.latitude, row.longitude], tooltip=str(title), popup=popup).add_to(marker_layer)
                marker_layer.add_to(folium_map)
            folium.LayerControl(collapsed=False).add_to(folium_map)
            if not points.empty:
                folium_map.fit_bounds([[26.0, 80.0], [30.5, 88.5]])
            map_result = st_folium(
                folium_map,
                height=610,
                use_container_width=True,
                returned_objects=["last_clicked"],
                key=f"nepal_map_{mode}_{SNAPSHOT_ID}",
            )
            st.caption(f"Showing {len(points):,} filtered coordinates. Marker layers are sampled for responsiveness; the heatmap uses all filtered points.")
            click = (map_result or {}).get("last_clicked")
            if click and not points.empty:
                lat0, lon0 = click.get("lat"), click.get("lng")
                distance = np.hypot((points["latitude"] - lat0) * 111, (points["longitude"] - lon0) * 98)
                nearby = points.loc[distance.idxmin()]
                with st.expander("Nearest incident to map click", expanded=True):
                    st.write(f"**{nearby.get('title', 'Incident')}** · {nearby.get('municipality_name', 'Unknown municipality')}")
                    st.caption(f"Hazard ID {nearby.get('hazard_id', 'unknown')} · {nearby.get('incidentOn', 'Date unavailable')} · record {nearby.get('id', '')}")
        st.download_button("Download mapped records", points.to_csv(index=False).encode("utf-8-sig"), "urbanpulse_mapped_records.csv", "text/csv")

    elif page == "Trends":
        c1, c2 = st.columns([1.35, 1], gap="medium")
        with c1:
            with st.container(border=True):
                panel_title("Monthly timeline", "Filtered incident records")
                if not filtered.empty:
                    monthly = filtered.assign(month=filtered["incident_datetime"].dt.to_period("M").astype(str)).groupby("month").size().reset_index(name="Records")
                    fig = px.line(monthly, x="month", y="Records", markers=True, color_discrete_sequence=[GREEN])
                    fig.update_traces(line=dict(width=2), marker=dict(size=4))
                    st.plotly_chart(chart_theme(fig, 390), use_container_width=True)
        with c2:
            with st.container(border=True):
                panel_title("Seasonal profile", "Calendar grouping used in notebook 02")
                if not filtered.empty:
                    order = ["Pre-monsoon", "Monsoon", "Post-monsoon", "Winter"]
                    season = filtered["incident_season"].value_counts().reindex(order, fill_value=0).rename_axis("Season").reset_index(name="Records")
                    fig = px.pie(season, names="Season", values="Records", hole=.64, color_discrete_sequence=["#176447", "#5d9c78", "#d4a453", "#9db5a3"])
                    fig.update_traces(textposition="inside", textinfo="percent")
                    fig.update_layout(height=390, margin=dict(l=6, r=6, t=18, b=6), showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)
        with st.container(border=True):
            panel_title("Hazard timeline", "Select hazard IDs in the left rail")
            if not filtered.empty:
                counts = filtered.assign(year=filtered["incident_datetime"].dt.year).groupby(["year", "hazard_id"]).size().reset_index(name="Records")
                top = filtered["hazard_id"].value_counts().head(6).index.astype(str)
                counts = counts[counts["hazard_id"].astype(str).isin(top)]
                fig = px.area(counts, x="year", y="Records", color="hazard_id", line_group="hazard_id", color_discrete_sequence=[GREEN, MINT, "#d3a14a", "#487b8a", "#8a719c", "#c27b5d"])
                fig.update_layout(legend_title_text="Hazard ID")
                st.plotly_chart(chart_theme(fig, 350), use_container_width=True)
        st.caption("Counts are historical reports in this snapshot. Partial years and unverified source coverage limit year-to-year comparisons.")

    elif page == "Municipalities":
        profiles_path = PROCESSED_ROOT / "hierarchical" / SNAPSHOT_ID / "municipality_profiles.csv"
        profiles = read_csv(str(profiles_path)) if profiles_path.is_file() else None
        if profiles is None:
            st.info("Run notebook 04 to build municipality profiles.")
        else:
            profiles["municipality_id"] = profiles["municipality_id"].astype("string")
            filtered_counts = (
                filtered.loc[filtered["municipality_id"].notna()]
                .groupby("municipality_id")
                .size()
                .rename("filtered_incident_count")
            )
            display_profiles = profiles.merge(filtered_counts, on="municipality_id", how="left")
            display_profiles["filtered_incident_count"] = display_profiles["filtered_incident_count"].fillna(0).astype(int)
            with st.container(border=True):
                panel_title("Where reports were recorded", "Municipality counts are not adjusted for population")
                top = display_profiles.sort_values("filtered_incident_count", ascending=False).head(20).sort_values("filtered_incident_count")
                fig = px.bar(top, x="filtered_incident_count", y="municipality_name", orientation="h", color="filtered_incident_count", color_continuous_scale=["#b8d4c0", GREEN])
                fig.update_layout(coloraxis_showscale=False, xaxis_title="Filtered incident records", yaxis_title="")
                st.plotly_chart(chart_theme(fig, 600), use_container_width=True)
            q1, q2 = st.columns([1, 1], gap="medium")
            with q1:
                with st.container(border=True):
                    panel_title("Municipality profile lookup")
                    search = st.text_input("Search by municipality name", placeholder="Start typing…")
                    shown = display_profiles
                    if search:
                        shown = shown[shown["municipality_name"].astype(str).str.contains(search, case=False, na=False)]
                    st.dataframe(shown.sort_values("filtered_incident_count", ascending=False).head(60), use_container_width=True, hide_index=True, height=420)
            with q2:
                with st.container(border=True):
                    panel_title("Clustering quality", "Exploratory results; no robust final grouping was found")
                    diag_path = PROCESSED_ROOT / "hierarchical" / SNAPSHOT_ID / "hierarchical_configuration_comparison.csv"
                    diagnostics = read_csv(str(diag_path)) if diag_path.is_file() else None
                    if diagnostics is not None:
                        fig = px.scatter(diagnostics, x="largest_cluster_size", y="silhouette", color="linkage", size="n_clusters", hover_data=["minimum_incidents", "smallest_cluster_size"], color_discrete_sequence=[GREEN, MINT, GOLD])
                        st.plotly_chart(chart_theme(fig, 300), use_container_width=True)
                        st.caption("High silhouette values came with singleton clusters; they are not a final model endorsement.")
            st.download_button("Download municipality profiles", profiles.to_csv(index=False).encode("utf-8-sig"), "urbanpulse_municipality_profiles.csv", "text/csv")

    elif page == "Anomalies":
        anomaly_path = PROCESSED_ROOT / "isolation_forest" / SNAPSHOT_ID / "municipality_month_anomaly_scores.csv"
        scores = read_csv(str(anomaly_path)) if anomaly_path.is_file() else None
        if scores is None:
            st.info("Run notebook 05 to generate Isolation Forest scores.")
        else:
            label_columns = [column for column in scores if column.endswith("_label")]
            selected_label = st.selectbox("Review threshold", label_columns, index=label_columns.index("iforest_samples512_contam01pct_label") if "iforest_samples512_contam01pct_label" in label_columns else 0)
            score_column = selected_label.replace("_label", "_score")
            candidates = scores.loc[scores[selected_label] == -1].sort_values(score_column)
            st.info(f"{len(candidates):,} candidates at this setting. Anomaly scores rank unusual historical profiles; they are not alerts or forecasts.")
            c1, c2 = st.columns([1.2, 1], gap="medium")
            with c1:
                with st.container(border=True):
                    panel_title("Most isolated municipality-months", "Lower score means more isolated in the fitted feature space")
                    columns = ["municipality_name", "month", "incident_count", "municipality_active_month_median", "count_ratio_to_active_month_median", score_column]
                    st.dataframe(candidates[[column for column in columns if column in candidates]].head(50), use_container_width=True, hide_index=True, height=510)
            with c2:
                with st.container(border=True):
                    panel_title("Score distribution")
                    fig = px.histogram(scores, x=score_column, nbins=40, color_discrete_sequence=[GREEN])
                    fig.add_vline(x=0, line_dash="dash", line_color=GOLD)
                    st.plotly_chart(chart_theme(fig, 320), use_container_width=True)
                    panel_title("High-count candidates")
                    high_count = candidates.sort_values("incident_count", ascending=False).head(12)
                    st.dataframe(high_count[[column for column in columns if column in high_count]], use_container_width=True, hide_index=True, height=300)
            st.download_button("Download candidates", candidates.to_csv(index=False).encode("utf-8-sig"), "urbanpulse_anomaly_candidates.csv", "text/csv")

    elif page == "Model lab":
        comparison_path = ROOT / "reports" / "model_comparison.csv"
        comparison = read_csv(str(comparison_path)) if comparison_path.is_file() else None
        if comparison is None:
            st.info("Run notebook 06 to create the cross-method comparison.")
        else:
            with st.container(border=True):
                panel_title("Method comparison", "Each method solves a different task; metrics are not a shared leaderboard")
                st.dataframe(comparison, use_container_width=True, hide_index=True, height=390)
            c1, c2, c3 = st.columns(3)
            c1.metric("DBSCAN settings", "5", help="Spatial density configurations tested")
            c2.metric("Municipality settings", "24", help="Linkage, cluster count, and count thresholds tested")
            c3.metric("Anomaly settings", "6", help="Isolation Forest subsample and contamination choices")
            st.download_button("Download comparison table", comparison.to_csv(index=False).encode("utf-8-sig"), "urbanpulse_model_comparison.csv", "text/csv")
            st.caption("No supervised forecast model was fitted. No validated prediction target or ground-truth anomaly labels are available in this workflow.")

    else:
        with st.container(border=True):
            panel_title("Dataset provenance")
            cols = st.columns(3)
            cols[0].metric("Retrieved records", f"{quality.get('rows', len(incidents)):,}")
            cols[1].metric("Duplicate IDs", f"{quality_audit.get('duplicate_ids_removed', 'Unknown')}")
            cols[2].metric("Invalid coordinates", f"{quality_audit.get('missing_or_invalid_coordinates', 'Unknown')}")
            st.write("**Source:** BIPAD Portal incident API")
            st.write(f"**Endpoint:** `{quality.get('source_endpoint', 'Not recorded')}`")
            st.write(f"**Retrieved:** `{quality.get('source_retrieved_at_utc', 'Not recorded')}`")
            st.warning(quality.get("coverage_limitation", "Historical source coverage has not been verified."))
            with st.expander("Quality audit", expanded=True):
                st.json(quality_audit)
            manifest_path = DATA_ROOT / "raw" / "bipad_incidents" / SNAPSHOT_ID / "retrieval_manifest.json"
            if manifest_path.is_file():
                with st.expander("Retrieval details"):
                    st.json(read_json(str(manifest_path)))
            temporal_path = PROCESSED_ROOT / "temporal" / SNAPSHOT_ID / "temporal_coverage_report.json"
            if temporal_path.is_file():
                with st.expander("Temporal coverage"):
                    st.json(read_json(str(temporal_path)))
            st.caption("Hazard categories are BIPAD numeric IDs; readable labels have not yet been joined.")

