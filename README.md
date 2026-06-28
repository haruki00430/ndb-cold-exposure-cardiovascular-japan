# ndb-cold-exposure-cardiovascular-japan

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

**[Japanese version: README_ja.md](README_ja.md)**

## Overview

This repository contains the analysis code and supplementary materials for the following manuscript:

> **Saito H, Ohira T.** "Association between Cold Month Exposure and Cardiovascular Disease Prescription Rate: A Nationwide Ecological Study in Japan." *Osong Public Health and Research Perspectives* (submitted, June 2026).

### Key Findings

- **Cold month ratio** (proportion of months with mean temperature <10°C) was the strongest predictor of prefectural CVD prescription rates among five temperature indicators (univariable R² = 0.390, *p* < 0.001).
- In multivariable OLS regression (adjusted R² = 0.626), **cold month ratio**, **aging rate**, and **unemployment rate** were independently significant.
- Per-capita CVD prescription rates showed **no significant spatial autocorrelation** (Global Moran's I = 0.091, *p* = 0.114), validating the OLS approach.
- Prefectures with prolonged cold seasons bear a **disproportionate cardiovascular pharmaceutical burden**.

---

## Data Sources

| Data | Source | Description |
|------|--------|-------------|
| NDB Open Data (10th release, released May 2025) | Ministry of Health, Labour and Welfare, Japan | Prefecture-level CVD prescription counts, FY2023 |
| Climate data (reference period) | Japan Meteorological Agency (JMA) | Monthly mean temperature by prefecture, 2016–2020 |
| Population | 2020 National Census (Statistics Bureau) | Population by prefecture for rate standardization |
| Socioeconomic | Cabinet Office, MIC, MHLW | Income, unemployment, aging rate, physician density |

> **Note**: NDB raw data cannot be redistributed. Please download directly from [MHLW website](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00001.html). JMA climate data are freely available at [JMA website](https://www.jma.go.jp/).

---

## Repository Structure

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

If you use this code, please cite:

```bibtex
@article{saito2026cold,
  title   = {Association between Cold Month Exposure and Cardiovascular Disease 
             Prescription Rate: A Nationwide Ecological Study in Japan},
  author  = {Saito, Haruki and Ohira, Tetsuya},
  journal = {Osong Public Health and Research Perspectives},
  year    = {2026},
  note    = {Submitted}
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
