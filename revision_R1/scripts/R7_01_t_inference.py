# -*- coding: utf-8 -*-
"""
R7_01: 主モデル（OLS, HC3）の推論を、報告値（正規近似）と t 分布（自由度 = n − 説明変数の数 − 1 = 42）で比較する小標本感度分析。
報告値（R2_01）は statsmodels の既定（cov_type="HC3"、正規近似）。ここでは use_t=True を指定した場合の寒冷月比率（1か月/年あたり）の p 値と95%CIのみを出力。
結果は results/R7_t_results.json（既存なら停止）。都道府県別の数値は出力しない。
"""
import sys, json
from pathlib import Path
import pandas as pd, statsmodels.api as sm
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

R1 = P.R1; OUT = R1 / "results" / "R7_t_results.json"
if OUT.exists(): raise SystemExit(f"既存のため停止: {OUT}")
df = pd.read_csv(R1 / "data" / "analysis_dataset_R2.csv", encoding="utf-8")
df["y"] = df.qty_tablet / df.population_2023; df["x"] = df.orig_Cold_months_ratio
COV = ["aging_pct_2023", "physicians_per100k_2022", "unemployment_pct_2023", "income_10000yen_FY2022"]
X = sm.add_constant(df[["x"] + COV])
res = {}
for name, ut in (("normal", False), ("t", True)):
    m = sm.OLS(df.y, X).fit(cov_type="HC3", use_t=ut); ci = m.conf_int().loc["x"] / 12
    res[name] = dict(per_month=float(m.params["x"] / 12), ci_lo=float(ci[0]), ci_hi=float(ci[1]), p=float(m.pvalues["x"]),
                     p_aging=float(m.pvalues["aging_pct_2023"]), df_resid=float(m.df_resid))
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in res.items(): print(k, {a: round(b, 6) for a, b in v.items()})
