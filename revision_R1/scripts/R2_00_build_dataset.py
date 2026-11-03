# -*- coding: utf-8 -*-
"""
R2_00: 改訂用解析データセットの構築と独立検証（OPHRP-2026-0484 Revision）。

- 共変量（人口・高齢化率・医師密度・失業率・所得）は公式原表（Codex が保存した Raw_Official、SHA256付き）から
  本スクリプトで再抽出し、Codex のデータセット列と照合する（一致判定のみ print）。
- アウトカムは原NDB Excel（02_Data/raw、読み取りのみ）から再集計する:
    * all_units : 元解析と同一（5薬効分類・全単位合算）
    * tablet    : 単位が「錠」の行のみ（5薬効分類合計と分類別）
- 研究データ保護: 都道府県別の実数は一切 print しない。出力は revision_R1/data/ へ保存（git管理しない）。
- 入力は読み取り専用。既存ファイルは上書きしない（出力先が存在する場合は停止）。
"""
import sys, re, ast, unicodedata
from pathlib import Path
import numpy as np, pandas as pd, openpyxl

sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P

PROJ = P.PROJ
RAW = P.OFFICIAL
# (removed: unused workspace-specific path)
OUT = P.DATA
OUT.mkdir(parents=True, exist_ok=True)
OUTFILE = OUT / "analysis_dataset_R2.csv"
if OUTFILE.exists():
    raise SystemExit(f"既存ファイルがあるため停止: {OUTFILE}")

PREF = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
        "新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県",
        "奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県",
        "熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
EN = ["Hokkaido","Aomori","Iwate","Miyagi","Akita","Yamagata","Fukushima","Ibaraki","Tochigi","Gunma","Saitama","Chiba","Tokyo","Kanagawa",
      "Niigata","Toyama","Ishikawa","Fukui","Yamanashi","Nagano","Gifu","Shizuoka","Aichi","Mie","Shiga","Kyoto","Osaka","Hyogo",
      "Nara","Wakayama","Tottori","Shimane","Okayama","Hiroshima","Yamaguchi","Tokushima","Kagawa","Ehime","Kochi","Fukuoka","Saga","Nagasaki",
      "Kumamoto","Oita","Miyazaki","Kagoshima","Okinawa"]
assert len(PREF) == 47 == len(EN)
SHORT = {p: (p if p == "北海道" else p[:-1]) for p in PREF}
BY_SHORT = {v: k for k, v in SHORT.items()}

def norm(s): return unicodedata.normalize("NFKC", str(s)).replace("\u3000", "").replace(" ", "").strip()
def pref_from(s):
    s = norm(s)
    if s in PREF: return s
    return BY_SHORT.get(s)

def sheet_rows(fn, sheet):
    wb = openpyxl.load_workbook(RAW / fn, read_only=True, data_only=True)
    return [list(r) for r in wb[sheet].iter_rows(values_only=True)]

res = {}
# ---------------- 人口（2023年10月1日, 第2表, 千人→人）
rows = sheet_rows("population2023.xlsx", "第2表")
pop = {}
for r in rows:
    p = pref_from(r[2]) if len(r) > 2 and r[2] else None
    if p and isinstance(r[4], (int, float)): pop[p] = r[4] * 1000
# ---------------- 65歳以上（第3表）
rows = sheet_rows("age2023.xlsx", "第3表")
a65 = {}
for r in rows:
    p = pref_from(r[2]) if len(r) > 2 and r[2] else None
    if p and isinstance(r[6], (int, float)): a65[p] = r[6] * 1000
aging = {p: a65[p] / pop[p] * 100 for p in PREF}
# ---------------- 医師密度（統計表10-1: 医師・医療施設の従事者・人口10万対）
rows = sheet_rows("physicians2022.xlsx", "統計表10-1")
phys = {}
for r in rows:
    p = pref_from(r[3]) if len(r) > 3 and r[3] else None
    if p and isinstance(r[6], (int, float)): phys[p] = float(r[6])
