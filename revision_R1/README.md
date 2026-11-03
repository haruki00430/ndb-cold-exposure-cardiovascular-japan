# revision_R1 — revised analysis (v1.1.0)

Analysis code, processed data, and results for the revised manuscript *Cold-Season Duration and Cardiovascular Drug Dispensing Across Japanese Prefectures: A Nationwide Ecological Study* (under review). See [../CORRECTIONS.md](../CORRECTIONS.md) for the corrections to the initial analysis.

## Contents

| Folder / file | Content |
|---|---|
| `R2_Analysis_Specification.md` | Specification of the primary analysis, written before the revised analysis was run (not a preregistration; the primary exposure was chosen with knowledge of the initial analysis). |
| `R2_Analysis_Specification_Amendments.md` | Analyses added after the primary analysis (indirect standardization, extra-covariate re-extraction, spatial-model reporting, SLM effects). |
| `scripts/` | Analysis scripts (see below). `paths.py` collects all paths (no absolute paths). |
| `data/` | Processed prefecture-level data (N = 47): analysis dataset, national age-sex quantities, 2023 population by age and sex, prefecture centroids, standardized outcome. |
| `results/`, `outputs/` | Model results (JSON/CSV) and script logs (aggregate values only). |
| `supplement/`, `figures/` | Supplementary Table S1 (Excel/CSV) and Figures 1–3 (JPG, 500 dpi). |

## Not included

- **Raw inputs** (NDB Open Data Excel files, official statistical tables, original-project files): download from the sources listed in `../DATA_SOURCES.md`, `../docs/DATA_SOURCES.md` and the manuscript, and place them under `data/inputs/` as expected by `scripts/paths.py`. `R2_00_build_dataset.py` and the extraction scripts need them.
- **Prefecture boundary data** (`prefecture_geometry.gpkg`): not redistributed; `R2_02_figures.py` (maps) needs boundary data.
- **Credentials**: the e-Stat application ID must be set in the environment variable `E_STAT_APP_ID` (see `R3_01_fetch_population_age_sex.py`); never write it into files.
- An exploratory conversion to defined daily doses was performed but is not reported (the correspondence between products and WHO DDD values could not be independently verified), so its files are not included.

## Order of the scripts

```
R2_00_build_dataset.py            # dataset construction + comparison with official tables (needs data/inputs)
R2_01_analysis.py                 # primary analysis, spatial analysis, sensitivity analyses (data/analysis_dataset_R2.csv)
R3_00 / R3_02                     # national age-sex quantities; indirect age-sex standardization
R6_00_verify_extra_covariates.py  # re-extraction of smoking/BMI/blood pressure/sodium from official tables (PyMuPDF)
R7_01_t_inference.py              # t-distribution check of the primary OLS inference
R7_00_slm_effects.py              # SLM direct, indirect, and total effects (simulation intervals)
R5_01_order_bug_demo.py           # demonstration of the row-order misalignment of the initial analysis
```

`R2_01` and the `R7` scripts stop if their output file exists (they never overwrite); run them in a copy with empty `results/`. Python ≥ 3.12 with pandas, numpy (≤ 2.3 with numba-based libpysal), scipy, statsmodels, libpysal, esda, spreg, geopandas. Verified from the included processed data alone: `R2_01`, `R3_02`, `R7_00`, and `R7_01` regenerate the result JSON files identically. The complete chain (including `R2_00`, `R3_00`, `R6_00`, and the figures) was verified in a full package that also contained the raw inputs.

All random seeds are fixed (permutation tests and simulations use seed 20261102).
