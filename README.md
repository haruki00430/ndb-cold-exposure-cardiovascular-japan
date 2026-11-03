# ndb-cold-exposure-cardiovascular-japan

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20997810.svg)](https://doi.org/10.5281/zenodo.20997810)
[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

**[Japanese version: README_ja.md](README_ja.md)**

## Overview

This repository contains the analysis code, processed data, and supplementary materials for the following manuscript (under review):

> **Saito H, Ohira T.** "Cold-Season Duration and Cardiovascular Drug Dispensing Across Japanese Prefectures: A Nationwide Ecological Study." *Osong Public Health and Research Perspectives* (revision under review; manuscript ID OPHRP-2026-0484).

> **Important — corrected release (v1.1.0).** Release v1.0.0 and the first submission contained errors (the cold-month threshold was reported as 10 °C but is 5 °C over 60 months; a row-order misalignment made the spatial autocorrelation appear absent). They are documented in [CORRECTIONS.md](CORRECTIONS.md) and corrected in [`revision_R1/`](revision_R1/). Please do not use the results of v1.0.0.

### Key Findings (revised; exploratory and model-dependent)

- **Cold month ratio** = proportion of the 60 months (2016–2020) with mean temperature **< 5 °C** (one Japan Meteorological Agency station per prefecture). Outcome = cardiovascular **tablets** dispensed per resident, fiscal year 2023 (10th NDB Open Data, five drug categories).
- In OLS (HC3), each additional cold month per year was associated with **+6.1 tablets per resident per year** (95% CI 2.0 to 10.2; p = 0.004; adjusted R² = 0.69).
- The OLS residuals were **spatially autocorrelated** (Moran's I = 0.29). The association was not significant in the spatial lag model (coefficient +1.7, p = 0.46; total effect +2.9, 95% interval −6.6 to 9.1) but was in the spatial error model (+5.1, p = 0.041), and it was attenuated after adjustment for smoking.
- The findings are exploratory and do not establish causation.

---

## Data Sources

| Data | Source | Description |
|------|--------|-------------|
| NDB Open Data (10th release, released May 2025) | Ministry of Health, Labour and Welfare, Japan | Prefecture-level CVD prescription counts, FY2023 |
| Climate data (reference period) | Japan Meteorological Agency (JMA) | Monthly mean temperature by prefecture, 2016–2020 |
| Population | Population Estimates, 1 October 2023 (Statistics Bureau) | Denominator and age-sex structure (revision); the initial analysis used the 2020 Census |
| Socioeconomic | Cabinet Office, MIC, MHLW | Income (FY2022), unemployment (Labour Force Survey 2023), aging rate (2023), physicians in medical facilities (2022) |

> **Note**: NDB raw data cannot be redistributed. Please download directly from [MHLW website](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00001.html). JMA climate data are freely available at [JMA website](https://www.jma.go.jp/).

---

## Repository Structure

`revision_R1/` contains the revised analysis (v1.1.0; see [revision_R1/README.md](revision_R1/README.md)). The scripts in `03_Analysis/scripts/` are the **initial analysis**; `07_percapita_reanalysis.py` and the files under `results/` are superseded.

```
ndb-cold-exposure-cardiovascular-japan/
├── README.md                    # This file (English)
├── README_ja.md                 # Japanese version
├── config/
│   └── config.yaml              # Analysis configuration (drug codes, thresholds)
├── 03_Analysis/
│   └── scripts/
│       ├── 00_preprocess_jma_data.py    # JMA CSV preprocessing
│       ├── 01_fetch_weather_data.py     # Climate variable aggregation
│       ├── 02_extract_cvd_data.py       # CVD drug extraction from NDB
│       ├── 03_integrate_data.py         # Data integration
│       ├── 03b_collect_ses_data.py      # SES data collection
│       ├── 04_descriptive_analysis.py   # Descriptive statistics, correlation
│       ├── 05_regression_analysis.py    # OLS regression, model selection
│       ├── 06_spatial_analysis.py       # Moran's I, LISA cluster analysis
│       ├── 07_percapita_reanalysis.py   # Per-capita standardization
│       └── 08_percapita_choropleth.py   # Choropleth map generation
├── 04_Manuscripts/
│   ├── Manuscript_temperature_CVD.qmd   # Quarto source
│   ├── references.bib                   # Bibliography
│   └── submission_package_phrp/         # PHRP submission files
├── data/
│   ├── raw/weather/                     # JMA CSV (not redistributed)
│   └── interim/                         # Processed intermediate data
├── results/
│   └── figures/                         # Generated figures
└── docs/
    └── DATA_SOURCES.md                  # Data source documentation
```

---

## Analysis Pipeline

```
JMA CSV (raw) ──→ 00_preprocess ──→ 01_aggregate ──┐
NDB Excel (raw) ──→ 02_extract ──────────────────────┤
SES data ──→ 03b_collect ──────────────────────────────┤
                                                       ↓
                                            03_integrate → analysis_dataset.csv
                                                       ↓
                              04_descriptive → 05_regression → 06_spatial
                                                       ↓
                              07_percapita_reanalysis → 08_choropleth
                                                       ↓
                                         Manuscript_temperature_CVD.qmd
```

---

## Environment Setup

```bash
# Clone repository
git clone https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan.git
cd ndb-cold-exposure-cardiovascular-japan

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Requirements

- Python 3.11+
- pandas, numpy, scipy
- statsmodels, scikit-learn
- geopandas, PySAL (libpysal, esda, spreg)
- matplotlib, seaborn
- python-docx, quarto (for manuscript rendering)

---

## Reproducing Results

```bash
# Step 1: Preprocess JMA climate data (place JMA CSVs in data/raw/weather/ first)
python 03_Analysis/scripts/00_preprocess_jma_data.py
python 03_Analysis/scripts/01_fetch_weather_data.py

# Step 2: Extract CVD data from NDB (place NDB Excel files in data/raw/ first)
python 03_Analysis/scripts/02_extract_cvd_data.py

# Step 3: Integrate datasets
python 03_Analysis/scripts/03_integrate_data.py
python 03_Analysis/scripts/03b_collect_ses_data.py

# Step 4: Analysis
python 03_Analysis/scripts/04_descriptive_analysis.py
python 03_Analysis/scripts/05_regression_analysis.py
python 03_Analysis/scripts/06_spatial_analysis.py

# Step 5: Per-capita analysis (primary)
python 03_Analysis/scripts/07_percapita_reanalysis.py
python 03_Analysis/scripts/08_percapita_choropleth.py
```

---

## Citation

If you use this code, please cite the archived release (see CITATION.cff; the concept DOI [10.5281/zenodo.20997810](https://doi.org/10.5281/zenodo.20997810) always resolves to the latest version) and the manuscript once published:

```bibtex
@article{saito2026cold,
  title   = {Cold-Season Duration and Cardiovascular Drug Dispensing Across Japanese Prefectures: A Nationwide Ecological Study},
  author  = {Saito, Haruki and Ohira, Tetsuya},
  journal = {Osong Public Health and Research Perspectives},
  year    = {2026},
  note    = {Under review}
}
```

---

## Ethics

This study used only publicly available aggregate data (NDB Open Data) and did not involve individual patient data. Ethics review was not required under the Japanese Ethical Guidelines for Life Science and Medical Research Involving Human Subjects.

---

## License

[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

This repository is licensed under the [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/).

---

## Authors

- **Haruki Saito** (Corresponding Author) — Department of Epidemiology, Fukushima Medical University School of Medicine, Japan — ORCID: [0009-0009-7890-6068](https://orcid.org/0009-0009-7890-6068)
- **Tetsuya Ohira** — Department of Epidemiology, Fukushima Medical University School of Medicine, Japan — ORCID: [0000-0003-4532-7165](https://orcid.org/0000-0003-4532-7165)