# ---------------- 完全失業率（時系列表 第6表, 2023年）
rows = sheet_rows("unemployment_annual.xlsx", "時系列表 第６表")
hdr = None
for i, r in enumerate(rows):
    names = [pref_from(x) for x in r if x]
    if sum(1 for n in names if n) >= 40: hdr = (i, r); break
unemp = {}
if hdr:
    i, hr = hdr
    for r in rows[i + 1:]:
        if r[1] is not None and str(r[1]).strip().replace(".0", "") == "2023":
            for ci, x in enumerate(hr):
                p = pref_from(x) if x else None
                if p and isinstance(r[ci], (int, float)): unemp[p] = float(r[ci])
# ---------------- 県民所得（FY2022 = 令和4年度, 千円→万円）
rows = sheet_rows("income2022.xlsx", "実数")
col = None
for r in rows[:12]:
    for ci, x in enumerate(r):
        if x and norm(x) == "令和4年度": col = ci
inc = {}
if col is not None:
    for r in rows:
        p = pref_from(r[1]) if len(r) > 1 and r[1] else None
        if p and len(r) > col and isinstance(r[col], (int, float)): inc[p] = r[col] / 10
print(f"[原表再抽出] pop={len(pop)} age65={len(a65)} phys={len(phys)} unemp={len(unemp)} income(col={col})={len(inc)}")

cx = pd.read_csv(RAW / "Prefecture_Analysis_Dataset.csv", encoding="utf-8-sig").set_index("prefecture")
def cmp(name, mine, theirs_col, tol=1e-6):
    a = pd.Series(mine).reindex(PREF); b = cx[theirs_col].reindex(PREF)
    ok = bool(a.notna().all() and np.allclose(a.values, b.values, rtol=1e-9, atol=tol))
    print(f"  照合 {name:34s} 47県一致={ok}" + ("" if ok else f"  (最大差={np.nanmax(np.abs(a.values-b.values)):.3g})"))
    return ok
checks = [cmp("人口 2023-10-01", pop, "population_20231001", 0.5),
          cmp("高齢化率 2023", aging, "aging_pct_2023", 1e-6),
          cmp("医師密度 2022（医療施設従事）", phys, "physicians_medical_facility_per100k_2022", 1e-6),
          cmp("完全失業率 2023（モデル推計）", unemp, "unemployment_pct_2023", 1e-6),
          cmp("所得 FY2022（万円）", inc, "income_10000yen_FY2022", 1e-6)]
print("共変量の独立再抽出が Codex データセットと全て一致:", all(checks))

# ---------------- アウトカム再集計（原NDB Excel）
ndb_dir = P.NDB_DIR
xl = [f for f in ndb_dir.iterdir() if "都道府県" in f.name and "院外" in f.name and f.suffix == ".xlsx"]
assert len(xl) == 1
raw = pd.read_excel(xl[0], header=None, engine="openpyxl")
pref_cols = {}
for ridx in [3, 2, 4]:
    pc = {}
    for ci in range(8, raw.shape[1]):
        v = str(raw.iloc[ridx, ci]).strip()
        if v in PREF: pc[v] = ci
    if len(pc) >= 40: pref_cols = pc; break
assert len(pref_cols) == 47
data = raw.iloc[4:].copy(); data.columns = range(raw.shape[1])
data[0] = data[0].astype(str).replace("nan", np.nan).ffill()
CODES = {"214": "antihypertensive", "217": "vasodilator", "218": "antihyperlipidemic", "219": "other_cv", "333": "anticoagulant"}
sub = data[data[0].isin(CODES)].copy()
sub["unit"] = sub[4].astype(str).str.strip()
num = sub[[ci for ci in pref_cols.values()]].apply(pd.to_numeric, errors="coerce")
num.columns = list(pref_cols.keys())
out = pd.DataFrame(index=PREF)
out["qty_all_units"] = num.sum().reindex(PREF).values
tab = sub["unit"] == "錠"
out["qty_tablet"] = num[tab.values].sum().reindex(PREF).values
for code, nm in CODES.items():
    m = (sub[0] == code).values
    out[f"qty_all_{nm}"] = num[m].sum().reindex(PREF).values
    out[f"qty_tab_{nm}"] = num[m & tab.values].sum().reindex(PREF).values
