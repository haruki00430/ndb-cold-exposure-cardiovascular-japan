# -*- coding: utf-8 -*-
"""
R3_02: 間接法による年齢・性別標準化アウトカムの作成と主解析の再実行。
  期待値 E_j = Σ_{性,年齢} 全国の錠数量率(性,年齢) × 県jの人口(性,年齢)
  標準化比 SMR_j = O_j / E_j（O_j=県jの錠数量）
  標準化アウトカム y_std_j = SMR_j × 全国の1人あたり錠数量
全国率の分子=NDB性年齢別表（錠・5薬効分類）、分母=人口推計2023（e-Stat 0004012968, 全国）。85歳以上は統合。
都道府県別の実数は print しない。仕様: R2_Analysis_Specification.md の主解析と同一（共変量は年次整合）。追加として「高齢化率を除く」版を報告。
"""
import sys, json, pickle, warnings
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy import stats
import geopandas as gpd
from libpysal.weights import KNN
from esda.moran import Moran
import spreg.output as _o, spreg.ml_error as _me, spreg.ml_lag as _ml
for _mod in (_o, _me, _ml):
    for _nm in ("_nonspat_top", "_nonspat_mid", "_spat_top", "_spat_mid", "_summary_chow", "_summary_vif"):
        if hasattr(_mod, _nm): setattr(_mod, _nm, lambda *a, **k: "")
from spreg import OLS as spOLS, ML_Lag, ML_Error
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P

PROJ = P.PROJ
R1 = P.R1
SEED = 20261102
JSON_OUT = R1 / "results" / "R3_results.json"
if JSON_OUT.exists(): raise SystemExit(f"既存のため停止: {JSON_OUT}")

# ---------------- データ
df = pd.read_csv(R1 / "data" / "analysis_dataset_R2_with_diagnostics.csv", encoding="utf-8")
nat = pd.read_csv(R1 / "data" / "national_agesex_tablets.csv", encoding="utf-8"); nat = nat[nat.category == "all5"]
pop = pd.read_csv(R1 / "data" / "pop2023_age5_sex.csv", encoding="utf-8")
OLD = ["85～89歳", "90～94歳", "95～99歳", "100歳以上"]
nat["age"] = nat.age_group.replace({a: "85歳以上" for a in OLD}).str.strip()
nat["sex"] = nat.sex.map({"M": "男", "F": "女"})
nat = nat.groupby(["sex", "age"], as_index=False).tablets.sum()
p = pop[(pop.age != "総数") & (pop.sex != "男女計")].copy(); p["age"] = p.age.str.strip()
pn = p[p.area == "全国"].set_index(["sex", "age"]).population
assert set(nat.set_index(["sex", "age"]).index) == set(pn.index), "年齢階級の対応が取れない"
rate = nat.set_index(["sex", "age"]).tablets / pn.reindex(nat.set_index(["sex", "age"]).index)
print(f"年齢×性別 階級数={len(rate)}, 全国の1人あたり錠数量(標準化の基準)={nat.tablets.sum()/pn.sum():.1f}")
pj = p[p.area != "全国"].pivot_table(index="area", columns=["sex", "age"], values="population", aggfunc="sum")
E_exp = pj.mul(rate.reindex(pj.columns), axis=1).sum(axis=1)
d = df.set_index("prefecture")
O = d.qty_tablet
nat_per_res = nat.tablets.sum() / pn.sum()
d["E_exp"] = E_exp.reindex(d.index); d["SMR"] = O / d.E_exp
print(f"整合: Σ期待値/Σ観測値 = {d.E_exp.sum()/O.sum():.4f}; SMR 平均={d.SMR.mean():.3f}, SD={d.SMR.std():.3f}, 範囲={d.SMR.min():.2f}-{d.SMR.max():.2f}")
df = d.reset_index()
df["y_std"] = df.SMR * nat_per_res
print(f"標準化アウトカム: mean={df.y_std.mean():.1f}, SD={df.y_std.std(ddof=1):.1f}; 粗アウトカムとの相関 r={np.corrcoef(df.y, df.y_std)[0,1]:.3f}; 粗の高齢化率との相関 {np.corrcoef(df.y, df.aging_pct_2023)[0,1]:.3f} → 標準化後 {np.corrcoef(df.y_std, df.aging_pct_2023)[0,1]:.3f}")

# ---------------- 解析関数（R2_01 と同一定義）
COV = ["aging_pct_2023", "physicians_per100k_2022", "unemployment_pct_2023", "income_10000yen_FY2022"]
def make_w(dd, k=4):
    w = KNN.from_array(dd[["lon", "lat"]].values, k=k, distance_metric="ARC", radius=6371.0088); w = w.symmetrize(); w.transform = "R"; return w
def sblock(y, X, w):
    ys = ((y - y.mean()) / y.std(ddof=1)).values.reshape(-1, 1); Xs = ((X - X.mean()) / X.std(ddof=1)).values
    sc = y.std(ddof=1) / X.iloc[:, 0].std(ddof=1)
    sp = spOLS(ys, Xs, w=w, spat_diag=True, moran=True); lag = ML_Lag(ys, Xs, w=w); err = ML_Error(ys, Xs, w=w)
    return dict(lm_lag=(float(sp.lm_lag[0]), float(sp.lm_lag[1])), lm_err=(float(sp.lm_error[0]), float(sp.lm_error[1])),
                rlm_lag=(float(sp.rlm_lag[0]), float(sp.rlm_lag[1])), rlm_err=(float(sp.rlm_error[0]), float(sp.rlm_error[1])),
                moran_res=(float(sp.moran_res[0]), float(sp.moran_res[1]), float(sp.moran_res[2])),
                slm_beta=float(lag.betas[1][0] * sc), slm_p=float(lag.z_stat[1][1]), slm_z=float(lag.z_stat[1][0]), slm_rho=float(lag.rho),
                sem_beta=float(err.betas[1][0] * sc), sem_p=float(err.z_stat[1][1]), sem_z=float(err.z_stat[1][0]), sem_lam=float(err.lam))
