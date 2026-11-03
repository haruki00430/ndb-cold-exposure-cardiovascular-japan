# -*- coding: utf-8 -*-
"""
R2_01: 改訂の主解析・空間解析・感度分析（仕様: R2_Analysis_Specification.md）。
都道府県別の実数は print しない。結果は results/*.csv と results/R2_results.json に保存（既存があれば停止）。
実行: NDB_Research_Hub/.venv（libpysal, esda, spreg）
"""
import sys, json, hashlib, pickle, warnings
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.multitest import multipletests
from scipy import stats
import geopandas as gpd
from libpysal.weights import KNN
from esda.moran import Moran, Moran_Local
import spreg.output as _o, spreg.ml_error as _me, spreg.ml_lag as _ml
for _mod in (_o, _me, _ml):                               # spreg + NumPy2.x: 要約文の書式化のみ無効化（推定には無関係）
    for _nm in ("_nonspat_top", "_nonspat_mid", "_spat_top", "_spat_mid", "_summary_chow", "_summary_vif"):
        if hasattr(_mod, _nm): setattr(_mod, _nm, lambda *a, **k: "")
from spreg import OLS as spOLS, ML_Lag, ML_Error
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P

SEED = 20261102
PROJ = P.PROJ
R1 = P.R1
RES = R1 / "results"; RES.mkdir(exist_ok=True)
SUP = R1 / "supplement"; SUP.mkdir(exist_ok=True)
JSON_OUT = RES / "R2_results.json"
if JSON_OUT.exists(): raise SystemExit(f"既存のため停止: {JSON_OUT}")
spec_hash = hashlib.sha256((R1 / "R2_Analysis_Specification.md").read_bytes()).hexdigest()
print("仕様書 SHA256:", spec_hash)

df = pd.read_csv(R1 / "data" / "analysis_dataset_R2.csv", encoding="utf-8")
# ---- 県重心（経緯度）: 元スクリプトと同じ県ポリゴンキャッシュを使用し、必ず df の並びに合わせる
cent_csv = pd.read_csv(P.DATA / "prefecture_centroids.csv", encoding="utf-8")[["prefecture", "lon", "lat"]]   # 県重心（R5_00で元の形状から作成）
df = df.merge(cent_csv, on="prefecture", how="left", validate="one_to_one")
assert df[["lon", "lat"]].notna().all().all() and len(df) == 47

df["y"] = df.qty_tablet / df.population_2023                     # 錠/人/年（主）
df["y_all"] = df.qty_all_units / df.population_2023              # 全単位5分類（元アウトカムの定義）
df["x"] = df.orig_Cold_months_ratio                              # 寒冷月比率（<5℃, 2016-2020, 60か月）
df["cold_months_per_year"] = df.x * 12
COV = ["aging_pct_2023", "physicians_per100k_2022", "unemployment_pct_2023", "income_10000yen_FY2022"]
COV_ORIG = ["orig_elderly_ratio", "orig_physicians_per_100k", "orig_unemployment_rate", "orig_income_per_capita"]
SD_X = df.x.std(ddof=1)

def make_w(d, k=4):
    w = KNN.from_array(d[["lon", "lat"]].values, k=k, distance_metric="ARC", radius=6371.0088)
    w = w.symmetrize(); w.transform = "R"; return w

def ols_info(y, X):
    Xc = sm.add_constant(X)
    m = sm.OLS(y, Xc).fit(); mh = sm.OLS(y, Xc).fit(cov_type="HC3")
    infl = m.get_influence()
    vif = {c: variance_inflation_factor(Xc.values, i) for i, c in enumerate(Xc.columns) if c != "const"}
    bp = het_breuschpagan(m.resid, Xc.values)
    sw = stats.shapiro(m.resid)
    return dict(m=m, mh=mh, vif=vif, bp_p=bp[1], sw_W=sw[0], sw_p=sw[1], cook=infl.cooks_distance[0], resid=m.resid.values)

