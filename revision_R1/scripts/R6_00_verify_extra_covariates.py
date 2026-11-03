# -*- coding: utf-8 -*-
"""
R6_00: 追加交絡（BMI・喫煙・収縮期血圧・SBP≥140の割合・食塩）を、公式の原表から独立に再抽出して、解析用データセットの値と照合する。
- 特定健診（FY2022、NDBオープンデータ）: smoking_q8.xlsx（質問8）、checkup_means.xlsx（平均値）、sbp_distribution.xlsx（収縮期血圧の分布）
  標準化: 全都道府県の質問8回答者を合わせた14の性×年齢階級（40-74歳）の人数を重みとする直接法（Codexの記載と同じ方法）。
  本スクリプトは、方法の妥当性ではなく、①列の対応（見出し）②算術 ③転記 が原表と一致するかを検証する。
- 食塩: 国民健康・栄養調査2016 表55（PDF）の本文から男女別・年齢調整平均値を直接読み取る。
出力は一致判定と最大差のみ（都道府県別の実数は表示しない）。
"""
import sys, re
from pathlib import Path
import numpy as np, pandas as pd, openpyxl, fitz
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
sys.stdout.reconfigure(encoding="utf-8")

OFF = P.OFFICIAL
ds = pd.read_csv(OFF / "Prefecture_Analysis_Dataset.csv", encoding="utf-8-sig").set_index("prefecture")
PREF = list(ds.index)

def sheet(fn):
    wb = openpyxl.load_workbook(OFF / fn, read_only=True, data_only=True)
    return [list(r) for r in next(iter(wb.worksheets)).iter_rows(values_only=True)]

COLS = list(range(2, 9)) + list(range(10, 17))     # 男40-44〜70-74、女40-44〜70-74（各「中計」列を除く）
def check_header(rows, name):
    sex = rows[2]; age = rows[3]
    ages7 = ["40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65～69歳", "70～74歳"]
    ok_age = all(str(age[c]).strip() == a for c, a in zip(COLS, ages7 + ages7))
    ok_tot = str(age[9]).strip() == "中計" and str(age[17]).strip() == "中計"
    ok_sex = str(sex[2]).strip() == "男" and any(str(x).strip() == "女" for x in sex[10:12])
    print(f"  {name}: 見出しの対応（年齢階級・中計列・性別）一致 = {ok_age and ok_tot and ok_sex}")
    return ok_age and ok_tot and ok_sex

res = {}
# ---- 喫煙（質問8）
r = sheet("smoking_q8.xlsx"); h1 = check_header(r, "smoking_q8")
counts = {}; cur = None
for row in r[5:]:
    if row[0]: cur = row[0]
    if cur in PREF and row[1] in ("はい", "いいえ"): counts.setdefault(cur, {})[row[1]] = np.array([float(row[j]) for j in COLS])
assert set(counts) == set(PREF)
standard = sum(counts[p]["はい"] + counts[p]["いいえ"] for p in PREF); w = standard / standard.sum()
smoke = {p: 100 * float((w * counts[p]["はい"] / (counts[p]["はい"] + counts[p]["いいえ"])).sum()) for p in PREF}
# ---- BMI・SBP平均
r = sheet("checkup_means.xlsx"); h2 = check_header(r, "checkup_means")
bmi, sbp = {}, {}; cur = None
for row in r[5:]:
    if row[0]: cur = row[0]
    if cur in PREF and row[1] == "BMI": bmi[cur] = float(sum(wi * float(row[j]) for wi, j in zip(w, COLS)))
    if cur in PREF and row[1] == "収縮期血圧": sbp[cur] = float(sum(wi * float(row[j]) for wi, j in zip(w, COLS)))
# ---- SBP≥140 の割合
r = sheet("sbp_distribution.xlsx"); h3 = check_header(r, "sbp_distribution")
bp = {}; cur = None
for row in r[5:]:
    if row[0]: cur = row[0]
    if cur in PREF and row[1] and ("以上" in str(row[1]) or "未満" in str(row[1])): bp.setdefault(cur, []).append((str(row[1]), np.array([float(row[j]) for j in COLS])))
ge140 = {}
for p, arr in bp.items():
    assert len(arr) == 6, (p, len(arr))
    den = sum(v for _, v in arr); num = sum(v for lab, v in arr if lab.startswith(("180", "160", "140")))
    ge140[p] = 100 * float((w * num / den).sum())
# ---- 食塩（PDF 表55）
doc = fitz.open(OFF / "nhns2016_pref.pdf"); toks = []
for pg in doc:
    t = pg.get_text()
    if "第55" in t.replace(" ", "") or "食塩摂取量の平均値" in t:
        toks = [x.strip() for x in t.split("\n") if x.strip()]; break
salt = {}
i = 0
while i < len(toks):
    if toks[i] in PREF:
        nums = []; j = i + 1
        while j < len(toks) and toks[j] not in PREF and toks[j] != "全国" and len(nums) < 8:
            nums.append(toks[j]); j += 1
        if len(nums) == 8:
            def f(x):
                try: return float(x)
                except ValueError: return np.nan
            salt[toks[i]] = (f(nums[1]), f(nums[5]))
        else: salt[toks[i]] = (np.nan, np.nan)
        i = j
    else: i += 1
print(f"  食塩PDF: 読み取れた県数={len(salt)}, 欠損（熊本県など）={[p for p, v in salt.items() if np.isnan(v[0])]}")

def cmp(label, mine, col, tol=1e-9):
    a = pd.Series(mine).reindex(PREF); b = ds[col].reindex(PREF)
    both = a.notna() & b.notna(); same_na = (a.isna() == b.isna()).all()
    ok = bool(same_na and np.allclose(a[both].values, b[both].values, rtol=0, atol=tol))
    d = float(np.nanmax(np.abs(a[both].values - b[both].values))) if both.any() else float("nan")
    print(f"  照合 {label:42s} 一致={ok}  最大差={d:.2e}  比較県数={int(both.sum())}")
    return ok
oks = [cmp("喫煙（年齢・性別標準化 %）", smoke, "smoking_pct_age_sex_standardized_checkup2022"),
       cmp("BMI（標準化）", bmi, "BMI_standardized_checkup2022"),
       cmp("収縮期血圧（標準化 mmHg）", sbp, "SBP_standardized_checkup2022"),
       cmp("収縮期血圧≥140の割合（標準化 %）", ge140, "SBP_ge140_pct_standardized_checkup2022"),
       cmp("食塩・男性（年齢調整 g/日）", {p: v[0] for p, v in salt.items()}, "sodium_g_day_male_age_adjusted_NHNS2016", 1e-6),
       cmp("食塩・女性（年齢調整 g/日）", {p: v[1] for p, v in salt.items()}, "sodium_g_day_female_age_adjusted_NHNS2016", 1e-6)]
print("\n列の対応の検証:", h1 and h2 and h3, "| 5変数（6列）がすべて原表と一致:", all(oks))
