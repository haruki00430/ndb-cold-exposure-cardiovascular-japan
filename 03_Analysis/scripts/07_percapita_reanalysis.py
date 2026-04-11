# -*- coding: utf-8 -*-
"""
07_percapita_reanalysis.py
CVD処方量を人口10万人あたりに正規化し、回帰分析・空間分析を再実行するスクリプト
"""
import sys, os, warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import yaml
import geopandas as gpd
from pathlib import Path
from sklearn.preprocessing import StandardScaler

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "interim"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# 2020 National Census population by prefecture (total population)
# Source: https://www.stat.go.jp/data/kokusei/2020/kekka.html
POPULATION_2020 = {
    '北海道': 5224614, '青森県': 1237984, '岩手県': 1210534, '宮城県': 2301996,
    '秋田県': 959502, '山形県': 1068027, '福島県': 1833152, '茨城県': 2867009,
    '栃木県': 1933146, '群馬県': 1939110, '埼玉県': 7344765, '千葉県': 6284480,
    '東京都': 14047594, '神奈川県': 9237337, '新潟県': 2201272, '富山県': 1034814,
    '石川県': 1132526, '福井県': 766863, '山梨県': 809974, '長野県': 2048011,
    '岐阜県': 1978742, '静岡県': 3633202, '愛知県': 7542415, '三重県': 1770254,
    '滋賀県': 1413610, '京都府': 2578087, '大阪府': 8837685, '兵庫県': 5465002,
    '奈良県': 1324473, '和歌山県': 922584, '鳥取県': 553407, '島根県': 671126,
    '岡山県': 1888432, '広島県': 2799702, '山口県': 1342059, '徳島県': 719559,
    '香川県': 950244, '愛媛県': 1334841, '高知県': 691527, '福岡県': 5135214,
    '佐賀県': 811442, '長崎県': 1312317, '熊本県': 1738301, '大分県': 1123852,
    '宮崎県': 1069576, '鹿児島県': 1588256, '沖縄県': 1467480
}

# --- Step 1: Load data ---
print("=== 07_percapita_reanalysis.py ===")
print("--- Step 1: データ読み込み ---")
df = pd.read_csv(DATA_DIR / "analysis_dataset.csv", encoding="utf-8")
print(f"  N={len(df)}, columns={len(df.columns)}")

# Map pref_name to population
# First check the prefecture column name
pref_col = 'prefecture'
df['population'] = df[pref_col].map(POPULATION_2020)
missing = df['population'].isna().sum()
if missing > 0:
    print(f"  ! {missing} prefectures have no population data")
    # Try matching with pref_name column if exists
    if 'pref_name' in df.columns:
        df['population'] = df['pref_name'].map(POPULATION_2020)
        missing = df['population'].isna().sum()
        if missing > 0:
            print(f"  Still {missing} missing after pref_name match")
            print(df[df['population'].isna()][[pref_col]])
else:
    print(f"  Population data matched for all {len(df)} prefectures")

# Per 100,000 population rate
df['cvd_rate_per100k'] = df['cvd_total_quantity'] / df['population'] * 100000
print(f"  CVD rate per 100k: mean={df['cvd_rate_per100k'].mean():.1f}, SD={df['cvd_rate_per100k'].std():.1f}")
print(f"  Range: {df['cvd_rate_per100k'].min():.1f} - {df['cvd_rate_per100k'].max():.1f}")

# --- Step 2: Descriptive statistics ---
print("\n--- Step 2: 記述統計（人口あたり） ---")
from scipy import stats as scipy_stats

desc_vars = {
    'cvd_rate_per100k': 'CVD処方量（10万人対）',
    'Mean_Temp_avg': '年間平均気温 (℃)',
    'Temp_range_annual': '年間気温較差 (℃)',
    'physicians_per_100k': '医師数 (10万対)',
    'unemployment_rate': '完全失業率 (%)',
    'elderly_ratio': '高齢化率 (%)',
    'income_per_capita': '県民所得 (万円)',
}