def spatial_block(y, X, w):
    """標準化して OLS診断・SLM・SEM を推定し、先頭の説明変数（曝露）の係数を元の単位へ戻す。"""
    ys = ((y - y.mean()) / y.std(ddof=1)).values.reshape(-1, 1)
    Xs = ((X - X.mean()) / X.std(ddof=1)).values
    sd_y, sd_x = y.std(ddof=1), X.iloc[:, 0].std(ddof=1)
    sp = spOLS(ys, Xs, w=w, spat_diag=True, moran=True)
    lag = ML_Lag(ys, Xs, w=w); err = ML_Error(ys, Xs, w=w)
    sc = sd_y / sd_x
    return dict(
        lm_lag=(float(sp.lm_lag[0]), float(sp.lm_lag[1])), lm_err=(float(sp.lm_error[0]), float(sp.lm_error[1])),
        rlm_lag=(float(sp.rlm_lag[0]), float(sp.rlm_lag[1])), rlm_err=(float(sp.rlm_error[0]), float(sp.rlm_error[1])),
        moran_res=(float(sp.moran_res[0]), float(sp.moran_res[1]), float(sp.moran_res[2])),
        slm_beta_std=float(lag.betas[1][0]), slm_beta=float(lag.betas[1][0] * sc), slm_p=float(lag.z_stat[1][1]), slm_z=float(lag.z_stat[1][0]),
        slm_rho=float(lag.rho), slm_rho_p=float(lag.z_stat[-1][1]), slm_aic=float(lag.aic),
        sem_beta_std=float(err.betas[1][0]), sem_beta=float(err.betas[1][0] * sc), sem_p=float(err.z_stat[1][1]), sem_z=float(err.z_stat[1][0]),
        sem_lam=float(err.lam), sem_lam_p=float(err.z_stat[-1][1]), sem_aic=float(err.aic), ols_aic=float(sp.aic))

def choose_model(sb):
    a, b = sb["lm_lag"][1], sb["lm_err"][1]
    if a < 0.05 and b < 0.05: return "SLM" if sb["rlm_lag"][1] < sb["rlm_err"][1] else "SEM"
    if a < 0.05: return "SLM"
    if b < 0.05: return "SEM"
    return "OLS"

def full(d, ycol, xcols, k=4):
    y = d[ycol]; X = d[xcols]; o = ols_info(y, X); w = make_w(d, k); sb = spatial_block(y, X, w)
    b = o["mh"].params.iloc[1]; p = o["mh"].pvalues.iloc[1]
    zs = o["mh"].params.iloc[1] * X.iloc[:, 0].std(ddof=1) / y.std(ddof=1)
    return dict(o=o, sb=sb, w=w, beta=float(b), p_hc3=float(p), std_beta=float(zs), sel=choose_model(sb))

R = {"spec_sha256": spec_hash, "seed": SEED}
np.random.seed(SEED)

# ============================================================ 1. 記述統計・相関・単変量
desc_vars = [("y", "Tablets per resident per year (5 categories, tablets only)"), ("x", "Cold month ratio (<5°C, 60 months, 2016-2020)"),
             ("cold_months_per_year", "Cold months per year (ratio x 12)"), ("orig_Mean_Temp_avg", "Mean annual temperature (°C)"),
             ("aging_pct_2023", "Aging rate (%)"), ("physicians_per100k_2022", "Physicians in medical facilities per 100,000"),
             ("unemployment_pct_2023", "Unemployment rate (%)"), ("income_10000yen_FY2022", "Per capita prefectural income (10,000 yen)")]
rows = []
for c, lab in desc_vars:
    s = df[c]; sw = stats.shapiro(s)
    rows.append(dict(variable=lab, col=c, mean=s.mean(), sd=s.std(ddof=1), min=s.min(), max=s.max(), shapiro_p=sw[1]))
T1 = pd.DataFrame(rows); T1.to_csv(RES / "T1_descriptives.csv", index=False, encoding="utf-8")
R["desc"] = {r["col"]: {k: float(r[k]) for k in ["mean", "sd", "min", "max", "shapiro_p"]} for r in rows}

cv = ["y", "x", "orig_Mean_Temp_avg", "physicians_per100k_2022", "unemployment_pct_2023", "aging_pct_2023", "income_10000yen_FY2022"]
cm = df[cv].corr(); pm = pd.DataFrame(np.ones((7, 7)), index=cv, columns=cv)
for i in cv:
    for j in cv:
        if i != j: pm.loc[i, j] = stats.pearsonr(df[i], df[j])[1]
cm.to_csv(RES / "T2_correlation_r.csv", encoding="utf-8"); pm.to_csv(RES / "T2_correlation_p.csv", encoding="utf-8")
R["corr"] = {"cols": cv, "r": cm.values.tolist(), "p": pm.values.tolist()}

