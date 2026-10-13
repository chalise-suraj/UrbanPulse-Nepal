<div align="center">

# UrbanPulse Nepal

### Exploring historical disaster reports with data analysis and machine learning

![Project status: exploratory](https://img.shields.io/badge/status-exploratory-2f6f4e)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB)
![Dashboard: Streamlit](https://img.shields.io/badge/dashboard-Streamlit-FF4B4B)
![Source: BIPAD](https://img.shields.io/badge/source-BIPAD-176447)

UrbanPulse turns a saved set of BIPAD incident records into an interactive workspace for exploring historical patterns across Nepal. It combines temporal summaries, spatial density clustering, municipality profile comparisons, and anomaly review. It is an exploratory analysis tool, not a disaster forecasting or official risk assessment system.

</div>

## Contents

- [At a glance](#at-a-glance)
- [Problem and research questions](#problem-and-research-questions)
- [Data source and coverage](#data-source-and-coverage)
- [Analysis workflow](#analysis-workflow)
- [Methods and observed results](#methods-and-observed-results)
- [Dashboard guide](#dashboard-guide)
- [Installation and use](#installation-and-use)
- [Repository layout](#repository-layout)
- [Reproducibility](#reproducibility)
- [Limitations and responsible use](#limitations-and-responsible-use)
- [Future improvements](#future-improvements)

## At a glance

| Item | Current saved analysis |
|---|---|
| Source | [BIPAD Portal API](https://bipadportal.gov.np/api/) incident endpoint |
| Retrieved incident records | 64,735 |
| Incident date span in the retrieved records | 14 Apr 2011 – 13 Oct 2026 |
| Hazard categories | 20 |
| Municipalities represented by mapped reports | 755 |
| Duplicate IDs removed during preprocessing | 0 |
| Missing or invalid coordinates in the processed snapshot | 0 |
| Methods | Haversine DBSCAN, agglomerative municipality clustering, Isolation Forest |
| Forecast model | None; no validated target or forecasting evaluation is available |
| Saved analysis snapshot | `20261013T101245Z` |

The record count and quality figures describe this saved retrieval. They do not establish that BIPAD's historical archive is complete.

## Problem and research questions

Disaster records are useful for understanding what has been reported, where records are concentrated, and how recorded activity varies over time. A dashboard can make those patterns easier to explore, but it must distinguish observed reports from estimates of underlying risk.

This project investigates:

1. Where do the retrieved incident coordinates form dense spatial groups, and how sensitive are those groups to DBSCAN settings?
2. Do municipalities separate into interpretable groups based on their recorded hazard and seasonal profiles?
3. Which municipality-month activity profiles look unusual enough to review against the source records?
4. How do the retrieved report counts vary by month, year, season, and hazard?

The contribution is a reproducible, side-by-side exploration of complementary analytical tasks, with parameter comparisons and limitations shown alongside results. A dense historical cluster is not treated as a future danger zone, and an anomaly score is not treated as an alert.

## Data source and coverage

### Sources

- **Incident records:** [`https://bipadportal.gov.np/api/v1/incident/`](https://bipadportal.gov.np/api/v1/incident/)
- **API documentation:** [BIPAD API](https://bipadportal.gov.np/api/)
- **Hazard labels:** BIPAD's public hazard reference records; the dashboard maps retained hazard IDs to readable English names.
- **Administrative lookup:** BIPAD municipality and ward lookup records used to connect ward IDs to municipalities. The retrieval manifest is in [`data/raw/bipad_admin_lookup/20261013T103410Z/lookup_manifest.json`](data/raw/bipad_admin_lookup/20261013T103410Z/lookup_manifest.json).

The incident retrieval saved paginated responses, a combined raw export, retrieval parameters, and a manifest. Preprocessed records and analysis outputs are stored separately under `data/processed/`.

### Coverage and data-quality findings

The acquisition notebook retrieved 64,735 records and stopped after an empty response on page 66. The API's reported total was `9223372036854775807`, an implausible sentinel rather than a usable total. The manifest therefore records pagination as **incomplete/unverified**. A successful page response or an empty final page is not proof that the source archive was fully retrieved.

Within the retrieved snapshot, the audit found no duplicate IDs, missing IDs, missing or invalid coordinates, coordinates outside the broad Nepal bounds used for the check, or missing/unparseable incident dates. Parsed incident dates range from 14 Apr 2011 to 13 Oct 2026 in Nepal time. These checks describe the saved records only; they do not detect every possible source error or reporting gap.

See the full [data-quality report](data/processed/bipad_incidents/20261013T101245Z/data_quality_report.json), [retrieval manifest](data/raw/bipad_incidents/20261013T101245Z/retrieval_manifest.json), and [temporal coverage report](data/processed/temporal/20261013T101245Z/temporal_coverage_report.json).

## Analysis workflow

Run the notebooks in order. Each notebook contains its findings with the corresponding analysis.

| Order | Notebook | Purpose and main output |
|---:|---|---|
| 1 | [BIPAD data acquisition](notebooks/01_bipad_data_acquisition.ipynb) | Fetch paginated incident and administrative lookup data; save raw responses and retrieval manifests. |
| 2 | [Data audit and preprocessing](notebooks/02_data_audit_and_preprocessing.ipynb) | Validate IDs, dates, coordinates, and fields; join municipality information; save processed records, a field dictionary, and quality report. |
| 3 | [DBSCAN spatial clusters](notebooks/03_dbscan_spatial_clusters.ipynb) | Compare Haversine distance settings; save incident cluster labels and configuration metrics. |
| 4 | [Municipality hierarchical clustering](notebooks/04_municipality_hierarchical_clustering.ipynb) | Build municipality hazard/season profiles and compare agglomerative configurations. |
| 5 | [Isolation Forest activity anomalies](notebooks/05_isolation_forest_activity_anomalies.ipynb) | Score municipality-month profiles under multiple settings; save scores and candidates for review. |
| 6 | [Cross-method model comparison](notebooks/06_cross_method_model_comparison.ipynb) | Summarize the methods, their measured results, and their task-specific limitations. |
| 7 | [Temporal pattern analysis](notebooks/07_temporal_pattern_analysis.ipynb) | Summarize annual, monthly, seasonal, and hazard counts and temporal coverage. |

### Feature definitions

- Incident timestamps are parsed in Nepal time (`Asia/Kathmandu`).
- Latitude and longitude are extracted from the source geographic point coordinates and checked against broad Nepal bounds (latitude 26–31, longitude 80–89).
- Seasons are derived from incident month: Winter (Dec–Feb), Pre-monsoon (Mar–May), Monsoon (Jun–Sep), and Post-monsoon (Oct–Nov).
- Municipality profiles aggregate recorded hazard and seasonal activity at a consistent municipality level. Source identifiers are retained for traceability and are not used as numeric model features.
- Isolation Forest features describe historical municipality-month activity. Candidate scores are ranks for review, not labels of confirmed abnormal events.

## Methods and observed results

The project keeps three methods because they address different questions. The saved comparison is available as [`reports/model_comparison.csv`](reports/model_comparison.csv), with a summary in [`reports/model_comparison_summary.json`](reports/model_comparison_summary.json).

| Method | Example measured configuration | Observed result | Interpretation |
|---|---|---|---|
| **DBSCAN** — spatial density and noise among incident locations | Haversine distance, `eps=1 km`, `min_samples=10` | 1,019 clusters; 32.49% noise; largest cluster 1,244; sampled clustered-point silhouette 0.779 | Many small clusters. The silhouette is sample-based and excludes noise, so it is not evidence of future risk or a universally best setting. |
| **DBSCAN sensitivity** | `eps=5 km`, `min_samples=5` | 298 clusters; 0.99% noise; largest cluster 38,428; sampled silhouette -0.528 | The broad radius over-merges records into a very large group. This illustrates why noise rate alone is not a selection criterion. |
| **Agglomerative clustering** — municipality hazard/season profiles | Average linkage, `k=3`, minimum 10 incidents | 726 municipalities; cluster sizes include 724 and 1; silhouette 0.772 | The high score accompanies an extremely imbalanced partition with a singleton, so it is not a useful final segmentation. |
| **Agglomerative comparison** | Ward linkage, `k=3`, minimum 20 incidents | 610 municipalities; cluster sizes 10–314; silhouette 0.097 | The groups are more balanced, but separation is weak. No robust municipality grouping is selected. |
| **Isolation Forest** — unusual municipality-month profiles | `max_samples=512`, `contamination=1%` | 283 of 28,202 active-month profiles flagged as candidates (1.00%) | Candidates require manual review; there are no ground-truth anomaly labels for precision or recall. |
| **Isolation Forest sensitivity** | `max_samples=512`, `contamination=3%` | 847 of 28,202 profiles flagged (3.00%) | The candidate rate follows the chosen contamination setting; it is not a measured anomaly prevalence. |

No single model is selected as a winner. The methods remain complementary exploratory analyses. No supervised disaster forecast has been fitted, and no predictive accuracy claim is made.

## Dashboard guide

Launch [`dashboard.py`](dashboard.py) from the repository root. The sidebar filters the saved records by incident date, hazard type, and municipality.

| Section | What it shows |
|---|---|
| **Overview** | Dataset counts plus monthly, hazard, seasonal, and municipality report-count charts. |
| **Nepal map** | A historical density heatmap, sampled incident points, or saved DBSCAN labels. The map supports pan, zoom, and layer controls. |
| **Trends** | Monthly and seasonal patterns and a hazard timeline for the filtered records. |
| **Municipalities** | Filtered report counts, municipality profile lookup, and exploratory clustering diagnostics. |
| **Anomalies** | Isolation Forest candidate rows and score distributions for the selected threshold. |
| **Model lab** | The saved cross-method comparison table. |
| **Data quality** | Retrieval provenance, audit results, and coverage limitations. |

Charts show counts from the retrieved BIPAD snapshot. Municipality counts are not population-adjusted. Point-marker layers are sampled for responsiveness; the density layer uses all filtered coordinates. Map tiles come from OpenStreetMap and require network access.

## Installation and use

Python 3.10 or newer is recommended.

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Open and run the notebooks

```bash
jupyter lab
```

Open `notebooks/` and run notebooks 01–07 in numerical order. Notebook 01 makes requests to BIPAD; the remaining notebooks use saved raw or processed files and write versioned artifacts under `data/` and `reports/`. Re-running acquisition can create a new saved snapshot. Preserve the run's manifests and inspect pagination status before interpreting results.

### Launch the dashboard

```bash
streamlit run dashboard.py
```

The dashboard loads the latest processed incident artifact under `data/processed/bipad_incidents/` and related outputs for that snapshot. It does not fetch data or fit models when it starts. To use a new retrieval, complete the acquisition and analysis notebooks first.

## Repository layout

```text
.
├── dashboard.py
├── requirements.txt
├── configs/
│   └── config.yaml
├── notebooks/
│   ├── 01_bipad_data_acquisition.ipynb
│   ├── 02_data_audit_and_preprocessing.ipynb
│   ├── 03_dbscan_spatial_clusters.ipynb
│   ├── 04_municipality_hierarchical_clustering.ipynb
│   ├── 05_isolation_forest_activity_anomalies.ipynb
│   ├── 06_cross_method_model_comparison.ipynb
│   └── 07_temporal_pattern_analysis.ipynb
├── data/
│   ├── raw/          # Saved API pages, exports, and retrieval manifests
│   └── processed/   # Audited data, features, labels, scores, and summaries
├── reports/
│   ├── model_comparison.csv
│   └── model_comparison_summary.json
└── .streamlit/
    └── config.toml
```

## Reproducibility

- The saved incident retrieval is identified by `20261013T101245Z`; administrative lookups use `20261013T103410Z`.
- Raw page responses, combined exports, and retrieval manifests are retained under `data/raw/`.
- Processed records, feature definitions, model labels/scores, and quality reports are retained under `data/processed/`.
- Model configurations and interpretation notes are saved in the comparison CSV and JSON summary.
- The API's reported total is not used as the retrieved record count because it is an invalid sentinel.
- Notebook results should be interpreted together with each notebook's final findings and the coverage report.

## Limitations and responsible use

- **Unverified archive completeness:** the BIPAD API returned an implausible total. The retrieved 64,735 records may be a partial archive.
- **Reporting bias:** counts depend on reporting, data entry, and source coverage. They are not equivalent to the true incidence or severity of disasters.
- **No forecasts:** the workflow has no validated prediction target, prospective evaluation, or supervised forecast model.
- **Exploratory clusters:** DBSCAN results depend on distance and density settings. Municipality partitions were either highly imbalanced or weakly separated.
- **Unvalidated anomalies:** Isolation Forest has no ground-truth labels here. Scores identify records to investigate; they do not establish errors, exceptional disasters, or imminent events.
- **Raw counts:** municipality counts are not adjusted for population, exposure, reporting access, or time-varying data completeness.
- **Map sampling:** incident markers and DBSCAN points are sampled to keep the interactive map responsive; the heatmap uses all filtered coordinates.
- **Temporal gaps:** a month with no retrieved records is not proof that no disaster occurred. The last observed year is partial.

Do not use this application alone for emergency response, resource allocation, public warnings, or official risk decisions. Review source records and consult authoritative disaster-management information for operational decisions.

## Future improvements

- Verify source coverage with BIPAD maintainers or an independently validated archive and document repeatable refresh behavior.
- Add source-documented administrative boundaries for clearer district and municipality comparisons.
- Evaluate spatial-cluster stability and municipality profile quality across time windows and preprocessing choices.
- Review anomaly candidates with domain experts and create validated labels before reporting classification metrics.
- Consider forecasting only if a defensible target, aligned predictor data, and leakage-safe temporal evaluation become available.
- Add automated checks for the acquisition, preprocessing, model-output, and dashboard data contracts.
