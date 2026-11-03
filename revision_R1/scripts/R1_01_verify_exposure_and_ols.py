# -*- coding: utf-8 -*-
"""
元解析（data/interim/*）の独立再検証。
研究データ保護ルールに従い、都道府県別の実数は一切 print しない。
出力するのは (1) 集計値（Table 1相当の平均/SD/範囲）、(2) モデル要約、(3) 一致/不一致の判定のみ。
入力は読み取り専用。何も上書きしない。
"""
import sys, re, ast, json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import docx

sys.stdout.reconfigure(encoding="utf-8")
import pathlib as _pl; sys.path.insert(0, str(_pl.Path(__file__).resolve().parent)); import paths as P

PROJ = P.PROJ
INT = PROJ / "data" / "interim"
MS = P.SUB_V4 / "Manuscript_PHRP_v4.docx"

# 07 スクリプトから人口辞書だけを ast で取り出す（コードは実行しない）
src07 = (PROJ / "03_Analysis" / "scripts" / "07_percapita_reanalysis.py").read_text(encoding="utf-8")
tree = ast.parse(src07)
POP = None
for node in tree.body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "POPULATION_2020":
        POP = ast.literal_eval(node.value)
assert POP and len(POP) == 47

df = pd.read_csv(INT / "analysis_dataset.csv", encoding="utf-8")
wp = pd.read_csv(INT / "weather_data_prefecture.csv", encoding="utf-8")
wl = pd.read_csv(INT / "weather_monthly_long.csv", encoding="utf-8")
df["population"] = df["prefecture"].map(POP)
df["rate"] = df["cvd_total_quantity"] / df["population"] * 1e5

print("=" * 70)
print("A. 寒冷月比率の定義の検証（weather_monthly_long.csv からの再計算）")
print("=" * 70)
ym = wl[["year", "month"]].drop_duplicates()
print(f"月次データ期間: {wl.year.min()}/{wl.month[wl.year==wl.year.min()].min()} - {wl.year.max()}/{wl.month[wl.year==wl.year.max()].max()}, 異なる年月={len(ym)}")
per_pref_n = wl.groupby("prefecture")["Mean_Temp"].count()
print(f"都道府県数={wl.prefecture.nunique()}, 1県あたり有効月数: min={per_pref_n.min()}, max={per_pref_n.max()}, NaN気温={int(wl.Mean_Temp.isna().sum())}")
stations = wl[["prefecture", "station"]].drop_duplicates()
print("観測所（都道府県庁所在地以外を◆）:")
CAP = {"北海道":"札幌","青森県":"青森","岩手県":"盛岡","宮城県":"仙台","秋田県":"秋田","山形県":"山形","福島県":"福島","茨城県":"水戸","栃木県":"宇都宮","群馬県":"前橋","埼玉県":"さいたま","千葉県":"千葉","東京都":"東京","神奈川県":"横浜","新潟県":"新潟","富山県":"富山","石川県":"金沢","福井県":"福井","山梨県":"甲府","長野県":"長野","岐阜県":"岐阜","静岡県":"静岡","愛知県":"名古屋","三重県":"津","滋賀県":"大津","京都府":"京都","大阪府":"大阪","兵庫県":"神戸","奈良県":"奈良","和歌山県":"和歌山","鳥取県":"鳥取","島根県":"松江","岡山県":"岡山","広島県":"広島","山口県":"山口","徳島県":"徳島","香川県":"高松","愛媛県":"松山","高知県":"高知","福岡県":"福岡","佐賀県":"佐賀","長崎県":"長崎","熊本県":"熊本","大分県":"大分","宮崎県":"宮崎","鹿児島県":"鹿児島","沖縄県":"那覇"}
non_cap = [(r.prefecture, r.station) for r in stations.itertuples() if CAP[r.prefecture] != r.station]
print("  非庁所在地の観測所:", non_cap)

for thr in (5.0, 10.0):
    r = wl.groupby("prefecture")["Mean_Temp"].apply(lambda s: (s < thr).sum() / len(s))
    n = per_pref_n.iloc[0]
    integer_ok = bool(np.allclose(r.values * n, np.round(r.values * n)))
    print(f"  閾値<{thr:>4.1f}°C 再計算: mean={r.mean():.3f}, SD={r.std():.3f}, min={r.min():.3f}, max={r.max():.4f}  (最大月数={r.max()*n:.1f}/{n}) 1/{n}刻み={integer_ok}")