TEMPS = [("x", "Cold month ratio (<5°C)"), ("orig_Mean_Temp_avg", "Mean annual temperature"), ("orig_Winter_temp_avg", "Winter mean temperature"),
         ("orig_Temp_std", "Temperature variability (SD)"), ("orig_Temp_range_annual", "Annual temperature range")]
uni = []
for c, lab in TEMPS:
    X = sm.add_constant(df[[c]]); m = sm.OLS(df.y, X).fit(); mh = sm.OLS(df.y, X).fit(cov_type="HC3")
    uni.append(dict(indicator=lab, col=c, beta=m.params[c], se=m.bse[c], r2=m.rsquared, p=m.pvalues[c], p_hc3=mh.pvalues[c]))
T3 = pd.DataFrame(uni); T3.to_csv(RES / "T3_univariable.csv", index=False, encoding="utf-8"); R["uni"] = uni

# ============================================================ 2. 主モデル
P = full(df, "y", ["x"] + COV)
o = P["o"]; mh = o["mh"]; m = o["m"]
names = ["Intercept", "Cold month ratio"] + ["Aging rate (%)", "Physicians per 100,000", "Unemployment rate (%)", "Per capita income (10,000 yen)"]
ci = mh.conf_int()
coef = []
for i, nm in enumerate(names):
    coef.append(dict(term=nm, beta=float(mh.params.iloc[i]), se_hc3=float(mh.bse.iloc[i]), ci_lo=float(ci.iloc[i, 0]), ci_hi=float(ci.iloc[i, 1]),
                     p_hc3=float(mh.pvalues.iloc[i]), se_classic=float(m.bse.iloc[i]), p_classic=float(m.pvalues.iloc[i])))
T4 = pd.DataFrame(coef); T4.to_csv(RES / "T4_primary_ols.csv", index=False, encoding="utf-8")
b, lo, hi = mh.params.iloc[1], ci.iloc[1, 0], ci.iloc[1, 1]
R["primary"] = dict(coef=coef, r2=float(m.rsquared), adj_r2=float(m.rsquared_adj), F=float(m.fvalue), F_p=float(m.f_pvalue), n=int(m.nobs),
                    vif={k: float(v) for k, v in o["vif"].items()}, bp_p=float(o["bp_p"]), sw_W=float(o["sw_W"]), sw_p=float(o["sw_p"]),
                    per_month=dict(beta=float(b / 12), ci_lo=float(lo / 12), ci_hi=float(hi / 12)),
                    per_sd=dict(beta=float(b * SD_X), ci_lo=float(lo * SD_X), ci_hi=float(hi * SD_X), sd_x=float(SD_X)),
                    std_beta=P["std_beta"], p_hc3=P["p_hc3"], y_mean=float(df.y.mean()), y_sd=float(df.y.std(ddof=1)),
                    pct_of_mean_per_month=float(b / 12 / df.y.mean() * 100))
cook = pd.Series(o["cook"], index=df.prefecture_en); th = 4 / 47
over = cook[cook > th].sort_values(ascending=False)
R["cook"] = dict(threshold=th, over=list(over.index), max_name=cook.idxmax(), max_val=float(cook.max()), over_vals={k: float(v) for k, v in over.items()})

# ============================================================ 3. 空間解析（並びは df に統一）
sbp = P["sb"]; w4 = P["w"]
np.random.seed(SEED); mi_y = Moran(df.y.values, w4, permutations=999)
np.random.seed(SEED); mi_r = Moran(o["resid"], w4, permutations=999)
np.random.seed(SEED); lisa = Moran_Local(df.y.values, w4, permutations=999)
lab = {1: "High-High", 2: "Low-High", 3: "Low-Low", 4: "High-Low"}
lisa_sig = [(df.prefecture_en[i], lab[int(lisa.q[i])]) for i in range(47) if lisa.p_sim[i] < 0.05]
df["lisa_cluster"] = [lab[int(lisa.q[i])] if lisa.p_sim[i] < 0.05 else "n.s." for i in range(47)]
df["cook_d"] = o["cook"]
np.random.seed(SEED); mi_x = Moran(df.x.values, w4, permutations=999)
R["spatial"] = dict(moran_y=dict(I=float(mi_y.I), z=float(mi_y.z_sim), p=float(mi_y.p_sim)), moran_resid_perm=dict(I=float(mi_r.I), p=float(mi_r.p_sim)),
                    moran_x=dict(I=float(mi_x.I), p=float(mi_x.p_sim)), block_k4=sbp, selected=P["sel"], lisa=lisa_sig,
                    n_islands_k4=len(w4.islands), n_neighbors_min=int(min(w4.cardinalities.values())), n_neighbors_max=int(max(w4.cardinalities.values())))