desc_rows = []
for col, label in desc_vars.items():
    s = df[col]
    sw_stat, sw_p = scipy_stats.shapiro(s)
    desc_rows.append({
        'Variable': label,
        'N': len(s),
        'Mean': f"{s.mean():.2f}",
        'SD': f"{s.std():.2f}",
        'Min': f"{s.min():.2f}",
        'Max': f"{s.max():.2f}",
        'Shapiro-W': f"{sw_stat:.4f}",
        'p': f"{sw_p:.4f}" if sw_p >= 0.001 else "<0.001",
    })

desc_df = pd.DataFrame(desc_rows)
print(desc_df.to_string(index=False))

# --- Step 3: OLS Regression (per capita) ---
print("\n--- Step 3: OLS回帰分析（人口あたり） ---")
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan

dep_var = 'cvd_rate_per100k'
temp_vars = ['Mean_Temp_avg', 'Temp_range_annual', 'Winter_temp_avg', 'Temp_std', 'Cold_months_ratio']
ses_vars = ['physicians_per_100k', 'unemployment_rate', 'elderly_ratio', 'income_per_capita']

# Univariate
print("\n  --- 3.1 単変量OLS ---")
uni_results = []
for tv in temp_vars:
    X = sm.add_constant(df[[tv]])
    y = df[dep_var]
    model = sm.OLS(y, X).fit()
    uni_results.append({
        'Temp': tv,
        'beta': f"{model.params[tv]:.4f}",
        'p': f"{model.pvalues[tv]:.4f}",
        'R2': f"{model.rsquared:.4f}",
    })
    print(f"  {tv}: beta={model.params[tv]:.4f}, p={model.pvalues[tv]:.4f}, R2={model.rsquared:.4f}")

# Multivariable
print("\n  --- 3.2 多変量OLS ---")
multi_results = []
for tv in temp_vars:
    X = sm.add_constant(df[[tv] + ses_vars])
    y = df[dep_var]
    model = sm.OLS(y, X).fit()
    multi_results.append({
        'Temp': tv,
        'beta_temp': model.params[tv],
        'p_temp': model.pvalues[tv],
        'adj_r2': model.rsquared_adj,
        'aic': model.aic,
    })
    print(f"  {tv}: beta={model.params[tv]:.4f}, p={model.pvalues[tv]:.4f}, adj_R2={model.rsquared_adj:.4f}, AIC={model.aic:.1f}")

# Best model
best = sorted(multi_results, key=lambda x: -x['adj_r2'])[0]
best_temp = best['Temp']
print(f"\n  Best model: {best_temp} (adj_R2={best['adj_r2']:.4f})")

# Full details of best model
X = sm.add_constant(df[[best_temp] + ses_vars])
y = df[dep_var]
best_model = sm.OLS(y, X).fit()
print(best_model.summary())

# VIF
print("\n  --- 3.3 VIF ---")
X_vif = df[[best_temp] + ses_vars]
for i, col in enumerate(X_vif.columns):
    vif = variance_inflation_factor(X_vif.values, i)
    print(f"  {col}: VIF={vif:.2f}")

# Residual diagnostics
print("\n  --- 3.4 残差診断 ---")
resid = best_model.resid
sw_stat, sw_p = scipy_stats.shapiro(resid)
print(f"  Shapiro-Wilk: W={sw_stat:.4f}, p={sw_p:.4f}")
bp_stat, bp_p, _, _ = het_breuschpagan(resid, best_model.model.exog)
print(f"  Breusch-Pagan: chi2={bp_stat:.3f}, p={bp_p:.4f}")
from statsmodels.stats.stattools import durbin_watson
dw = durbin_watson(resid)
print(f"  Durbin-Watson: {dw:.3f}")

