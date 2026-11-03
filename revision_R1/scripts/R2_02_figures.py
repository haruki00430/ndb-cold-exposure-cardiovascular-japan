# -*- coding: utf-8 -*-
"""
R2_02: 改訂用図（Figure 1-3）。データからの通常のプロットのみ（生成AIによる画像作成・加工なし）。
JPG, 幅16.5 cm, 500 dpi。既存ファイルがあれば停止。実数の print はしない。
"""
import sys, pickle, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import statsmodels.api as sm
from scipy import stats
import geopandas as gpd
from libpysal.weights import KNN
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P

PROJ = P.PROJ
R1 = P.R1
FIG = R1 / "figures"; FIG.mkdir(exist_ok=True)
DPI = 500; W = 16.5 / 2.54
plt.rcParams.update({"font.size": 7, "axes.titlesize": 8, "axes.labelsize": 7, "font.family": "DejaVu Sans", "axes.linewidth": 0.6})

df = pd.read_csv(R1 / "data" / "analysis_dataset_R2_with_diagnostics.csv", encoding="utf-8")
g0 = gpd.read_file(P.DATA / "prefecture_geometry.gpkg", layer="prefecture")   # 簡略化済みの地図用形状（R5_00）
g = g0.merge(df, on="prefecture", how="left", validate="one_to_one")

def style_map(ax):
    ax.set_axis_off(); ax.set_xlim(122, 146.5); ax.set_ylim(24, 46)

# ---------------- Figure 1
fig, axs = plt.subplots(1, 2, figsize=(W, 3.5))
for ax, c, ttl, cmap, lab in [(axs[0], "x", "A  Cold month ratio\n(months <5°C, 2016–2020)", "Blues", "Proportion of 60 months"),
                              (axs[1], "y", "B  Dispensed cardiovascular tablets\n(FY2023)", "YlOrRd", "Tablets per resident per year")]:
    g.plot(column=c, cmap=cmap, linewidth=0.2, edgecolor="0.3", legend=True, ax=ax,
           legend_kwds={"shrink": 0.6, "label": lab, "orientation": "horizontal", "pad": 0.02})
    ax.set_title(ttl, fontsize=7, loc="left"); style_map(ax)
plt.tight_layout(); fig.savefig(FIG / "Figure_1.jpg", dpi=DPI, pil_kwargs={"quality": 95}); plt.close(fig)

# ---------------- Figure 2: 診断
fig, axs = plt.subplots(1, 3, figsize=(W, 2.9))
ax = axs[0]
ax.scatter(df.x, df.y, s=9, c="#2b6cb0", edgecolors="white", linewidths=0.3)
b = np.polyfit(df.x, df.y, 1); xs = np.linspace(df.x.min(), df.x.max(), 50); ax.plot(xs, np.polyval(b, xs), color="0.2", lw=0.8)
# ラベルは点の近くではなく空いている領域（右下・回帰直線の下側）に置き、細い引き出し線で点に結ぶ
_pos = {"Tokyo": (0.20, 149.0), "Okinawa": (0.20, 137.0), "Hokkaido": (0.285, 184.0)}
for nm, (tx, ty) in _pos.items():
    r = df[df.prefecture_en == nm].iloc[0]
    ax.annotate(nm, (r.x, r.y), xytext=(tx, ty), textcoords="data", fontsize=5.5, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.4, color="0.35", shrinkA=1, shrinkB=2))
r = df[df.prefecture_en == "Akita"].iloc[0]; ax.annotate("Akita", (r.x, r.y), fontsize=5.5, xytext=(-4, 2), textcoords="offset points", ha="right")
ax.set_xlabel("Cold month ratio (<5°C)"); ax.set_ylabel("Tablets per resident per year"); ax.set_title("A  Unadjusted relation", loc="left", fontsize=7)
ax = axs[1]
cd = df[["prefecture_en", "cook_d"]].sort_values("cook_d", ascending=False).reset_index(drop=True)
ax.bar(range(47), cd.cook_d, color=["#c05621" if v > 4/47 else "#a0aec0" for v in cd.cook_d], width=0.8)
ax.set_yscale("log"); ax.set_ylim(min(cd.cook_d.min(), 4/47) * 0.5, cd.cook_d.max() * 6)
ax.axhline(4/47, color="k", ls="--", lw=0.6); ax.text(46.5, 4/47 * 1.1, "4/n", fontsize=5.5, va="bottom", ha="right")
n_over = int((cd.cook_d > 4/47).sum())
for i in range(min(n_over, 9)):                     # 棒には番号だけを付け、名称は凡例ボックスに並べる（重なりを構造的に防ぐ）
    ax.text(i, cd.cook_d[i] * (1.25 if i % 2 == 0 else 2.3), str(i + 1), fontsize=5.5, ha="center", va="bottom")   # 隣り合う番号が重ならないよう高さをずらす