ks = {}
for k in (3, 4, 5, 6):
    sb = P["sb"] if k == 4 else spatial_block(df.y, df[["x"] + COV], make_w(df, k))
    ks[k] = dict(sb=sb, sel=choose_model(sb))
R["spatial_k"] = ks
rows = []
for k, v in ks.items():
    s = v["sb"]
    rows.append(dict(k=k, moran_resid=s["moran_res"][0], moran_resid_p=s["moran_res"][2], lm_lag_p=s["lm_lag"][1], lm_err_p=s["lm_err"][1], rlm_lag_p=s["rlm_lag"][1], rlm_err_p=s["rlm_err"][1],
                     selected=v["sel"], slm_beta=s["slm_beta"], slm_p=s["slm_p"], slm_rho=s["slm_rho"], sem_beta=s["sem_beta"], sem_p=s["sem_p"], sem_lam=s["sem_lam"]))
pd.DataFrame(rows).to_csv(RES / "T5_spatial_by_k.csv", index=False, encoding="utf-8")

# ============================================================ 4. 感度分析
sens = {}
# 4.1 曝露5指標（多変量, HC3, BH補正）
ind = []
for c, lab_ in TEMPS:
    X = df[[c] + COV]; mm = sm.OLS(df.y, sm.add_constant(X)).fit(); mhh = sm.OLS(df.y, sm.add_constant(X)).fit(cov_type="HC3")
    sd_c = df[c].std(ddof=1)
    ind.append(dict(indicator=lab_, beta=mhh.params[c], ci_lo=mhh.conf_int().loc[c, 0], ci_hi=mhh.conf_int().loc[c, 1], p_hc3=mhh.pvalues[c],
                    std_beta=mhh.params[c] * sd_c / df.y.std(ddof=1), adj_r2=mm.rsquared_adj))
pb = multipletests([r["p_hc3"] for r in ind], method="fdr_bh")[1]
for r, q in zip(ind, pb): r["p_bh"] = float(q)
pd.DataFrame(ind).to_csv(RES / "S_indicators_multivariable.csv", index=False, encoding="utf-8"); sens["indicators"] = ind

# 4.2 影響点・除外
def excl(names_en, label):
    d = df[~df.prefecture_en.isin(names_en)].reset_index(drop=True)
    r = full(d, "y", ["x"] + COV)
    return dict(label=label, n=len(d), beta=r["beta"], per_month=r["beta"] / 12, p_hc3=r["p_hc3"], std_beta=r["std_beta"], selected=r["sel"],
                slm_beta=r["sb"]["slm_beta"] / 12, slm_p=r["sb"]["slm_p"], sem_beta=r["sb"]["sem_beta"] / 12, sem_p=r["sb"]["sem_p"])
ex = [excl([], "All 47 prefectures"), excl(list(over.index), "Excluding Cook's D > 4/n"), excl([cook.idxmax()], f"Excluding highest Cook's D ({cook.idxmax()})"),
      excl(["Hokkaido", "Okinawa"], "Excluding Hokkaido and Okinawa"), excl(["Tokyo"], "Excluding Tokyo")]
pd.DataFrame(ex).to_csv(RES / "S_exclusions.csv", index=False, encoding="utf-8"); sens["exclusions"] = ex
loo = []
for p_ in df.prefecture_en:
    d = df[df.prefecture_en != p_]
    mm = sm.OLS(d.y, sm.add_constant(d[["x"] + COV])).fit(cov_type="HC3"); loo.append((float(mm.params["x"]), float(mm.pvalues["x"])))
sens["loo"] = dict(p_max=max(p for _, p in loo), p_min=min(p for _, p in loo), beta_min=min(b for b, _ in loo), beta_max=max(b for b, _ in loo), all_sig=all(p < 0.05 for _, p in loo))

