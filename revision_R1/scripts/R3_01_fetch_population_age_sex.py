# -*- coding: utf-8 -*-
"""
R3_01: e-Stat から都道府県×年齢5歳階級×男女別人口（2023年10月1日、総人口）を取得し、既存の人口表（第2表）と照合する。
統計表ID 0004012968（人口推計 各年10月1日現在人口 令和2年国勢調査基準 参考表）。公開統計のみ取得。キー・URLは出力しない。
"""
import sys
from pathlib import Path
import pandas as pd, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estat_client as E

sys.stdout.reconfigure(encoding="utf-8")
R1 = E.R1
OUT = R1 / "data" / "pop2023_age5_sex.csv"

root = E.call("getStatsData", statsDataId="0004012968", limit=100000)
vals = root["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
meta = root["STATISTICAL_DATA"]["CLASS_INF"]["CLASS_OBJ"]
cl = {o["@id"]: {c["@code"]: c["@name"] for c in ([o["CLASS"]] if isinstance(o["CLASS"], dict) else o["CLASS"])} for o in meta}
unit = {v.get("@unit") for v in vals}
rows = []
for v in vals:
    s = v["$"]
    try: x = float(s)
    except ValueError: x = np.nan
    rows.append(dict(area_code=v["@area"], area=cl["area"][v["@area"]], age=cl["cat01"][v["@cat01"]], sex=cl["cat02"][v["@cat02"]], population=x))
df = pd.DataFrame(rows)
print(f"取得レコード={len(df)}, 単位={unit}, 欠損値={int(df.population.isna().sum())}")
print(f"地域={df.area.nunique()}（全国含む）, 年齢区分={df.age.nunique()}, 性別={df.sex.nunique()}")

# 単位: 千人の可能性があるため、既存の人口表（千人×1000）で判定
base = pd.read_csv(R1 / "data" / "analysis_dataset_R2.csv", encoding="utf-8").set_index("prefecture")
tot = df[(df.age == "総数") & (df.sex == "男女計") & (df.area != "全国")].set_index("area").population
ratio = (base.population_2023 / tot.reindex(base.index)).median()
mult = 1000 if abs(ratio - 1000) < 100 else (1 if abs(ratio - 1) < 0.1 else None)
print(f"既存人口表(第2表)/取得値 の比の中央値 = {ratio:.1f} → 倍率 {mult}")
assert mult is not None
df["population"] = df.population * mult

# ---- 照合（真偽のみ）
t = df[(df.age == "総数") & (df.sex == "男女計") & (df.area != "全国")].set_index("area").population.reindex(base.index)
print("県別総人口が既存人口表（千人丸め）と一致（差≤500人）:", bool(((t - base.population_2023).abs() <= 500).all()))
age_only = df[(df.age != "総数") & (df.area != "全国")]
for sx in ("男", "女", "男女計"):
    s = age_only[age_only.sex == sx].groupby("area").population.sum().reindex(base.index)
    t2 = df[(df.age == "総数") & (df.sex == sx) & (df.area != "全国")].set_index("area").population.reindex(base.index)
    print(f"  年齢階級の合計＝総数 ({sx}): 最大相対差 {((s - t2).abs() / t2).max():.4%}")
mf = df[(df.age != "総数") & (df.sex == "男女計")].set_index(["area", "age"]).population
m = df[(df.age != "総数") & (df.sex == "男")].set_index(["area", "age"]).population
fm = df[(df.age != "総数") & (df.sex == "女")].set_index(["area", "age"]).population
print("男＋女＝男女計（全地域・全年齢区分）:", bool(np.allclose((m + fm).reindex(mf.index), mf, atol=1500)))   # 千人丸めの許容
OUT.parent.mkdir(exist_ok=True)
df.to_csv(OUT, index=False, encoding="utf-8")
print("保存:", OUT.name, df.shape)