# --- Step 4: Spatial Analysis (per capita) ---
print("\n--- Step 4: 空間解析（人口あたり） ---")

# Build prefecture GeoDataFrame (use cache if exists)
import pickle
CACHE_PATH = DATA_DIR / "pref_gdf_cache.pkl"
if CACHE_PATH.exists():
    print("  Loading cached GeoDataFrame...")
    gdf = pickle.load(open(CACHE_PATH, 'rb'))
    if not isinstance(gdf, gpd.GeoDataFrame):
        gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
else:
    print("  Building prefecture GeoDataFrame from shapefiles...")
    config_path = PROJECT_ROOT / "config" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    shp_dir = Path(config['data_sources']['shapefile']['path'])
    if not shp_dir.is_absolute():
        shp_dir = PROJECT_ROOT / shp_dir
    shp_files = list(shp_dir.glob("*.shp"))
    gdfs = []
    for shp in shp_files:
        g = gpd.read_file(shp)
        gdfs.append(g)
    all_gdf = pd.concat(gdfs, ignore_index=True)
    if 'PREF_NAME' in all_gdf.columns:
        pref_gdf = all_gdf.dissolve(by='PREF_NAME').reset_index()
    elif 'N03_001' in all_gdf.columns:
        pref_gdf = all_gdf.dissolve(by='N03_001').reset_index()
        pref_gdf = pref_gdf.rename(columns={'N03_001': 'PREF_NAME'})
    gdf = pref_gdf
    with open(CACHE_PATH, 'wb') as f:
        pickle.dump(gdf, f)

# Merge analysis data - cached GDF uses 'prefecture' column
merge_col = 'prefecture' if 'prefecture' in gdf.columns else 'PREF_NAME'
gdf = gdf.merge(df, left_on=merge_col, right_on=pref_col, how='inner', suffixes=('_geo', ''))
print(f"  Merged GeoDataFrame: N={len(gdf)}")

# Spatial weights (KNN k=4)
from libpysal.weights import Queen, KNN
w = Queen.from_dataframe(gdf)
if len(w.islands) > 0:
    print(f"  ! Islands detected, switching to KNN(k=4)")
    w = KNN.from_dataframe(gdf, k=4)
    w = w.symmetrize()
    w.transform = 'R'
    w_desc = 'KNN(k=4) symmetrized + row-standardized'
else:
    w.transform = 'R'
    w_desc = 'Queen contiguity (row-standardized)'

# Global Moran's I
from esda.moran import Moran, Moran_Local
y_moran = df[dep_var].values
mi = Moran(y_moran, w, permutations=999)
print(f"\n  Global Moran's I = {mi.I:.4f}")
print(f"  z = {mi.z_sim:.3f}, p(sim) = {mi.p_sim:.4f}")
print(f"  p(norm) = {mi.p_norm:.4f}")

# LISA
lisa = Moran_Local(y_moran, w, permutations=999)
sig = lisa.p_sim < 0.05
q = lisa.q  # 1=HH,2=LH,3=LL,4=HL
labels = {1: 'High-High', 2: 'Low-High', 3: 'Low-Low', 4: 'High-Low'}
print("\n  LISA clusters (p<0.05):")
for i in range(len(gdf)):
    if sig[i]:
        pname = gdf.iloc[i][merge_col]
        print(f"    {pname}: {labels[q[i]]}")

# OLS for spatial
print("\n  --- Spatial OLS + LM tests ---")
from spreg import OLS as spreg_OLS, ML_Lag, ML_Error

scaler = StandardScaler()
X_cols = [best_temp] + ses_vars
X_std = scaler.fit_transform(df[X_cols])
y_std = scaler.fit_transform(df[[dep_var]])

ols_sp = spreg_OLS(y_std, X_std, w=w, name_y=dep_var, name_x=X_cols, spat_diag=True)
print(f"  OLS R2 = {ols_sp.r2:.4f}")
print(f"  OLS AIC = {ols_sp.aic:.1f}")