# 4.3 仕様の組合せ（アウトカム×曝露×共変量）
d2 = df.copy()
d2["y_tab214"] = d2.qty_tab_antihypertensive / d2.population_2023
d2["y_all214"] = d2.qty_all_antihypertensive / d2.population_2023
d2["x_fy5"] = d2.cx_cold_ratio5_FY2023; d2["x_fy10"] = d2.cx_cold_ratio_FY2023
outs = [("tablets, 5 categories (primary)", "y"), ("all units, 5 categories (original definition)", "y_all"), ("tablets, category 214", "y_tab214"), ("all units, category 214", "y_all214")]
exps = [("<5°C, 2016-2020 (primary)", "x"), ("<5°C, FY2023", "x_fy5"), ("<10°C, FY2023", "x_fy10")]
covs = [("year-aligned (primary)", COV), ("original covariates", COV_ORIG)]
grid = []
for on, oc in outs:
    for en, ec in exps:
        for cn, cc in covs:
            r = full(d2, oc, [ec] + cc)
            grid.append(dict(outcome=on, exposure=en, covariates=cn, std_beta=r["std_beta"], ols_hc3_p=r["p_hc3"], slm_p=r["sb"]["slm_p"], sem_p=r["sb"]["sem_p"],
                             lm_lag_p=r["sb"]["lm_lag"][1], lm_err_p=r["sb"]["lm_err"][1], selected=r["sel"],
                             selected_p=(r["p_hc3"] if r["sel"] == "OLS" else (r["sb"]["slm_p"] if r["sel"] == "SLM" else r["sb"]["sem_p"]))))
G = pd.DataFrame(grid); G.to_csv(RES / "S_specification_grid.csv", index=False, encoding="utf-8"); sens["grid"] = grid
# 元の完全設定（元アウトカム/人口2020/元共変量, 元の並びずれを除いた正しい空間解析）
d3 = df.copy(); d3["y_orig"] = d3.orig_cvd_total_quantity / d3.orig_population_2020 * 1e5
r0 = full(d3, "y_orig", ["x"] + COV_ORIG)
sens["original_spec"] = dict(std_beta=r0["std_beta"], ols_hc3_p=r0["p_hc3"], adj_r2=float(r0["o"]["m"].rsquared_adj), r2=float(r0["o"]["m"].rsquared),
                             beta=r0["beta"], slm_p=r0["sb"]["slm_p"], sem_p=r0["sb"]["sem_p"], selected=r0["sel"], lm_lag_p=r0["sb"]["lm_lag"][1], lm_err_p=r0["sb"]["lm_err"][1],
                             moran_res=r0["sb"]["moran_res"][0], moran_res_p=r0["sb"]["moran_res"][2])

# 4.4 薬効分類別
catr = []
labs = {"antihypertensive": "214 Antihypertensives", "vasodilator": "217 Vasodilators", "antihyperlipidemic": "218 Antihyperlipidemics", "other_cv": "219 Other cardiovascular agents", "anticoagulant": "333 Anticoagulants"}
for k_, nm in labs.items():
    d2["yc"] = d2[f"qty_tab_{k_}"] / d2.population_2023
    r = full(d2, "yc", ["x"] + COV)
    s = r["sb"]
    catr.append(dict(category=nm, mean=float(d2.yc.mean()), std_beta=r["std_beta"], per_month=r["beta"] / 12, ols_hc3_p=r["p_hc3"], selected=r["sel"],
                     slm_p=s["slm_p"], sem_p=s["sem_p"], lm_lag_p=s["lm_lag"][1], lm_err_p=s["lm_err"][1]))
pc = multipletests([c["ols_hc3_p"] for c in catr], method="fdr_bh")[1]
for c, q in zip(catr, pc): c["ols_p_bh"] = float(q)
pd.DataFrame(catr).to_csv(RES / "S_categories.csv", index=False, encoding="utf-8"); sens["categories"] = catr

