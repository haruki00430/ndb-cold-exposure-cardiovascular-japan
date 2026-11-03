# -*- coding: utf-8 -*-
"""
R3_00: NDB 性年齢別表（外来・院外・内服、全国）から、5薬効分類・単位「錠」の性×年齢階級別の全国数量を集計する。
間接法による年齢・性別標準化（期待値の算出）の分子側データ。02_Data/raw は読み取りのみ。
出力は revision_R1/data/national_agesex_tablets.csv。標準出力は一致判定と集計割合のみ。
"""
import sys, os
from pathlib import Path
import numpy as np, pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P
OUT = P.DATA / "national_agesex_tablets.csv"
base = P.NDB_DIR
fn_age = [f for f in os.listdir(base) if "外来（院外）" in f and "性年齢別" in f and "医科" not in f][0]
fn_pref = [f for f in os.listdir(base) if "外来（院外）" in f and "都道府県別" in f][0]

raw = pd.read_excel(base / fn_age, header=None, engine="openpyxl")
hdr = next(i for i in range(8) if "0～4歳" in [str(x).strip() for x in raw.iloc[i].tolist()])
sex_row = raw.iloc[hdr - 1].tolist(); age_row = [str(x).strip() for x in raw.iloc[hdr].tolist()]
ages = [(c, a) for c, a in enumerate(age_row) if a.endswith("歳") or a.endswith("歳以上")]
assert len(ages) == 42, len(ages)
male_cols = [c for c, a in ages[:21]]; female_cols = [c for c, a in ages[21:]]
labels = [a for c, a in ages[:21]]
assert [a for c, a in ages[21:]] == labels, "男女の年齢階級が一致しない"
print(f"ファイル: {fn_age} / 見出し行={hdr} / 年齢階級={len(labels)} / 総計列=8")

data = raw.iloc[hdr + 1:].copy(); data.columns = range(raw.shape[1])
data[0] = data[0].astype(str).replace("nan", np.nan).ffill()
CODES = ["214", "217", "218", "219", "333"]
sub = data[data[0].isin(CODES)].copy()
sub["unit"] = sub[4].astype(str).str.strip()
num = sub.apply(pd.to_numeric, errors="coerce")
tab = (sub["unit"] == "錠").values
print(f"対象行(5薬効分類)={len(sub)}, うち錠={int(tab.sum())}")

rows = []
for code in CODES + ["all5"]:
    m = tab & ((sub[0] == code).values if code != "all5" else True)
    for sex, cols in (("M", male_cols), ("F", female_cols)):
        for c, lab in zip(cols, labels):
            rows.append(dict(category=code, sex=sex, age_group=lab, tablets=float(num.loc[m, c].sum(skipna=True))))
df = pd.DataFrame(rows)
OUT.parent.mkdir(exist_ok=True)
df.to_csv(OUT, index=False, encoding="utf-8")

# ---- 整合性チェック（真偽のみ）
a5 = df[df.category == "all5"]
tot_agesex = a5.tablets.sum()
tot_col = num.loc[tab, 8].sum(skipna=True)
print(f"性年齢別の合計 ≈ 総計列（錠）の相対差 = {abs(tot_agesex - tot_col) / tot_col:.4%}")
pref = pd.read_excel(base / fn_pref, header=None, engine="openpyxl")
pdt = pref.iloc[4:].copy(); pdt.columns = range(pref.shape[1]); pdt[0] = pdt[0].astype(str).replace("nan", np.nan).ffill()
ps = pdt[pdt[0].isin(CODES)].copy(); ps["unit"] = ps[4].astype(str).str.strip()
PREF47 = 47
pcols = [c for c in range(8, pref.shape[1]) if str(pref.iloc[3, c]).strip().endswith(("県", "府", "都", "道"))]
pnum = ps.loc[ps.unit == "錠", pcols].apply(pd.to_numeric, errors="coerce")
tot_pref = float(pnum.sum().sum())
print(f"都道府県列={len(pcols)}; 都道府県別表の錠合計と性年齢別表の錠合計の相対差 = {abs(tot_pref - tot_agesex) / tot_agesex:.4%}")
m_share = a5[a5.sex == "M"].tablets.sum() / tot_agesex
old = a5[a5.age_group.isin([l for l in labels if any(l.startswith(x) for x in ("65", "70", "75", "80", "85", "90", "95", "100"))])].tablets.sum() / tot_agesex
print(f"全国の錠数量に占める 男性={m_share:.1%}, 65歳以上={old:.1%}")
print("保存:", OUT.name, df.shape)