# LM tests
lm_tests = ols_sp.lm_lag, ols_sp.lm_error, ols_sp.rlm_lag, ols_sp.rlm_error
lm_names = ['LM-Lag', 'LM-Error', 'Robust LM-Lag', 'Robust LM-Error']
print("\n  LM tests:")
selected_model = None
for name, test in zip(lm_names, lm_tests):
    stat, pval = test
    sig_str = 'sig' if pval < 0.05 else 'n.s.'
    print(f"    {name}: stat={stat:.3f}, p={pval:.4f} ({sig_str})")

# Model selection based on LM tests
lm_lag_p = ols_sp.lm_lag[1]
lm_err_p = ols_sp.lm_error[1]
rlm_lag_p = ols_sp.rlm_lag[1]
rlm_err_p = ols_sp.rlm_error[1]

if lm_lag_p < 0.05 and lm_err_p >= 0.05:
    selected_model = 'SLM'
elif lm_err_p < 0.05 and lm_lag_p >= 0.05:
    selected_model = 'SEM'
elif lm_lag_p < 0.05 and lm_err_p < 0.05:
    selected_model = 'SLM' if rlm_lag_p < rlm_err_p else 'SEM'
else:
    selected_model = 'OLS'

print(f"\n  Selected model: {selected_model}")

# Fit spatial model
if selected_model == 'SLM':
    sp_model = ML_Lag(y_std, X_std, w=w, name_y=dep_var, name_x=X_cols)
    rho = sp_model.rho
    print(f"  SLM rho = {rho:.4f}")
    print(f"  SLM Pseudo-R2 = {sp_model.pr2:.4f}")
    print(f"  SLM AIC = {sp_model.aic:.1f}")
elif selected_model == 'SEM':
    sp_model = ML_Error(y_std, X_std, w=w, name_y=dep_var, name_x=X_cols)
    lam = sp_model.lam
    print(f"  SEM lambda = {lam:.4f}")
    print(f"  SEM Pseudo-R2 = {sp_model.pr2:.4f}")
    print(f"  SEM AIC = {sp_model.aic:.1f}")
else:
    sp_model = None

# Print coefficients
if sp_model is not None:
    print(f"\n  Coefficients ({selected_model}):")
    betas = sp_model.betas.flatten()
    zstat = sp_model.z_stat
    for i, name in enumerate(['Intercept'] + X_cols):
        coef = betas[i]
        z_val = zstat[i][0]
        p_val = zstat[i][1]
        sig_star = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''
        print(f"    {name}: beta={coef:.4f}, z={z_val:.2f}, p={p_val:.4f} {sig_star}")

# --- Step 5: Write Markdown report ---
print("\n--- Step 5: Markdown出力 ---")
md_path = RESULTS_DIR / "percapita_reanalysis.md"