# 4.5 追加交絡（Codex編纂の公式資料由来・未独立検証）
d2["sodium_mean"] = d2[["cx_sodium_g_day_male_age_adjusted_NHNS2016", "cx_sodium_g_day_female_age_adjusted_NHNS2016"]].mean(axis=1, skipna=False)
adds = [("+ BMI (checkup FY2022)", ["cx_BMI_standardized_checkup2022"]), ("+ Smoking (checkup FY2022)", ["cx_smoking_pct_age_sex_standardized_checkup2022"]),
        ("+ Systolic BP (checkup FY2022)", ["cx_SBP_standardized_checkup2022"]), ("+ SBP >=140 mmHg % (checkup FY2022)", ["cx_SBP_ge140_pct_standardized_checkup2022"]),
        ("+ BMI, smoking, systolic BP", ["cx_BMI_standardized_checkup2022", "cx_smoking_pct_age_sex_standardized_checkup2022", "cx_SBP_standardized_checkup2022"]),
        ("+ Sodium intake (NHNS 2016; 46 prefectures)", ["sodium_mean"])]
ar = []
for lab_, add in adds:
    d = d2.dropna(subset=add).reset_index(drop=True)
    r = full(d, "y", ["x"] + COV + add)
    ar.append(dict(model=lab_, n=len(d), per_month=r["beta"] / 12, std_beta=r["std_beta"], ols_hc3_p=r["p_hc3"], selected=r["sel"], slm_p=r["sb"]["slm_p"], sem_p=r["sb"]["sem_p"],
                   vif_max=float(max(r["o"]["vif"].values()))))
pd.DataFrame(ar).to_csv(RES / "S_added_confounders.csv", index=False, encoding="utf-8"); sens["added"] = ar
R["sens"] = sens

# ============================================================ 5. 補足表S1（47県）
S1 = pd.DataFrame({
    "Prefecture code": df.pref_code, "Prefecture": df.prefecture_en, "JMA station": df.station, "Months used (n)": df.n_months,
    "Months with mean temperature <5°C (n)": df.n_cold_months_lt5, "Cold month ratio (<5°C)": df.x, "Cold months per year (ratio x 12)": df.cold_months_per_year,
    "Mean annual temperature (°C)": df.orig_Mean_Temp_avg, "Winter mean temperature (°C)": df.orig_Winter_temp_avg, "Temperature SD (°C)": df.orig_Temp_std,
    "Annual temperature range (°C)": df.orig_Temp_range_annual,
    "Observed tablets, 5 categories (n)": df.qty_tablet, "Population, 1 Oct 2023": df.population_2023, "Tablets per resident per year (primary outcome)": df.y,
    "All-unit quantity per resident per year (original definition)": df.y_all,
    "Aging rate, 1 Oct 2023 (%)": df.aging_pct_2023, "Physicians in medical facilities per 100,000, Dec 2022": df.physicians_per100k_2022,
    "Unemployment rate, 2023 (%)": df.unemployment_pct_2023, "Per capita prefectural income, FY2022 (10,000 yen)": df.income_10000yen_FY2022,
    "Cook's distance (primary model)": df.cook_d, "LISA cluster (p<0.05)": df.lisa_cluster})
S1.to_csv(SUP / "Supplementary_Table_S1.csv", index=False, encoding="utf-8-sig")
S1.to_excel(SUP / "Supplementary_Table_S1.xlsx", index=False)
df.to_csv(R1 / "data" / "analysis_dataset_R2_with_diagnostics.csv", index=False, encoding="utf-8")
with open(JSON_OUT, "w", encoding="utf-8") as f: json.dump(R, f, ensure_ascii=False, indent=1, default=float)