r5 = wl.groupby("prefecture")["Mean_Temp"].apply(lambda s: (s < 5.0).sum() / len(s))
r10 = wl.groupby("prefecture")["Mean_Temp"].apply(lambda s: (s < 10.0).sum() / len(s))
w_idx = wp.set_index("prefecture")["Cold_months_ratio"]
a_idx = df.set_index("prefecture")["Cold_months_ratio"]
print(f"  weather_data_prefecture.csv の Cold_months_ratio と一致: 5°C再計算 max|diff|={np.abs(w_idx - r5.reindex(w_idx.index)).max():.2e} / 10°C再計算 max|diff|={np.abs(w_idx - r10.reindex(w_idx.index)).max():.2e}")
print(f"  analysis_dataset.csv の Cold_months_ratio と一致: 5°C max|diff|={np.abs(a_idx - r5.reindex(a_idx.index)).max():.2e}")
print(f"  → 解析に使われた閾値 = {'5°C' if np.abs(a_idx - r5.reindex(a_idx.index)).max() < 1e-9 else ('10°C' if np.abs(a_idx - r10.reindex(a_idx.index)).max() < 1e-9 else '不明')}")
print(f"  10°C定義で『0.20超』となる県数={int((r10 > 0.20).sum())}/47, 5°C定義で『0.20超』となる県数={int((r5 > 0.20).sum())}/47")
# 0.20超の県が「4か月以上」に相当するか（5°C, 60か月）
n = per_pref_n.iloc[0]
print(f"  5°C定義: 比率0.20 = 年平均 {0.20*12:.1f} か月/年 (=60か月中{0.20*n:.0f}か月). 比率0.33が年4か月に相当")

print()
print("=" * 70)
print("B. 元回帰の再現（07_percapita_reanalysis.py と同じ式、実数は非表示）")
print("=" * 70)
ses = ["physicians_per_100k", "unemployment_rate", "elderly_ratio", "income_per_capita"]
tv_all = ["Mean_Temp_avg", "Temp_range_annual", "Winter_temp_avg", "Temp_std", "Cold_months_ratio"]
print(f"アウトカム rate: mean={df.rate.mean():,.0f} SD={df.rate.std():,.0f} min={df.rate.min():,.0f} max={df.rate.max():,.0f}  (原稿 17,521,396 ± 2,607,830 / 13,864,815–25,622,603)")
print(f"寒冷月比率: mean={df.Cold_months_ratio.mean():.3f} SD={df.Cold_months_ratio.std():.3f} min={df.Cold_months_ratio.min():.3f} max={df.Cold_months_ratio.max():.3f}  (原稿 0.09 ± 0.11 / 0–0.38)")
uni = {}
for tv in tv_all:
    m = sm.OLS(df.rate, sm.add_constant(df[[tv]])).fit()
    uni[tv] = (m.params[tv], m.pvalues[tv], m.rsquared)
    print(f"  単変量 {tv:18s}: beta={m.params[tv]:>14,.0f} p={m.pvalues[tv]:.4f} R2={m.rsquared:.4f}")
multi = {}
for tv in tv_all:
    m = sm.OLS(df.rate, sm.add_constant(df[[tv] + ses])).fit()
    multi[tv] = m
best = max(multi, key=lambda k: multi[k].rsquared_adj)
mb = multi[best]
print(f"  adj R2 最大の多変量モデル: {best} (adj R2={mb.rsquared_adj:.4f}, R2={mb.rsquared:.4f}, F={mb.fvalue:.2f})")
print("  --- 全5指標の多変量モデル（感度分析として未報告だった結果）---")
for tv in tv_all:
    m = multi[tv]
    print(f"    {tv:18s}: beta={m.params[tv]:>14,.0f} p={m.pvalues[tv]:.4f} adjR2={m.rsquared_adj:.4f}")
c = multi["Cold_months_ratio"]
print(f"  原稿との照合: beta(Cold)={c.params['Cold_months_ratio']:,.0f} (原稿10,450,255) / R2={c.rsquared:.4f} (0.667) / adjR2={c.rsquared_adj:.4f} (0.626)")
print(f"  共変量: unemployment beta={c.params['unemployment_rate']:,.0f} p={c.pvalues['unemployment_rate']:.4f} (原稿 +1,300,753 / 0.025); elderly beta={c.params['elderly_ratio']:,.0f} (原稿 +499,769)")

# 5°C を 10°C に置換した場合（原稿の文言どおりの定義だったら）の影響
df["Cold10"] = df.prefecture.map(r10)
m10 = sm.OLS(df.rate, sm.add_constant(df[["Cold10"] + ses])).fit()
print(f"  [参考] 同じ式で曝露を『<10°C』比率に置換: beta={m10.params['Cold10']:,.0f} p={m10.pvalues['Cold10']:.4f} adjR2={m10.rsquared_adj:.4f}")

print()
print("=" * 70)
print("C. 原稿 Table 2（相関行列）と実データ再計算の照合")
print("=" * 70)
d = docx.Document(MS)
t2 = d.tables[1]
hdr = [c.text.strip() for c in t2.rows[0].cells]
printed = {}
for row in t2.rows[1:]:
    cells = [c.text.strip() for c in row.cells]
    name = cells[0]
    vals = []
    for x in cells[1:]:
        mm = re.search(r"-?\d+\.\d+", x.replace("−", "-"))
        vals.append(float(mm.group()) if mm else np.nan)
    printed[name] = vals
