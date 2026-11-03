# -*- coding: utf-8 -*-
"""
spatial_tools: 主解析（R2_01）と同一定義の OLS(HC3)・空間診断・空間ラグ/誤差モデルの共通関数。
入力の DataFrame は lon, lat（県重心の経緯度）を持つこと。出力は集計値のみ。
"""
import warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from libpysal.weights import KNN
import spreg.output as _o, spreg.ml_error as _me, spreg.ml_lag as _ml
for _mod in (_o, _me, _ml):          # spreg + NumPy2.x: 要約文の書式化だけを無効化（推定には無関係）
    for _nm in ("_nonspat_top", "_nonspat_mid", "_spat_top", "_spat_mid", "_summary_chow", "_summary_vif"):
        if hasattr(_mod, _nm): setattr(_mod, _nm, lambda *a, **k: "")
from spreg import OLS as spOLS, ML_Lag, ML_Error
warnings.filterwarnings("ignore")


def make_w(d, k=4):
    w = KNN.from_array(d[["lon", "lat"]].values, k=k, distance_metric="ARC", radius=6371.0088)
    w = w.symmetrize(); w.transform = "R"; return w


def spatial_block(y, X, w):
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


def run_model(df, ycol, xcols, label, ks=(3, 5, 6)):
    y = df[ycol]; X = df[xcols]; Xc = sm.add_constant(X)
    m = sm.OLS(y, Xc).fit(); mh = sm.OLS(y, Xc).fit(cov_type="HC3"); ci = mh.conf_int()
    vif = max(variance_inflation_factor(Xc.values, i) for i in range(1, Xc.shape[1]))
    sb = spatial_block(y, X, make_w(df, 4)); sel = choose(sb)
    kk = {4: dict(sel=sel, slm_p=sb["slm_p"], sem_p=sb["sem_p"])}
    for k in ks:
        s2 = spatial_block(y, X, make_w(df, k)); kk[k] = dict(sel=choose(s2), slm_p=s2["slm_p"], sem_p=s2["sem_p"])
    return dict(label=label, ycol=ycol, n=len(df), r2=float(m.rsquared), adj_r2=float(m.rsquared_adj), vif_max=float(vif),
                per_month=float(mh.params.iloc[1] / 12), ci_lo=float(ci.iloc[1, 0] / 12), ci_hi=float(ci.iloc[1, 1] / 12), p_hc3=float(mh.pvalues.iloc[1]),
                std_beta=float(mh.params.iloc[1] * X.iloc[:, 0].std(ddof=1) / y.std(ddof=1)), selected=sel, sb=sb, ks=kk,
                slm_pm=sb["slm_beta"] / 12, sem_pm=sb["sem_beta"] / 12,
                coef={n: dict(beta=float(mh.params[n]), p=float(mh.pvalues[n])) for n in X.columns})