# ============================================================ 要約（集計値のみ）
pr = R["primary"]; sp_ = R["spatial"]; s4 = sp_["block_k4"]
print("=" * 70); print("主モデル (P): 錠/人/年 ~ 寒冷月比率(<5℃,2016-20) + 高齢化2023 + 医師2022 + 失業2023 + 所得FY2022; n=47")
print(f"  アウトカム mean={pr['y_mean']:.1f} SD={pr['y_sd']:.1f} 錠/人/年; 比率 mean={df.x.mean():.3f} SD={SD_X:.3f}")
print(f"  OLS(HC3): 比率 β={pr['coef'][1]['beta']:.1f} [95%CI {pr['coef'][1]['ci_lo']:.1f}, {pr['coef'][1]['ci_hi']:.1f}] p={pr['p_hc3']:.4f}; 標準化β={pr['std_beta']:.3f}")
print(f"  1か月/年あたり β={pr['per_month']['beta']:.2f} [{pr['per_month']['ci_lo']:.2f}, {pr['per_month']['ci_hi']:.2f}] 錠/人/年 ({pr['pct_of_mean_per_month']:.1f}% of mean); 1SDあたり {pr['per_sd']['beta']:.1f}")
print(f"  R2={pr['r2']:.3f} adjR2={pr['adj_r2']:.3f} F={pr['F']:.2f}; VIF max={max(pr['vif'].values()):.2f}; BP p={pr['bp_p']:.3f}; Shapiro p={pr['sw_p']:.3f}")
for c in pr["coef"][2:]: print(f"    {c['term']:34s} β={c['beta']:.3f} p(HC3)={c['p_hc3']:.4f}")
print(f"  Cook's D>4/n: {R['cook']['over']} (max {R['cook']['max_name']}={R['cook']['max_val']:.3f})")
print("-" * 70); print("空間（k=4, 大圏距離）")
print(f"  Moran I(アウトカム)={sp_['moran_y']['I']:.3f} (z={sp_['moran_y']['z']:.2f}, p={sp_['moran_y']['p']:.4f}); 曝露 I={sp_['moran_x']['I']:.3f} (p={sp_['moran_x']['p']:.4f})")
print(f"  残差 Moran I={s4['moran_res'][0]:.3f} (p={s4['moran_res'][2]:.4f}); LM-lag p={s4['lm_lag'][1]:.4f}, LM-err p={s4['lm_err'][1]:.4f}, RLM-lag p={s4['rlm_lag'][1]:.4f}, RLM-err p={s4['rlm_err'][1]:.4f} → 選択: {sp_['selected']}")
print(f"  SLM: 1か月あたり β={s4['slm_beta']/12:.2f} p={s4['slm_p']:.4f} rho={s4['slm_rho']:.2f} (p={s4['slm_rho_p']:.4f}); SEM: β={s4['sem_beta']/12:.2f} p={s4['sem_p']:.4f} lambda={s4['sem_lam']:.2f} (p={s4['sem_lam_p']:.4f})")
print(f"  LISA(p<0.05): {lisa_sig}")
for k, v in ks.items():
    s = v["sb"]; print(f"  k={k}: 残差I={s['moran_res'][0]:.3f} LMlag p={s['lm_lag'][1]:.4f} LMerr p={s['lm_err'][1]:.4f} RLMlag p={s['rlm_lag'][1]:.4f} RLMerr p={s['rlm_err'][1]:.4f} 選択={v['sel']} | SLM p={s['slm_p']:.4f} SEM p={s['sem_p']:.4f}")
print("-" * 70); print("感度分析")
for r in ind: print(f"  指標 {r['indicator']:32s} std β={r['std_beta']:+.3f} p(HC3)={r['p_hc3']:.4f} BH={r['p_bh']:.4f} adjR2={r['adj_r2']:.3f}")
for r in ex: print(f"  除外 {r['label']:44s} n={r['n']} OLS p={r['p_hc3']:.4f} 選択={r['selected']} SLM p={r['slm_p']:.4f} SEM p={r['sem_p']:.4f}")
print(f"  LOO: p範囲 {sens['loo']['p_min']:.4f}〜{sens['loo']['p_max']:.4f}, 全てp<0.05={sens['loo']['all_sig']}")
print("  元の完全設定:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sens["original_spec"].items()})
print("  --- 仕様グリッド（std β / OLS p / 選択モデルのp）---")
for r in grid: print(f"    {r['outcome'][:34]:34s}| {r['exposure'][:24]:24s}| {r['covariates'][:12]:12s}| β={r['std_beta']:+.2f} OLSp={r['ols_hc3_p']:.4f} sel={r['selected']} selp={r['selected_p']:.4f}")
print("  --- 薬効分類別 ---")
for c in catr: print(f"    {c['category']:32s} stdβ={c['std_beta']:+.2f} OLSp={c['ols_hc3_p']:.4f} BH={c['ols_p_bh']:.4f} sel={c['selected']} SLMp={c['slm_p']:.4f} SEMp={c['sem_p']:.4f}")
print("  --- 追加交絡 ---")
for a in ar: print(f"    {a['model']:46s} n={a['n']} stdβ={a['std_beta']:+.2f} OLSp={a['ols_hc3_p']:.4f} sel={a['selected']} SLMp={a['slm_p']:.4f} SEMp={a['sem_p']:.4f} VIFmax={a['vif_max']:.1f}")
print("DONE")
