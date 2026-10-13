"""UrbanPulse Nepal exploratory dashboard.

Run from the repository root with:
    streamlit run src/dashboard.py

The dashboard reads saved outputs from notebooks 01–07. It does not download data
or refit models. All model results remain descriptive and are shown with their
coverage and interpretation limits.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
PROCESSED_ROOT = DATA_ROOT / "processed"


def latest_snapshot() -> Path:
    """Return the newest processed incident snapshot directory."""
    root = PROCESSED_ROOT / "bipad_incidents"
    candidates = sorted(
        (p for p in root.iterdir() if (p / "incidents_processed.csv").is_file()),
        key=lambda p: p.name,
    ) if root.exists() else []
    if not candidates:
        raise FileNotFoundError(
            "Processed incidents were not found. Run notebooks 01 and 02 first."
        )
    return candidates[-1]


@st.cache_data(show_spinner="Loading the saved BIPAD analysis…")
def load_csv(path_string: str) -> pd.DataFrame:
    """Load a CSV artifact and cache it for this dashboard session."""
    return pd.read_csv(path_string, low_memory=False)


@st.cache_data(show_spinner=False)
def load_json(path_string: str) -> dict[str, Any]:
    """Load a JSON artifact if available."""
    return json.loads(Path(path_string).read_text(encoding="utf-8"))


def optional_csv(path: Path) -> pd.DataFrame | None:
    return load_csv(str(path)) if path.is_file() else None


def optional_json(path: Path) -> dict[str, Any] | None:
    return load_json(str(path)) if path.is_file() else None


st.set_page_config(
    page_title="UrbanPulse Nepal | Disaster Patterns",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
      .stApp { background: #f5f7f3; }
      [data-testid="stSidebar"] { background: #edf3ed; }
      .hero { padding: 1.25rem 1.5rem; border-radius: 16px; background: #123b2b; color: #f5faf6; margin-bottom: 1rem; }
      .hero h1 { color: #ffffff; margin: 0 0 .3rem 0; font-size: 2rem; }
      .hero p { color: #d7e8dc; margin: 0; }
      .coverage { padding: .8rem 1rem; border-radius: 10px; background: #fff3d8; color: #63480e; border: 1px solid #ead8a7; }
      .section-note { color: #52645a; font-size: .92rem; }
      div[data-testid="stMetric"] { background: white; padding: .8rem; border: 1px solid #e0e8df; border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><h1>UrbanPulse Nepal</h1>'
    '<p>Historical disaster patterns and exploratory analysis from BIPAD Portal incident records</p></div>',
    unsafe_allow_html=True,
)

try:
    SNAPSHOT_DIR = latest_snapshot()
    incidents = load_csv(str(SNAPSHOT_DIR / "incidents_processed.csv"))
except (FileNotFoundError, OSError, pd.errors.ParserError) as exc:
    st.error(f"Could not load the processed incident data: {exc}")
    st.info("Run notebooks 01 and 02, then restart this dashboard.")
    st.stop()

SNAPSHOT_ID = SNAPSHOT_DIR.name
quality = optional_json(SNAPSHOT_DIR / "data_quality_report.json") or {}
quality_audit = quality.get("quality_audit", {})
temporal_dir = PROCESSED_ROOT / "temporal" / SNAPSHOT_ID
dbscan_dir = PROCESSED_ROOT / "dbscan" / SNAPSHOT_ID
hierarchical_dir = PROCESSED_ROOT / "hierarchical" / SNAPSHOT_ID
isolation_dir = PROCESSED_ROOT / "isolation_forest" / SNAPSHOT_ID

if "incidentOn_nepal" in incidents:
    incidents["incident_datetime"] = pd.to_datetime(
        incidents["incidentOn_nepal"], errors="coerce", utc=True
    ).dt.tz_convert("Asia/Kathmandu")
else:
    incidents["incident_datetime"] = pd.NaT

for field in ("latitude", "longitude"):
    if field in incidents:
        incidents[field] = pd.to_numeric(incidents[field], errors="coerce")

st.markdown(
    '<div class="coverage"><strong>Coverage notice:</strong> BIPAD returned an '
    'implausible maximum-integer record count. Pagination ended on an empty page, '
    'so complete historical coverage has not been verified. Counts and patterns '
    'below describe the saved snapshot only.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Explore the snapshot")
    st.caption(f"Snapshot: {SNAPSHOT_ID}")
    valid_dates = incidents["incident_datetime"].dropna()
    if valid_dates.empty:
        start_date, end_date = None, None
        st.warning("No parseable incident dates are available.")
    else:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        selected_dates = st.date_input(
            "Incident date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
        else:
            start_date, end_date = min_date, max_date

    hazard_values = sorted(incidents.get("hazard_id", pd.Series(dtype=str)).dropna().astype(str).unique())
    selected_hazards = st.multiselect(
        "Hazard ID",
        options=hazard_values,
        default=hazard_values,
        help="BIPAD numeric hazard IDs are shown because readable labels were not joined.",
    )
    page = st.radio(
        "Dashboard section",
        ["Overview", "Map & DBSCAN", "Temporal patterns", "Municipalities", "Anomaly review", "Model comparison", "Data quality & sources"],
    )

filtered = incidents.copy()
if start_date is not None and end_date is not None:
    local_dates = filtered["incident_datetime"].dt.date
    filtered = filtered.loc[local_dates.between(start_date, end_date)]
if "hazard_id" in filtered and selected_hazards:
    filtered = filtered.loc[filtered["hazard_id"].astype(str).isin(selected_hazards)]
elif "hazard_id" in filtered and not selected_hazards:
    filtered = filtered.iloc[0:0]

incident_count = len(filtered)
hazard_count = filtered["hazard_id"].nunique() if "hazard_id" in filtered else 0
date_text = "Unavailable"
if not filtered["incident_datetime"].dropna().empty:
    date_text = (
        f"{filtered['incident_datetime'].min():%d %b %Y} – "
        f"{filtered['incident_datetime'].max():%d %b %Y}"
    )


def metric_row() -> None:
    cols = st.columns(4)
    cols[0].metric("Incident records", f"{incident_count:,}")
    cols[1].metric("Hazard IDs", f"{hazard_count:,}")
    cols[2].metric("Municipalities in snapshot", "755")
    cols[3].metric("Date span after filters", date_text)


def top_hazard_chart(data: pd.DataFrame) -> None:
    if "hazard_id" not in data or data.empty:
        st.info("No records match the selected filters.")
        return
    counts = data["hazard_id"].astype(str).value_counts().head(12).rename_axis("Hazard ID").reset_index(name="Records")
    fig = px.bar(counts, x="Hazard ID", y="Records", color_discrete_sequence=["#26845c"])
    fig.update_layout(margin=dict(l=10, r=10, t=25, b=10), height=350)
    st.plotly_chart(fig, use_container_width=True)


if page == "Overview":
    metric_row()
    st.subheader("Snapshot at a glance")
    st.markdown(
        '<p class="section-note">The notebook audit found no missing IDs or incident dates, '
        'and all parsed points fell within the broad Nepal sanity-check bounds. '
        'These checks do not verify historical completeness or exact incident locations.</p>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("#### Incident records by month")
        if not filtered.empty:
            trend = filtered.assign(month=filtered["incident_datetime"].dt.to_period("M").astype(str)).groupby("month").size().reset_index(name="Records")
            fig = px.line(trend, x="month", y="Records", markers=False, color_discrete_sequence=["#247a54"])
            fig.update_layout(height=370, margin=dict(l=5, r=5, t=15, b=5), xaxis_title="Month", yaxis_title="Records")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No records match the selected filters.")
    with right:
        st.markdown("#### Most frequent hazard IDs")
        top_hazard_chart(filtered)
    st.markdown("#### Seasonal distribution")
    if "incident_season" in filtered and not filtered.empty:
        season = filtered["incident_season"].value_counts().rename_axis("Season").reset_index(name="Records")
        fig = px.bar(season, x="Season", y="Records", color_discrete_sequence=["#76a88b"])
        fig.update_layout(height=300, margin=dict(l=5, r=5, t=10, b=5))
        st.plotly_chart(fig, use_container_width=True)
    st.download_button(
        "Download filtered incident records",
        filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"urbanpulse_incidents_{SNAPSHOT_ID}.csv",
        mime="text/csv",
    )

elif page == "Map & DBSCAN":
    metric_row()
    st.subheader("Recorded incident locations")
    st.caption("Map points are historical records in the selected date range. DBSCAN labels represent density groups for one fitted configuration, not future danger zones.")
    label_file = dbscan_dir / "dbscan_labels.csv"
    labels = optional_csv(label_file)
    cluster_choice = None
    map_df = filtered.copy()
    if labels is not None:
        label_options = [c for c in labels.columns if c.startswith("labels_eps")]
        if label_options:
            default_label = "labels_eps1km_min5" if "labels_eps1km_min5" in label_options else label_options[0]
            cluster_choice = st.selectbox("DBSCAN configuration", label_options, index=label_options.index(default_label))
            map_df = map_df.merge(labels[["id", cluster_choice]], on="id", how="left")
            map_df["DBSCAN label"] = map_df[cluster_choice].map(lambda value: "Noise" if value == -1 else f"Cluster {int(value)}" if pd.notna(value) else "Not labeled")
    if {"latitude", "longitude"}.issubset(map_df.columns):
        map_df = map_df.dropna(subset=["latitude", "longitude"])
        display_df = map_df.sample(n=10_000, random_state=42) if len(map_df) > 10_000 else map_df
        color = "DBSCAN label" if "DBSCAN label" in display_df else "hazard_id" if "hazard_id" in display_df else None
        fig = px.scatter_geo(
            display_df,
            lat="latitude",
            lon="longitude",
            color=color,
            hover_name="title" if "title" in display_df else None,
            hover_data=[c for c in ["id", "hazard_id", "incidentOn", "municipality_name"] if c in display_df],
            projection="mercator",
            opacity=0.65,
            title=f"Incident points (displaying {len(display_df):,} of {len(map_df):,})",
        )
        fig.update_geos(lonaxis_range=[80, 89], lataxis_range=[26, 31], showland=True, landcolor="#eff3ec", showcountries=True)
        fig.update_layout(height=650, margin=dict(l=0, r=0, t=45, b=0), legend_title_text="DBSCAN / hazard")
        st.plotly_chart(fig, use_container_width=True)
        if len(map_df) > len(display_df):
            st.caption("The map is deterministically sampled for display; the downloadable records remain un-sampled.")
    else:
        st.warning("Latitude and longitude fields were not found in the processed dataset.")
    if labels is not None and cluster_choice:
        counts = labels[cluster_choice].value_counts().rename_axis("DBSCAN label").reset_index(name="Records")
        st.markdown("#### Cluster and noise counts for the selected configuration")
        st.dataframe(counts, use_container_width=True, hide_index=True)

elif page == "Temporal patterns":
    metric_row()
    st.subheader("Historical timing")
    if not filtered.empty:
        annual = filtered.assign(year=filtered["incident_datetime"].dt.year).groupby("year").size().reset_index(name="Records")
        monthly = filtered.assign(month=filtered["incident_datetime"].dt.to_period("M").astype(str)).groupby("month").size().reset_index(name="Records")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### By year")
            fig = px.bar(annual, x="year", y="Records", color_discrete_sequence=["#25845b"])
            fig.update_layout(height=380, xaxis_title="Year", margin=dict(l=5, r=5, t=10, b=5))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### By month")
            fig = px.line(monthly, x="month", y="Records", color_discrete_sequence=["#314d3c"])
            fig.update_layout(height=380, xaxis_title="Month", margin=dict(l=5, r=5, t=10, b=5))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Seasonal totals")
        top_hazard_chart(filtered)
        if "incident_season" in filtered:
            st.dataframe(filtered["incident_season"].value_counts().rename_axis("Season").reset_index(name="Records"), use_container_width=True, hide_index=True)
        st.download_button("Download filtered monthly series", monthly.to_csv(index=False).encode("utf-8-sig"), file_name="filtered_monthly_counts.csv", mime="text/csv")
    else:
        st.info("No records match the selected filters.")

elif page == "Municipalities":
    metric_row()
    st.subheader("Municipality incident profiles")
    profiles = optional_csv(hierarchical_dir / "municipality_profiles.csv")
    comparison = optional_csv(hierarchical_dir / "hierarchical_configuration_comparison.csv")
    if profiles is None:
        st.info("Run notebook 04 to generate municipality profiles.")
    else:
        st.warning("The hierarchical comparison did not establish a robust final municipality segmentation. Profiles are descriptive counts and proportions, not population-adjusted risk.")
        search = st.text_input("Search municipality")
        show = profiles
        if search:
            show = show[show["municipality_name"].astype(str).str.contains(search, case=False, na=False)]
        sort_by = "incident_count" if "incident_count" in show else show.columns[0]
        st.dataframe(show.sort_values(sort_by, ascending=False).head(100), use_container_width=True, hide_index=True)
        if comparison is not None:
            st.markdown("#### Hierarchical configuration diagnostics")
            st.dataframe(comparison.sort_values("silhouette", ascending=False), use_container_width=True, hide_index=True)
        st.download_button("Download displayed municipality profiles", show.to_csv(index=False).encode("utf-8-sig"), file_name="municipality_profiles.csv", mime="text/csv")

elif page == "Anomaly review":
    metric_row()
    st.subheader("Unusual municipality-month candidates")
    scores = optional_csv(isolation_dir / "municipality_month_anomaly_scores.csv")
    if scores is None:
        st.info("Run notebook 05 to generate Isolation Forest scores.")
    else:
        label_col = "iforest_samples512_contam01pct_label"
        score_col = "iforest_samples512_contam01pct_score"
        if label_col not in scores or score_col not in scores:
            st.warning("Expected Isolation Forest configuration columns were not found.")
        else:
            candidates = scores.loc[scores[label_col] == -1].sort_values(score_col)
            st.warning(f"{len(candidates):,} records are candidates under the 1% contamination setting. Candidates are not validated anomalies or forecasts.")
            st.dataframe(candidates[[c for c in ["municipality_name", "municipality_id", "month", "incident_count", "municipality_active_month_median", "count_ratio_to_active_month_median", score_col] if c in candidates]].head(100), use_container_width=True, hide_index=True)
            st.download_button("Download anomaly candidates", candidates.to_csv(index=False).encode("utf-8-sig"), file_name="anomaly_candidates.csv", mime="text/csv")

elif page == "Model comparison":
    metric_row()
    st.subheader("Exploratory model diagnostics")
    st.caption("DBSCAN silhouette, hierarchical silhouette, and Isolation Forest contamination rates measure different things. They are not a common leaderboard.")
    report = optional_csv(ROOT / "reports" / "model_comparison.csv")
    if report is None:
        st.info("Run notebook 06 to generate the cross-method comparison table.")
    else:
        st.dataframe(report, use_container_width=True, hide_index=True)
        st.download_button("Download model comparison", report.to_csv(index=False).encode("utf-8-sig"), file_name="model_comparison.csv", mime="text/csv")

else:
    st.subheader("Data quality and sources")
    st.write(f"**Incident endpoint:** `{quality.get('source_endpoint', 'Not recorded')}`")
    st.write(f"**Retrieved at (UTC):** `{quality.get('source_retrieved_at_utc', 'Not recorded')}`")
    st.write(f"**Records in processed snapshot:** {quality.get('rows', len(incidents)):,}")
    st.write(f"**Pagination complete:** {quality_audit.get('pagination_complete', 'Unknown')}")
    st.write(f"**API-reported count:** {quality_audit.get('api_reported_total', 'Not recorded')}")
    st.write(f"**Coverage limitation:** {quality.get('coverage_limitation', 'See retrieval manifest.')}")
    st.markdown("#### Quality checks")
    st.json(quality_audit)
    manifest_path = DATA_ROOT / "raw" / "bipad_incidents" / SNAPSHOT_ID / "retrieval_manifest.json"
    manifest = optional_json(manifest_path)
    if manifest:
        with st.expander("Retrieval manifest"):
            st.json(manifest)
    st.markdown("#### Temporal coverage")
    temporal_report = optional_json(temporal_dir / "temporal_coverage_report.json")
    if temporal_report:
        st.json(temporal_report)
    st.caption("Source: BIPAD Portal API. Hazard values remain numeric IDs unless verified labels are joined in a future data-preparation step.")

