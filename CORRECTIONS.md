# Corrections to the initial analysis (release v1.0.0)

While preparing the revision of the manuscript (Osong Public Health and Research Perspectives), the original analysis scripts and data were re-examined. Several results of the initial analysis (release v1.0.0, and the first submission) were found to be incorrect. They are corrected in release **v1.1.0** (this release). The revised analysis is in [`revision_R1/`](revision_R1/).

| # | Item | Initial analysis (v1.0.0 / first submission) | Correction (v1.1.0) |
|---|------|------|------|
| 1 | Definition of the cold month ratio | Described as the proportion of months with mean temperature **< 10 °C** | The code computed the proportion of the **60 months (January 2016–December 2020)** with mean temperature **< 5 °C** (multiples of 1/60; mean 0.09, maximum 23/60 = 0.38). The threshold was misreported in the README and the manuscript. |
| 2 | Spatial autocorrelation (`03_Analysis/scripts/07_percapita_reanalysis.py`) | Global Moran's I = 0.091 (p = 0.114); "no spatial autocorrelation, validating OLS" | The outcome vector and the spatial weights matrix were ordered differently (row-order misalignment). After alignment, Global Moran's I = **0.555** (p = 0.001) for the initial outcome definition, and the LISA clusters and LM tests change accordingly. The statement that OLS was supported by absent spatial autocorrelation was wrong. Demonstration: `revision_R1/scripts/R5_01_order_bug_demo.py`. |
| 3 | Correlation matrix (manuscript Table 2) | — | 19 of 21 coefficients did not match the data; recalculated from the data. |
| 4 | Covariate sources | Physician density and unemployment rate attributed to the Survey of Physicians, Dentists and Pharmacists and the Labour Force Survey | The values were hospital full-time-equivalent physicians per 100,000 (Survey of Medical Institutions 2020) and the 2020 Census unemployment rate. The revision uses year-aligned covariates re-extracted from the official tables of the stated sources. |
| 5 | Outcome | Sum of quantities in all dosing units, divided by the 2020 Census population | The primary outcome is **tablets only**, per resident (Population Estimates, 1 October 2023); the all-unit sum is a sensitivity analysis. |
| 6 | Exposure selection | Described as pre-specified | The cold month ratio was selected for its fit among five indicators; the selection is not independent of the data. |

## Revised results (exploratory, model-dependent)

- OLS with HC3 standard errors: +6.07 tablets per resident per year per additional cold month per year (95% CI 1.98 to 10.17; p = 0.004; normal approximation; with t-distribution reference values p = 0.006).
- The OLS residuals are spatially autocorrelated (Moran's I = 0.29). Spatial lag model: coefficient +1.65 (p = 0.464); average direct, indirect, and total effects +1.73, +1.12, and +2.85 (total effect 95% interval −6.58 to 9.08). Spatial error model: +5.06 (p = 0.041).
- The association is attenuated after adjustment for smoking and is not found with a 10 °C definition of cold months in fiscal year 2023.

The older files under `results/` and the initial scripts are retained for transparency and are marked as superseded.

## Credentials

An earlier version of two helper scripts (`03b_collect_ses_data.py`, `verify_ses_data.py`) contained an e-Stat application ID. The key has been **revoked** and removed from the scripts (they now read `E_STAT_APP_ID` from the environment). The revoked key remains in earlier commits of this repository and in the archived v1.0.0 snapshot, but it no longer grants access. Do not store credentials in the repository.
