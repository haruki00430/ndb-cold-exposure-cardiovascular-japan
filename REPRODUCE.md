# Reproduction Guide / 再現手順書

**Project:** `ndb-cold-exposure-cardiovascular-japan`  
**Manuscript:** *Association between Cold Month Exposure and Cardiovascular Disease Prescription Rate: A Nationwide Ecological Study in Japan*  
**Repository:** https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan  
**Archive DOI:** `10.5281/zenodo.20997811`.

This guide describes how to reproduce the **prefecture-level aggregated analysis (N = 47)** reported in the manuscript.  
本書は論文に報告した **47都道府県の集計解析** を再現する手順です。

---

## What this repository includes / 含むもの・含まないもの

| Included / 含むもの | Not included / 含まないもの |
|---------------------|----------------------------|
| Analysis scripts (`03_Analysis/scripts/`) | NDB raw Excel (download from MHLW portal) |
| Config template (`config/config.yaml`) | JMA raw climate CSV (download manually) |
| `REPRODUCE.md`, `DATA_SOURCES.md` | Individual-level claims data |
| Key result summaries under `results/` | Files > 100 MB (GitHub limit) |

Under MHLW terms of use, **NDB raw data cannot be redistributed**. All raw inputs must be downloaded independently (see `DATA_SOURCES.md`).  
NDB生データは厚生労働省利用規約により再配布できません。生データは各自ダウンロードしてください（`DATA_SOURCES.md` 参照）。

---

## System requirements / システム要件

| Item | Requirement |
|------|-------------|
| Python | 3.14 (tested on Windows 11) |
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ |
| RAM | 8 GB minimum |
| Disk | ~3 GB for NDB Excel + interim files |

---

## Step 0: Clone and environment setup / 環境構築

```bash
git clone https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan.git
cd ndb-cold-exposure-cardiovascular-japan

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### Path configuration / パス設定

Edit `config/config.yaml` to point to your local data paths:

```yaml
# config/config.yaml — adjust raw data paths for your environment
ndb_data_path: "path/to/NDB_OpenData/No.10/"
jma_weather_path: "data/raw/weather/"
```

---

## Pipeline overview / 解析パイプライン概要

```
[Raw data download]
  JMA climate CSV  +  NDB Open Data Excel  +  Census / SES data
        ↓
00_preprocess_jma_data.py   → data/interim/weather_monthly_long.csv
01_fetch_weather_data.py    → data/interim/weather_data_prefecture.csv
02_extract_cvd_data.py      → data/interim/cvd_prescription.csv
03_integrate_data.py        → data/interim/analysis_dataset.csv
03b_collect_ses_data.py     → data/interim/ses_data.csv
        ↓
04_descriptive_analysis.py  → results/descriptive_statistics.md
05_regression_analysis.py   → results/regression_analysis.md
06_spatial_analysis.py      → results/spatial_analysis.md
07_percapita_reanalysis.py  → results/percapita_reanalysis.md
08_percapita_choropleth.py  → results/figures/Figure1_choropleth_cvd_percapita.png
```

---

## Step 1: Download raw data / 生データのダウンロード

Follow `DATA_SOURCES.md` for official download URLs and file placement.  
生データのダウンロードURLとファイル配置は `DATA_SOURCES.md` を参照してください。

**Summary:**

1. **NDB Open Data (10th release, FY2023)** — MHLW portal → `data/raw/NDB_OpenData/No.10/`
2. **JMA climate data (2016–2020)** — JMA Customized Tables → `data/raw/weather/`
3. **2020 National Census** — e-Stat → `data/raw/census/`
4. **Socioeconomic variables** — Cabinet Office, MIC → `data/raw/ses_data/`

---

## Step 2: Run analysis pipeline / 解析スクリプト実行

Run scripts in numbered order from the repository root:

```bash
cd 03_Analysis/scripts

python 00_preprocess_jma_data.py
python 01_fetch_weather_data.py
python 02_extract_cvd_data.py
python 03_integrate_data.py
python 03b_collect_ses_data.py
python 04_descriptive_analysis.py
python 05_regression_analysis.py
python 06_spatial_analysis.py
python 07_percapita_reanalysis.py
python 08_percapita_choropleth.py
```

**Expected key outputs:**

| File | Description |
|------|-------------|
| `results/regression_analysis.md` | OLS regression results, VIF, sensitivity analyses |
| `results/spatial_analysis.md` | Global Moran's I, LISA clusters |
| `results/figures/Figure1_choropleth_cvd_percapita.png` | Figure 1 (500 DPI) |
| `results/figures/Figure2_residual_diagnostics.png` | Figure 2 (500 DPI) |

**Headline results to verify against manuscript:**

| Quantity | Expected value |
|----------|---------------|
| N prefectures | 47 |
| Cold month ratio β (univariable R²) | 0.390 |
| Multivariable adjusted R² | 0.626 |
| Global Moran's I (per-capita CVD rate) | 0.091 (*p* = 0.114) |

---

## Troubleshooting / トラブルシュート

| Issue | Action |
|-------|--------|
| `ModuleNotFoundError: ndb_library` | Add `../../src/` to `PYTHONPATH` or install as editable package |
| Encoding error on Windows | Scripts use UTF-8; run `chcp 65001` or use Python 3.14 |
| `*.csv` not tracked by git | Only `data/interim/` outputs are expected; raw data is excluded by `.gitignore` |
| JMA download format changed | Use the "Customized Tables" interface at https://www.data.jma.go.jp/risk/obsdl/ |

---

## Citation / 引用

If you use this repository, please cite:

- **Code/data archive:** Saito H, Ohira T. *ndb-cold-exposure-cardiovascular-japan* (v1.0.0). Zenodo. https://doi.org/10.5281/zenodo.20997811
- **Original paper:** Saito H, Ohira T. Association between Cold Month Exposure and Cardiovascular Disease Prescription Rate: A Nationwide Ecological Study in Japan. *Osong Public Health and Research Perspectives.* 2026. (under review)

See also `CITATION.cff` for machine-readable citation metadata.

---

## Document map / 関連ドキュメント

| File | Purpose |
|------|---------|
| `DATA_SOURCES.md` | Official download URLs and file names / 公式データダウンロード手順 |
| `CITATION.cff` | Machine-readable citation metadata |
| `requirements.txt` | Python package dependencies |
| `config/config.yaml` | Analysis configuration and local paths |
| `03_Analysis/scripts/` | All analysis scripts (numbered 00–08) |
| `results/` | Key result outputs (markdown summaries + figures) |

**Last updated:** 2026-06-28