_lst = "\n".join(f"{i + 1}  {cd.prefecture_en[i]} ({cd.cook_d[i]:.2f})" for i in range(min(n_over, 9)))
ax.text(0.97, 0.97, _lst, transform=ax.transAxes, fontsize=5.5, va="top", ha="right", bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.6", lw=0.4))
ax.set_xlabel("Prefectures (sorted)"); ax.set_ylabel("Cook's distance (log scale)"); ax.set_xticks([]); ax.set_title("B  Influence (primary model)", loc="left", fontsize=7)
ax = axs[2]
X = sm.add_constant(df[["x", "aging_pct_2023", "physicians_per100k_2022", "unemployment_pct_2023", "income_10000yen_FY2022"]])
res = sm.OLS(df.y, X).fit().resid
(osm, osr), (slope, icpt, r) = stats.probplot(res, dist="norm")
ax.scatter(osm, osr, s=9, c="#2b6cb0", edgecolors="white", linewidths=0.3); ax.plot(osm, slope * np.array(osm) + icpt, color="0.2", lw=0.8)
ax.set_xlabel("Theoretical quantiles"); ax.set_ylabel("OLS residuals"); ax.set_title("C  Normal Q–Q plot", loc="left", fontsize=7)
plt.tight_layout(); fig.savefig(FIG / "Figure_2.jpg", dpi=DPI, pil_kwargs={"quality": 95}); plt.close(fig)

# ---------------- Figure 3: Moran 散布図 + LISA 地図
w = KNN.from_array(df[["lon", "lat"]].values, k=4, distance_metric="ARC", radius=6371.0088); w = w.symmetrize(); w.transform = "R"
z = (df.y - df.y.mean()) / df.y.std(ddof=1); lag = np.array([sum(w.weights[i][j] * z.values[nb] for j, nb in enumerate(w.neighbors[i])) for i in range(47)])
fig, axs = plt.subplots(1, 2, figsize=(W, 3.4), gridspec_kw={"width_ratios": [1, 1.25]})
ax = axs[0]
ax.scatter(z, lag, s=9, c="#2b6cb0", edgecolors="white", linewidths=0.3)
bb = np.polyfit(z, lag, 1); xs = np.linspace(z.min(), z.max(), 50); ax.plot(xs, np.polyval(bb, xs), color="0.2", lw=0.8)
ax.axhline(0, color="0.6", lw=0.5); ax.axvline(0, color="0.6", lw=0.5)
ax.set_xlabel("Standardized outcome"); ax.set_ylabel("Spatial lag of standardized outcome"); ax.set_title("A  Moran scatter plot (k = 4)", loc="left", fontsize=7)
ax = axs[1]
cmap = {"High-High": "#c53030", "Low-Low": "#2b6cb0", "n.s.": "#e2e8f0", "High-Low": "#ed8936", "Low-High": "#63b3ed"}
g["lc"] = g.lisa_cluster.map(cmap)
g.plot(color=g["lc"], linewidth=0.2, edgecolor="0.3", ax=ax); style_map(ax)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=cmap[k], label=k) for k in ["High-High", "Low-Low", "n.s."]], loc="lower right", fontsize=6, frameon=False)
ax.set_title("B  Local clusters of the outcome (LISA, p < 0.05)", loc="left", fontsize=7)
plt.tight_layout(); fig.savefig(FIG / "Figure_3.jpg", dpi=DPI, pil_kwargs={"quality": 95}); plt.close(fig)
from PIL import Image
for n in ("Figure_1.jpg", "Figure_2.jpg", "Figure_3.jpg"):
    im = Image.open(FIG / n); print(n, im.size, "dpi=", tuple(round(v) for v in im.info.get("dpi", (0, 0))), "width_cm=%.1f" % (im.size[0] / im.info["dpi"][0] * 2.54))