with open(md_path, 'w', encoding='utf-8') as f:
    f.write("# 人口あたりCVD処方量 再解析結果\n\n")
    f.write(f"**目的変数**: CVD処方量（10万人あたり）\n")
    f.write(f"**データ**: analysis_dataset.csv (N={len(df)}, 47都道府県)\n")
    f.write(f"**人口データ**: 2020年国勢調査\n\n")

    # Descriptive
    f.write("## 1. 記述統計\n\n")
    f.write("| 変数 | N | Mean | SD | Min | Max |\n")
    f.write("|------|---|------|-----|-----|-----|\n")
    for _, row in desc_df.iterrows():
        f.write(f"| {row['Variable']} | {row['N']} | {row['Mean']} | {row['SD']} | {row['Min']} | {row['Max']} |\n")
    f.write("\n")

    # Univariate OLS
    f.write("## 2. 単変量OLS\n\n")
    f.write("| 気温指標 | β | p値 | R² |\n")
    f.write("|---------|---|------|----|\n")
    for r in uni_results:
        f.write(f"| {r['Temp']} | {r['beta']} | {r['p']} | {r['R2']} |\n")
    f.write("\n")

    # Multivariable
    f.write("## 3. 多変量OLS\n\n")
    f.write(f"### 最良モデル: {best_temp} (Adj. R²={best['adj_r2']:.4f})\n\n")
    f.write("| 変数 | β | SE | t値 | p値 |\n")
    f.write("|------|---|-----|-----|------|\n")
    for var in best_model.params.index:
        coef = best_model.params[var]
        se = best_model.bse[var]
        t = best_model.tvalues[var]
        p = best_model.pvalues[var]
        sig_star = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
        f.write(f"| {var} | {coef:.4f} | {se:.4f} | {t:.2f} | {p:.4f} {sig_star} |\n")
    f.write(f"\n**R²={best_model.rsquared:.4f}, Adj. R²={best_model.rsquared_adj:.4f}**\n\n")

    # Residual diagnostics
    f.write("### 残差診断\n\n")
    f.write(f"- Shapiro-Wilk: W={sw_stat:.4f}, p={sw_p:.4f}\n")
    f.write(f"- Breusch-Pagan: chi2={bp_stat:.3f}, p={bp_p:.4f}\n")
    f.write(f"- Durbin-Watson: {dw:.3f}\n\n")

    # Spatial
    f.write("## 4. 空間解析\n\n")
    f.write(f"**空間重み行列**: {w_desc}\n\n")
    f.write(f"### Global Moran's I\n\n")
    f.write(f"- Moran's I = {mi.I:.4f}\n")
    f.write(f"- z = {mi.z_sim:.3f}\n")
    f.write(f"- p (permutation) = {mi.p_sim:.4f}\n\n")

    # LISA
    f.write("### LISA clusters (p<0.05)\n\n")
    f.write("| 都道府県 | クラスター |\n")
    f.write("|---------|-----------|\n")
    for i in range(len(gdf)):
        if sig[i]:
            pname = gdf.iloc[i][merge_col]
            f.write(f"| {pname} | {labels[q[i]]} |\n")
    f.write("\n")

    # LM tests
    f.write("### LM検定\n\n")
    f.write("| 検定 | 統計量 | p値 |\n")
    f.write("|------|--------|------|\n")
    for name, test in zip(lm_names, lm_tests):
        stat, pval = test
        f.write(f"| {name} | {stat:.3f} | {pval:.4f} |\n")
    f.write(f"\n**選択モデル**: {selected_model}\n\n")

    # Spatial model
    if sp_model is not None:
        f.write(f"### {selected_model} 結果\n\n")
        if selected_model == 'SLM':
            f.write(f"**ρ (rho) = {rho:.4f}**\n\n")
        else:
            f.write(f"**λ (lambda) = {lam:.4f}**\n\n")

        f.write(f"**Pseudo-R² = {sp_model.pr2:.4f}** (OLS R² = {ols_sp.r2:.4f})\n\n")
        f.write(f"**AIC = {sp_model.aic:.1f}** (OLS AIC = {ols_sp.aic:.1f})\n\n")

        f.write("| 変数 | β (標準化) | z値 | p値 |\n")
        f.write("|------|-----------|-----|------|\n")
        betas = sp_model.betas.flatten()
        zstat = sp_model.z_stat
        for i, name in enumerate(['Intercept'] + X_cols):
            coef = betas[i]
            z_val = zstat[i][0]
            p_val = zstat[i][1]
            sig_star = '***' if p_val < 0.001 else '**' if p_val < 0.01 else '*' if p_val < 0.05 else ''
            f.write(f"| {name} | {coef:+.4f} | {z_val:.2f} | {p_val:.4f} {sig_star} |\n")

        f.write("\n> 全変数はZスコア標準化済み\n")

print(f"\n  Report saved to: {md_path}")
print("\n=== Complete ===")
