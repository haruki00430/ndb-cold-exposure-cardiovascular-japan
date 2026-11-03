# -*- coding: utf-8 -*-
"""
R7_00: 空間ラグモデル(SLM)の直接効果・間接効果・総効果（LeSage & Pace 2009）。
主モデル（R2_01 と同一: 曝露=寒冷月比率 + 4共変量、KNN k=4、行標準化）について、
 - 回帰係数 β（波及を含まない偏微分）
 - 平均直接効果 = mean(diag S)、平均総効果 = mean(行和 S)、平均間接効果 = 総効果 - 直接効果。S = (I - ρW)^-1 β
を、1か月/年あたり（β_std × sd_y/sd_x / 12）の単位で算出する。不確実性は最尤推定量の漸近分布（β, ρ）からの
シミュレーション（10,000回、seed 20261102）の2.5–97.5%点。k=3,5,6 も同様に算出する。結果は results/R7_results.json（既存なら停止）。
都道府県別の数値は出力しない。
"""
import sys, json, warnings
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding="utf-8"); warnings.filterwarnings("ignore")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import spatial_tools as S                       # NumPy2 + spreg の書式化パッチを含む
from spreg import ML_Lag

R1 = P.R1; OUT = R1 / "results" / "R7_results.json"
if OUT.exists(): raise SystemExit(f"既存のため停止: {OUT}")
SEED = 20261102; NSIM = 10000
df = pd.read_csv(R1 / "data" / "analysis_dataset_R2.csv", encoding="utf-8")
cent = pd.read_csv(P.DATA / "prefecture_centroids.csv", encoding="utf-8")[["prefecture", "lon", "lat"]]
df = df.merge(cent, on="prefecture", how="left", validate="one_to_one")
df["y"] = df.qty_tablet / df.population_2023; df["x"] = df.orig_Cold_months_ratio
COV = ["aging_pct_2023", "physicians_per100k_2022", "unemployment_pct_2023", "income_10000yen_FY2022"]
y = df["y"]; X = df[["x"] + COV]
sc = y.std(ddof=1) / X.iloc[:, 0].std(ddof=1)          # 標準化係数 → 元の単位（錠/人/年 per 1.0 unit of ratio）
ys = ((y - y.mean()) / y.std(ddof=1)).values.reshape(-1, 1); Xs = ((X - X.mean()) / X.std(ddof=1)).values


def effects(k):
    w = S.make_w(df, k); W = w.full()[0]; n = W.shape[0]
    lag = ML_Lag(ys, Xs, w=w)
    b = float(lag.betas[1][0]); rho = float(lag.rho)
    # 共分散: betas（定数項を含む）と rho。vm の並びは betas, rho（vm は (k+1)x(k+1) 以上）
    vm = np.asarray(lag.vm); idx = [1, vm.shape[0] - 1] if vm.shape[0] == len(lag.betas) + 1 else [1, len(lag.betas) - 1]
    # lag.betas の最後の要素が rho（spreg）。vm は同順の betas 行列
    nb = len(lag.betas); idx = [1, nb - 1]
    cov = vm[np.ix_(idx, idx)]
    rng = np.random.default_rng(SEED + k)
    draws = rng.multivariate_normal([b, rho], cov, size=NSIM)
    I = np.eye(n)

    def eff(bb, rr):
        if abs(rr) >= 0.999: return None
        Sx = np.linalg.inv(I - rr * W) * bb
        d = np.trace(Sx) / n; t = Sx.sum() / n               # 行標準化のとき t = bb/(1-rr)
        return d, t - d, t
    pt = eff(b, rho)
    sim = np.array([e for e in (eff(bb, rr) for bb, rr in draws) if e is not None])
    f = sc / 12.0
    res = {}
    for j, nm in enumerate(("direct", "indirect", "total")):
        lo, hi = np.percentile(sim[:, j], [2.5, 97.5])
        # シミュレーションに基づく p 値（0を含まない側の割合の2倍）
        p = float(min(1.0, 2 * min((sim[:, j] <= 0).mean(), (sim[:, j] >= 0).mean())))
        res[nm] = dict(est=pt[j] * f, lo=float(lo * f), hi=float(hi * f), p_sim=p)
    res["coef_per_month"] = b * f; res["rho"] = rho; res["n_sim_valid"] = int(len(sim))
    res["total_check"] = float(b / (1 - rho) * f)               # 解析解との一致確認
    return res


out = {"seed": SEED, "nsim": NSIM, "k4": effects(4), "k_sens": {str(k): effects(k) for k in (3, 5, 6)}}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in (("k=4", out["k4"]), *((f"k={k}", out["k_sens"][k]) for k in out["k_sens"])):
    print(k, f"係数/月={v['coef_per_month']:.2f} rho={v['rho']:.2f}",
          " | ".join(f"{n}: {v[n]['est']:.2f} ({v[n]['lo']:.2f} to {v[n]['hi']:.2f}; p~{v[n]['p_sim']:.3f})" for n in ("direct", "indirect", "total")), f"| 総効果の解析解={v['total_check']:.2f}")