def choose(sb):
    a, b = sb["lm_lag"][1], sb["lm_err"][1]
    if a < 0.05 and b < 0.05: return "SLM" if sb["rlm_lag"][1] < sb["rlm_err"][1] else "SEM"
    if a < 0.05: return "SLM"
    if b < 0.05: return "SEM"
    return "OLS"
def run(ycol, xcols, label):
    y = df[ycol]; X = df[xcols]; Xc = sm.add_constant(X)
    m = sm.OLS(y, Xc).fit(); mh = sm.OLS(y, Xc).fit(cov_type="HC3")
    ci = mh.conf_int(); vif = max(variance_inflation_factor(Xc.values, i) for i in range(1, Xc.shape[1]))
    w = make_w(df, 4); sb = sblock(y, X, w); sel = choose(sb)
    ks = {}
    for k in (3, 5, 6):
        s2 = sblock(y, X, make_w(df, k)); ks[k] = dict(sel=choose(s2), slm_p=s2["slm_p"], sem_p=s2["sem_p"])
    ks[4] = dict(sel=sel, slm_p=sb["slm_p"], sem_p=sb["sem_p"])
    out = dict(label=label, ycol=ycol, n=len(df), r2=float(m.rsquared), adj_r2=float(m.rsquared_adj), vif_max=float(vif),
               per_month=float(mh.params.iloc[1] / 12), ci_lo=float(ci.iloc[1, 0] / 12), ci_hi=float(ci.iloc[1, 1] / 12), p_hc3=float(mh.pvalues.iloc[1]),
               std_beta=float(mh.params.iloc[1] * X.iloc[:, 0].std(ddof=1) / y.std(ddof=1)), selected=sel, sb=sb, ks=ks,
               slm_pm=sb["slm_beta"] / 12, sem_pm=sb["sem_beta"] / 12,
               aging_beta=(float(mh.params["aging_pct_2023"]) if "aging_pct_2023" in X.columns else None),
               aging_p=(float(mh.pvalues["aging_pct_2023"]) if "aging_pct_2023" in X.columns else None),
               coef={n: dict(beta=float(mh.params[n]), p=float(mh.pvalues[n])) for n in X.columns})
    return out

np.random.seed(SEED)
R = {"nat_per_resident": float(nat_per_res), "y_std_mean": float(df.y_std.mean()), "y_std_sd": float(df.y_std.std(ddof=1)),
     "smr_mean": float(df.SMR.mean()), "smr_sd": float(df.SMR.std()), "smr_min": float(df.SMR.min()), "smr_max": float(df.SMR.max()),
     "r_crude_std": float(np.corrcoef(df.y, df.y_std)[0, 1]), "r_aging_crude": float(np.corrcoef(df.y, df.aging_pct_2023)[0, 1]),
     "r_aging_std": float(np.corrcoef(df.y_std, df.aging_pct_2023)[0, 1]), "sum_expected_over_observed": float(df.E_exp.sum() / O.sum())}
R["A_primary_covariates"] = run("y_std", ["x"] + COV, "Standardized outcome, primary covariates")
R["B_without_aging"] = run("y_std", ["x"] + [c for c in COV if c != "aging_pct_2023"], "Standardized outcome, without aging rate")
R["C_crude_reference"] = run("y", ["x"] + COV, "Crude outcome (primary analysis)")
with open(JSON_OUT, "w", encoding="utf-8") as f: json.dump(R, f, ensure_ascii=False, indent=1, default=float)
df[["prefecture_en", "SMR", "y_std"]].to_csv(R1 / "data" / "standardized_outcome.csv", index=False, encoding="utf-8")

for key in ("C_crude_reference", "A_primary_covariates", "B_without_aging"):
    r = R[key]; s = r["sb"]
    print("-" * 70); print(r["label"])
    print(f"  OLS(HC3): 1か月あたり {r['per_month']:.2f} [{r['ci_lo']:.2f}, {r['ci_hi']:.2f}] 錠/人/年, p={r['p_hc3']:.4f}; 標準化β={r['std_beta']:.2f}; adjR2={r['adj_r2']:.3f}; VIFmax={r['vif_max']:.1f}")
    print(f"  高齢化率: β={r['aging_beta']}, p={r['aging_p']}" if r["aging_beta"] is not None else "  (高齢化率なし)")
    print(f"  残差Moran I={s['moran_res'][0]:.3f} (p={s['moran_res'][2]:.4f}); LM-lag p={s['lm_lag'][1]:.4f}, LM-err p={s['lm_err'][1]:.4f}, RLM-lag p={s['rlm_lag'][1]:.4f}, RLM-err p={s['rlm_err'][1]:.4f} → {r['selected']}")
    print(f"  SLM: {r['slm_pm']:.2f} p={s['slm_p']:.4f} (rho={s['slm_rho']:.2f}); SEM: {r['sem_pm']:.2f} p={s['sem_p']:.4f} (lam={s['sem_lam']:.2f})")
    print("  k別: " + "; ".join(f"k={k}: sel={v['sel']} SLM p={v['slm_p']:.3f} SEM p={v['sem_p']:.3f}" for k, v in sorted(r["ks"].items())))