# マスク（非数値）セル数: 錠・全単位
out["masked_cells_tablet_rows"] = num[tab.values].isna().sum().reindex(PREF).values
print(f"[アウトカム] 対象行={len(sub)}, 錠の行={int(tab.sum())} ({tab.mean()*100:.1f}%), 全国錠数量割合={out.qty_tablet.sum()/out.qty_all_units.sum()*100:.2f}%")
print(f"  マスク/非数値セル(錠の行)={int(out.masked_cells_tablet_rows.sum())} / {int(tab.sum())*47}")
orig = pd.read_csv(PROJ / "data" / "interim" / "analysis_dataset.csv", encoding="utf-8").set_index("prefecture")
print("  元解析の cvd_total_quantity と再集計(全単位)が一致:", bool(np.allclose(out.qty_all_units.values, orig["cvd_total_quantity"].reindex(PREF).values)))

# ---------------- 組み立て
df = pd.DataFrame({"prefecture": PREF, "prefecture_en": EN, "pref_code": range(1, 48)})
df["population_2023"] = [pop[p] for p in PREF]
df["aging_pct_2023"] = [aging[p] for p in PREF]
df["physicians_per100k_2022"] = [phys[p] for p in PREF]
df["unemployment_pct_2023"] = [unemp[p] for p in PREF]
df["income_10000yen_FY2022"] = [inc[p] for p in PREF]
for c in out.columns: df[c] = out[c].values
# 元データの曝露・気温指標（2016-2020, 60か月）と元共変量
o = orig.reindex(PREF)
for c in ["Cold_months_ratio", "Mean_Temp_avg", "Temp_range_annual", "Winter_temp_avg", "Temp_std", "physicians_per_100k", "unemployment_rate", "elderly_ratio", "income_per_capita"]:
    df["orig_" + c] = o[c].values
df["orig_cvd_total_quantity"] = o["cvd_total_quantity"].values
df["orig_population_2020"] = [ast.literal_eval(re.search(r"POPULATION_2020 = (\{.*?\})", (PROJ / "03_Analysis/scripts/07_percapita_reanalysis.py").read_text(encoding="utf-8"), re.S).group(1))[p] for p in PREF]
wl = pd.read_csv(PROJ / "data" / "interim" / "weather_monthly_long.csv", encoding="utf-8")
cnt = wl.assign(c=wl.Mean_Temp < 5.0).groupby("prefecture").agg(n_months=("Mean_Temp", "count"), n_cold_months_lt5=("c", "sum"), station=("station", "first"))
for c in cnt.columns: df[c] = cnt[c].reindex(PREF).values
# 補足交絡（Codex 編纂の公式資料由来・未独立検証 → 感度分析のみに使用）
for c in ["smoking_pct_age_sex_standardized_checkup2022", "BMI_standardized_checkup2022", "SBP_standardized_checkup2022",
          "SBP_ge140_pct_standardized_checkup2022", "sodium_g_day_male_age_adjusted_NHNS2016", "sodium_g_day_female_age_adjusted_NHNS2016",
          "outcome_primary_tablets_per100k", "cold_ratio_FY2023", "cold_ratio5_FY2023", "latitude", "longitude"]:
    df["cx_" + c] = cx[c].reindex(PREF).values
df.to_csv(OUTFILE, index=False, encoding="utf-8")
print(f"保存: {OUTFILE.name} shape={df.shape}")
