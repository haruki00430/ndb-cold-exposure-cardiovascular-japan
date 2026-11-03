# -*- coding: utf-8 -*-
"""
R5_01: 元の人口あたり解析（07_percapita_reanalysis.py）の「行の並びずれ」の実演（自己完結・pickle/ポリゴン不要）。
  元手順: 空間重み行列 w は県ポリゴンの並び（gdf順）で作られ、アウトカム y は analysis_dataset.csv の並び（df順＝県名の文字列順）で渡される。
  → y と w の行が対応しない（空間的に無関係な県同士）まま Moran's I を計算していた。
重みは元スクリプトと同じ KNN(k=4, ユークリッド距離, 重心=EPSG:4326上の平面重心)、対称化・行基準化。実数は表示しない。
"""
import sys, ast, re
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
from libpysal.weights import KNN
from esda.moran import Moran
sys.stdout.reconfigure(encoding="utf-8")

src07 = (P.PROJ / "03_Analysis" / "scripts" / "07_percapita_reanalysis.py").read_text(encoding="utf-8")
POP = next(ast.literal_eval(n.value) for n in ast.parse(src07).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "POPULATION_2020")
df = pd.read_csv(P.PROJ / "data" / "interim" / "analysis_dataset.csv", encoding="utf-8")
df["rate"] = df.cvd_total_quantity / df.prefecture.map(POP) * 1e5
cent = pd.read_csv(P.DATA / "prefecture_centroids.csv", encoding="utf-8").sort_values("gdf_order")      # 元の gdf の並び
print(f"gdf の並びと df の並びが同じ位置にある県の数: {int((cent.prefecture.values == df.prefecture.values).sum())}/47")
w = KNN.from_array(cent[["cx4326", "cy4326"]].values, k=4); w = w.symmetrize(); w.transform = "R"
y_df = df.rate.values                                             # 元手順: df順のまま
y_gdf = df.set_index("prefecture").rate.reindex(cent.prefecture).values   # 正しい手順: gdf順に揃える
np.random.seed(0)
a = Moran(y_df, w, permutations=999); b = Moran(y_gdf, w, permutations=999)
print(f"元の手順 (y=df順, w=gdf順): Moran's I = {a.I:.4f}（原稿 0.0910 を再現: {abs(a.I-0.0910)<0.0006}）")
print(f"並びを揃えた手順 (y=gdf順, w=gdf順): Moran's I = {b.I:.4f}, p(置換) = {b.p_sim:.3f}")