names_ms = list(printed.keys())
print("Table 2 行:", names_ms)
colmap = {"CVD prescription rate": "rate", "Cold month ratio": "Cold_months_ratio", "Mean annual temperature": "Mean_Temp_avg",
          "Physicians per 100,000": "physicians_per_100k", "Unemployment rate": "unemployment_rate", "Aging rate": "elderly_ratio",
          "Per capita income": "income_per_capita"}
order = [colmap.get(n) for n in names_ms]
print("対応付け:", order)
if all(order):
    real = df[order].corr().values
    pr = np.array([printed[n] for n in names_ms])
    diff = np.abs(real - pr)
    iu = np.triu_indices(len(order), 1)
    bad = [(names_ms[i], names_ms[j], round(float(pr[i, j]), 3), round(float(real[i, j]), 3)) for i, j in zip(*iu) if diff[i, j] > 0.0006]
    print(f"相関係数 {len(iu[0])} セル中、|印刷値-再計算値|>0.0006 のセル数 = {len(bad)}")
    for b in bad: print("   不一致:", b)
    # R2 from printed vs real correlation matrix
    def r2_from_corr(R):
        rxx = R[1:, 1:]; rxy = R[1:, 0]
        return float(rxy @ np.linalg.solve(rxx, rxy))
    # 原稿のTable2には温度指標2種のみ、回帰の説明変数5つ(Cold, Physicians, Unemp, Aging, Income)に該当する部分を使う
    sel = [names_ms.index(n) for n in ["CVD prescription rate", "Cold month ratio", "Physicians per 100,000", "Unemployment rate", "Aging rate", "Per capita income"] if n in names_ms]
    print(f"相関行列からのR2: 印刷値ベース={r2_from_corr(pr[np.ix_(sel, sel)]):.4f} / 実データ再計算ベース={r2_from_corr(real[np.ix_(sel, sel)]):.4f} (OLS直接のR2={c.rsquared:.4f})")

print()
print("=" * 70)
print("D. 影響点（Cook's D, 4/n）と感度分析（主モデル: Cold5°C + 4共変量）")
print("=" * 70)
infl = c.get_influence()
cd = pd.Series(infl.cooks_distance[0], index=df.prefecture)
th = 4 / len(df)
over = cd[cd > th].sort_values(ascending=False)
print(f"4/n={th:.3f} 超: {len(over)}県 -> {list(over.index)} ; 最大Cook's D={cd.max():.3f} ({cd.idxmax()})")
def fit_excl(excl, label):
    s = df[~df.prefecture.isin(excl)]
    m = sm.OLS(s.rate, sm.add_constant(s[["Cold_months_ratio"] + ses])).fit(cov_type="HC3")
    print(f"  {label:42s} n={len(s)}  beta={m.params['Cold_months_ratio']:>12,.0f}  HC3 p={m.pvalues['Cold_months_ratio']:.4f}")
m_hc3 = sm.OLS(df.rate, sm.add_constant(df[["Cold_months_ratio"] + ses])).fit(cov_type="HC3")
print(f"  {'全47県 (HC3)':42s} n=47  beta={m_hc3.params['Cold_months_ratio']:>12,.0f}  HC3 p={m_hc3.pvalues['Cold_months_ratio']:.4f}")
fit_excl(list(over.index), "Cook's D>4/n の県を除外")
fit_excl([cd.idxmax()], "最大Cook's D の県のみ除外")
fit_excl(["北海道", "沖縄県"], "北海道・沖縄を除外")
loo = []
for p in df.prefecture:
    s = df[df.prefecture != p]
    m = sm.OLS(s.rate, sm.add_constant(s[["Cold_months_ratio"] + ses])).fit(cov_type="HC3")
    loo.append((p, m.params["Cold_months_ratio"], m.pvalues["Cold_months_ratio"]))
lp = np.array([x[2] for x in loo]); lb = np.array([x[1] for x in loo])
print(f"  leave-one-out 47回: p最大={lp.max():.4f}, 全てp<0.05={bool((lp<0.05).all())}, beta範囲={lb.min():,.0f}〜{lb.max():,.0f}")
# 事前の定義ではない 4/n 超過の件数
print()
print("=" * 70)
print("E. 薬効分類別アウトカム（元データにある5分類）× Cold5°C 主モデル（人口10万対）")
print("=" * 70)
cats = ["血圧降下剤", "血管拡張剤", "高脂血症用剤", "その他循環器官用薬", "血液凝固阻止剤"]
tot = df[cats].sum().sum()
for k in cats:
    y = df[k] / df.population * 1e5
    m = sm.OLS(y, sm.add_constant(df[["Cold_months_ratio"] + ses])).fit(cov_type="HC3")
    print(f"  {k:10s}: 全国合計に占める割合={df[k].sum()/tot*100:5.1f}%  Cold5 beta={m.params['Cold_months_ratio']:>12,.0f} HC3 p={m.pvalues['Cold_months_ratio']:.4f}")
print("DONE")
