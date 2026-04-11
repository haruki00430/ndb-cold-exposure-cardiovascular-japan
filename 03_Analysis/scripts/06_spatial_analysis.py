#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 8: 空間統計解析

analysis_dataset.csv を用いて以下を実施:
  1. 都道府県ポリゴン作成（A38二次医療圏shpを都道府県コードでdissolve）
  2. CVD処方量のChoropleth地図
  3. Global Moran's I（空間的自己相関の全体評価）
  4. Local Moran's I（LISA）クラスタマップ
  5. LM検定によるモデル選択（SLM vs SEM）
  6. 空間回帰モデル実行
  7. 結果をMarkdown形式で出力

出力:
  results/spatial_analysis.md            — 全結果
  results/figures/choropleth_cvd.png     — CVD処方量地図
  results/figures/moran_scatter.png      — Moranの散布図
  results/figures/lisa_cluster.png       — LISAクラスタマップ
"""

import sys
import glob
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import yaml

from libpysal.weights import Queen
from esda.moran import Moran, Moran_Local
import spreg

# --- プロジェクトパス ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT.parents[1] / 'src'))

from ndb_library.viz import set_japanese_font

# --- 設定 ---
with open(PROJECT_ROOT / 'config' / 'config.yaml', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

DATA_FILE   = PROJECT_ROOT / 'data' / 'interim' / 'analysis_dataset.csv'
RESULTS_DIR = PROJECT_ROOT / 'results'
FIG_DIR     = RESULTS_DIR / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

# A38二次医療圏shpのパターン（市区町村ポリゴン）
A38_PATTERN = str(PROJECT_ROOT.parents[1] / '02_Data' / 'raw' / 'A38_Medical_Area' /
                  '*_GML' / '*_GML' / '*_1.shp')

DPI = cfg.get('output', {}).get('figures_dpi', 300)

# 都道府県コード → 都道府県名マッピング
PREF_CODE_MAP = {
    '01': '北海道', '02': '青森県', '03': '岩手県', '04': '宮城県', '05': '秋田県',
    '06': '山形県', '07': '福島県', '08': '茨城県', '09': '栃木県', '10': '群馬県',
    '11': '埼玉県', '12': '千葉県', '13': '東京都', '14': '神奈川県', '15': '新潟県',
    '16': '富山県', '17': '石川県', '18': '福井県', '19': '山梨県', '20': '長野県',
    '21': '岐阜県', '22': '静岡県', '23': '愛知県', '24': '三重県', '25': '滋賀県',
    '26': '京都府', '27': '大阪府', '28': '兵庫県', '29': '奈良県', '30': '和歌山県',
    '31': '鳥取県', '32': '島根県', '33': '岡山県', '34': '広島県', '35': '山口県',
    '36': '徳島県', '37': '香川県', '38': '愛媛県', '39': '高知県', '40': '福岡県',
    '41': '佐賀県', '42': '長崎県', '43': '熊本県', '44': '大分県', '45': '宮崎県',
    '46': '鹿児島県', '47': '沖縄県',
}

# 目的変数
TARGET = 'cvd_total_quantity'
TARGET_LABEL = 'CVD処方量（総数量）'

# 共変量（最良モデルから）
COVARIATES = ['Mean_Temp_avg', 'physicians_per_100k', 'unemployment_rate',
              'elderly_ratio', 'income_per_capita']
COV_LABELS = ['年間平均気温', '医師数(10万対)', '完全失業率(%)', '高齢化率(%)', '県民所得(万円)']


# ====================================================================
# Step 1: 都道府県GeoDataFrame作成
# ====================================================================
CACHE_FILE = PROJECT_ROOT / 'data' / 'interim' / 'pref_gdf_cache.pkl'

def build_prefecture_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """A38市町村shpをdissolveして都道府県ポリゴンを作成し、解析データと結合。"""
    print("\n--- Step 1: 都道府県GeoDataFrame作成 ---")

    if CACHE_FILE.exists():
        import pickle
        with open(CACHE_FILE, 'rb') as f:
            merged = pickle.load(f)
        print("  ... Loaded from cache")
        df_merged = pd.merge(merged[['prefecture', 'geometry']], df, on='prefecture', how='inner')
        return gpd.GeoDataFrame(df_merged, geometry='geometry')

    shp_files = glob.glob(A38_PATTERN)
    print(f"  A38 shpファイル数: {len(shp_files)}")
    if not shp_files:
        raise FileNotFoundError(f"A38 shpファイルが見つかりません: {A38_PATTERN}")

    # 全shpを結合
    gdfs = []
    for fp in sorted(shp_files):
        gdf = gpd.read_file(fp)
        gdf['pref_code'] = gdf['A38a_001'].astype(str).str[:2]
        gdfs.append(gdf[['pref_code', 'geometry']])

    all_gdf = pd.concat(gdfs, ignore_index=True)
    all_gdf = all_gdf.to_crs(epsg=4326)

    # 都道府県コードでdissolve
    pref_gdf = all_gdf.dissolve(by='pref_code').reset_index()
    pref_gdf['prefecture'] = pref_gdf['pref_code'].map(PREF_CODE_MAP)
    print(f"  都道府県数: {len(pref_gdf)}")

    import pickle
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(pref_gdf, f)

    # analysis_dataset とマージ
    merged = pref_gdf.merge(df, on='prefecture', how='left')
    n_miss = merged[TARGET].isna().sum()
    print(f"  結合後: {len(merged)}都道府県（CVD欠損: {n_miss}件）")

    return merged


# ====================================================================
# Step 2: Choropleth地図
# ====================================================================
def plot_choropleth(gdf: gpd.GeoDataFrame):
    """CVD処方量のChoropleth地図。"""
    print("\n--- Step 2: Choropleth地図 ---")
    set_japanese_font()

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf.plot(
        column=TARGET,
        cmap='YlOrRd',
        legend=True,
        ax=ax,
        edgecolor='grey',
        linewidth=0.3,
        legend_kwds={'label': TARGET_LABEL, 'shrink': 0.6, 'orientation': 'vertical'},
        missing_kwds={'color': 'lightgrey'},
    )
    ax.set_title(f'都道府県別{TARGET_LABEL}', fontsize=14, fontweight='bold')
    ax.set_axis_off()
    plt.tight_layout()

    outpath = FIG_DIR / 'choropleth_cvd.png'
    fig.savefig(outpath, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] {outpath.name}")


# ====================================================================
# Step 3: Global Moran's I
# ====================================================================
def run_global_moran(gdf: gpd.GeoDataFrame, w) -> dict:
    """Global Moran's I を計算。"""
    print("\n--- Step 3: Global Moran's I ---")
    y = gdf[TARGET].fillna(gdf[TARGET].mean()).values
    moran = Moran(y, w, permutations=999)
    result = {
        'I': moran.I,
        'EI': moran.EI,
        'z': moran.z_norm,
        'p_norm': moran.p_norm,
        'p_sim': moran.p_sim,
        'moran_obj': moran,
        'y': y,
    }
    sig = '***' if moran.p_sim < 0.001 else ('**' if moran.p_sim < 0.01 else
          ('*' if moran.p_sim < 0.05 else 'n.s.'))
    print(f"  Moran's I = {moran.I:.4f}  (E[I]={moran.EI:.4f})")
    print(f"  z = {moran.z_norm:.3f},  p(正規近似) = {moran.p_norm:.4f},  p(置換) = {moran.p_sim:.4f} {sig}")
    return result


def plot_moran_scatter(moran_result: dict, gdf: gpd.GeoDataFrame, w):
    """Moranの散布図。"""
    set_japanese_font()
    y = moran_result['y']
    y_std = (y - y.mean()) / y.std()
    wy = w.sparse.dot(y_std)

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(y_std, wy, alpha=0.7, edgecolors='white', s=60, c='steelblue')
    ax.axhline(0, color='grey', linestyle='--', alpha=0.5)
    ax.axvline(0, color='grey', linestyle='--', alpha=0.5)

    # 回帰線
    slope = moran_result['I']
    x_line = np.linspace(y_std.min(), y_std.max(), 100)
    ax.plot(x_line, slope * x_line, 'r-', linewidth=2,
            label=f"I = {slope:.4f} (p={moran_result['p_sim']:.4f})")
    ax.set_xlabel('標準化CVD処方量', fontsize=11)
    ax.set_ylabel('空間ラグ（標準化）', fontsize=11)
    ax.set_title(f"Moranの散布図  (Global Moran's I = {slope:.4f})", fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    outpath = FIG_DIR / 'moran_scatter.png'
    fig.savefig(outpath, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] {outpath.name}")


# ====================================================================
# Step 4: Local Moran's I（LISA）
# ====================================================================
def run_local_moran(gdf: gpd.GeoDataFrame, w) -> gpd.GeoDataFrame:
    """LISA（Local Indicators of Spatial Association）を計算。"""
    print("\n--- Step 4: Local Moran's I (LISA) ---")
    y = gdf[TARGET].fillna(gdf[TARGET].mean()).values
    moran_loc = Moran_Local(y, w, permutations=999, seed=42)

    gdf = gdf.copy()
    gdf['lisa_q'] = moran_loc.q       # 1=HH, 2=LH, 3=LL, 4=HL
    gdf['lisa_sig'] = moran_loc.p_sim < 0.05
    gdf['lisa_label'] = gdf.apply(
        lambda r: {1: 'High-High', 2: 'Low-High', 3: 'Low-Low', 4: 'High-Low'}.get(
            r['lisa_q'], 'n.s.') if r['lisa_sig'] else 'n.s.', axis=1
    )
    cluster_counts = gdf['lisa_label'].value_counts()
    print("  LISAクラスター分布:")
    for k, v in cluster_counts.items():
        print(f"    {k}: {v}都道府県")
    return gdf


def plot_lisa(gdf: gpd.GeoDataFrame):
    """LISAクラスタマップ。"""
    set_japanese_font()

    color_map = {
        'High-High': '#d73027',
        'Low-Low': '#4575b4',
        'High-Low': '#fc8d59',
        'Low-High': '#91bfdb',
        'n.s.': '#eeeeee',
    }
    gdf = gdf.copy()
    gdf['color'] = gdf['lisa_label'].map(color_map)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf.plot(color=gdf['color'], ax=ax, edgecolor='grey', linewidth=0.3)
    ax.set_title('LISA クラスタマップ（CVD処方量）', fontsize=14, fontweight='bold')
    ax.set_axis_off()

    # 凡例
    patches = [mpatches.Patch(color=v, label=k) for k, v in color_map.items()]
    ax.legend(handles=patches, loc='lower right', fontsize=10, title='クラスター')
    plt.tight_layout()

    outpath = FIG_DIR / 'lisa_cluster.png'
    fig.savefig(outpath, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] {outpath.name}")


# ====================================================================
# Step 5: LM検定 + 空間回帰
# ====================================================================
def run_spatial_regression(gdf: gpd.GeoDataFrame, w) -> dict:
    """LM検定でモデルを選択し、空間回帰を実行。"""
    print("\n--- Step 5: LM検定・空間回帰 ---")

    sub = gdf[COVARIATES + [TARGET]].dropna()
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    scaled_values = scaler.fit_transform(sub[COVARIATES + [TARGET]])
    sub_scaled = pd.DataFrame(scaled_values, columns=COVARIATES + [TARGET], index=sub.index)

    y = sub_scaled[TARGET].values.reshape(-1, 1)
    X = sub_scaled[COVARIATES].values

    # OLS + LM検定
    ols = spreg.OLS(
        y, X, w=w,
        name_y=TARGET, name_x=COVARIATES,
        spat_diag=True,
    )

    lm_lag  = ols.lm_lag
    lm_err  = ols.lm_error
    rlm_lag = ols.rlm_lag
    rlm_err = ols.rlm_error

    print(f"  OLS: R²={ols.r2:.3f}, AIC={ols.aic:.2f}")
    print(f"  LM-Lag    stat={lm_lag[0]:.3f}, p={lm_lag[1]:.4f}")
    print(f"  LM-Error  stat={lm_err[0]:.3f}, p={lm_err[1]:.4f}")
    print(f"  RLM-Lag   stat={rlm_lag[0]:.3f}, p={rlm_lag[1]:.4f}")
    print(f"  RLM-Error stat={rlm_err[0]:.3f}, p={rlm_err[1]:.4f}")

    # モデル選択
    sig_lag = lm_lag[1] < 0.05
    sig_err = lm_err[1] < 0.05

    if sig_lag and sig_err:
        # 両方有意 → RLMで判断
        if rlm_lag[1] < rlm_err[1]:
            model_type = 'SLM'
            print("  → 両方有意: RLM-Lag優位 → Spatial Lag Model (SLM) を選択")
        else:
            model_type = 'SEM'
            print("  → 両方有意: RLM-Error優位 → Spatial Error Model (SEM) を選択")
    elif sig_lag:
        model_type = 'SLM'
        print("  → LM-Lagのみ有意 → Spatial Lag Model (SLM) を選択")
    elif sig_err:
        model_type = 'SEM'
        print("  → LM-Errorのみ有意 → Spatial Error Model (SEM) を選択")
    else:
        model_type = 'OLS'
        print("  → 両方非有意 → OLSで十分")

    # 空間回帰実行（ML推定）
    spatial_model = None
    if model_type == 'SLM':
        spatial_model = spreg.ML_Lag(
            y, X, w=w,
            name_y=TARGET, name_x=COVARIATES,
        )
        print(f"  SLM(ML): ρ={spatial_model.rho:.4f}, Pseudo-R²={spatial_model.pr2:.3f}")
    elif model_type == 'SEM':
        spatial_model = spreg.ML_Error(
            y, X, w=w,
            name_y=TARGET, name_x=COVARIATES,
        )
        print(f"  SEM(ML): λ={spatial_model.lam:.4f}, Pseudo-R²={spatial_model.pr2:.3f}")

    return {
        'ols': ols,
        'spatial_model': spatial_model,
        'model_type': model_type,
        'lm_lag': lm_lag,
        'lm_err': lm_err,
        'rlm_lag': rlm_lag,
        'rlm_err': rlm_err,
        'sub': sub,
        'standardized': True,
    }


# ====================================================================
# Step 6: Markdown出力
# ====================================================================
def write_results_markdown(moran_result: dict, gdf_lisa: gpd.GeoDataFrame,
                            regression_result: dict):
    """結果をMarkdown形式で出力。"""
    outpath = RESULTS_DIR / 'spatial_analysis.md'
    lines = []

    lines.append("# 空間統計解析結果")
    lines.append("")
    lines.append(f"**データ**: analysis_dataset.csv (N=47, 47都道府県)")
    lines.append(f"**目的変数**: {TARGET_LABEL}")
    lines.append(f"**解析日**: {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    w_desc = regression_result.get('w_desc', 'Queen接触 (行標準化)')
    lines.append(f"**空間重み行列**: {w_desc}")
    lines.append("")

    # --- Global Moran's I ---
    lines.append("## 1. Global Moran's I")
    lines.append("")
    mi = moran_result['I']
    p = moran_result['p_sim']
    sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'n.s.'))
    interp = ("正の空間的自己相関（類似した値が隣接）" if mi > 0 and p < 0.05 else
              "負の空間的自己相関（異なる値が隣接）" if mi < 0 and p < 0.05 else "空間的自己相関なし")
    lines.append(f"| 指標 | 値 |")
    lines.append(f"|------|-----|")
    lines.append(f"| Moran's I | {mi:.4f} {sig} |")
    lines.append(f"| 期待値 E[I] | {moran_result['EI']:.4f} |")
    lines.append(f"| z値 | {moran_result['z']:.3f} |")
    lines.append(f"| p値（正規近似） | {moran_result['p_norm']:.4f} |")
    lines.append(f"| p値（置換検定 999回） | {moran_result['p_sim']:.4f} |")
    lines.append(f"| 解釈 | {interp} |")
    lines.append("")
    lines.append("> \\*p<0.05, \\*\\*p<0.01, \\*\\*\\*p<0.001")
    lines.append("")

    # --- LISA ---
    lines.append("## 2. LISA クラスター（Local Moran's I）")
    lines.append("")
    lines.append("| クラスター | 意味 | 都道府県数 |")
    lines.append("|-----------|------|----------|")
    for label in ['High-High', 'Low-Low', 'High-Low', 'Low-High', 'n.s.']:
        cnt = (gdf_lisa['lisa_label'] == label).sum()
        desc = {'High-High': 'CVD高・隣接も高（ホットスポット）',
                'Low-Low': 'CVD低・隣接も低（コールドスポット）',
                'High-Low': 'CVD高・隣接は低（孤立高値）',
                'Low-High': 'CVD低・隣接は高（孤立低値）',
                'n.s.': '有意なクラスターなし'}.get(label, '')
        lines.append(f"| {label} | {desc} | {cnt} |")
    lines.append("")

    # 有意なクラスター都道府県一覧
    sig_prefs = gdf_lisa[gdf_lisa['lisa_sig']][['prefecture', 'lisa_label']].sort_values('lisa_label')
    if not sig_prefs.empty:
        lines.append("**有意（p<0.05）クラスター都道府県一覧:**")
        lines.append("")
        lines.append("| 都道府県 | クラスター |")
        lines.append("|---------|-----------|")
        for _, row in sig_prefs.iterrows():
            lines.append(f"| {row['prefecture']} | {row['lisa_label']} |")
        lines.append("")

    # --- LM検定 ---
    r = regression_result
    lines.append("## 3. LM検定（モデル選択）")
    lines.append("")
    lines.append("| 検定 | 統計量 | p値 | 判定 |")
    lines.append("|------|--------|------|------|")

    def lm_row(name, stat, p):
        return f"| {name} | {stat:.3f} | {p:.4f} | {'有意 ✓' if p < 0.05 else 'n.s.'} |"

    lines.append(lm_row("LM-Lag", r['lm_lag'][0], r['lm_lag'][1]))
    lines.append(lm_row("LM-Error", r['lm_err'][0], r['lm_err'][1]))
    lines.append(lm_row("Robust LM-Lag", r['rlm_lag'][0], r['rlm_lag'][1]))
    lines.append(lm_row("Robust LM-Error", r['rlm_err'][0], r['rlm_err'][1]))
    lines.append("")
    lines.append(f"**選択モデル**: {r['model_type']}")
    lines.append("")

    # --- 空間回帰 ---
    ols = r['ols']
    lines.append("## 4. 空間回帰モデル結果")
    lines.append("")

    # OLS比較
    lines.append("### 4.1 モデル比較")
    lines.append("")
    lines.append("| モデル | R² / Pseudo-R² | AIC |")
    lines.append("|--------|----------------|-----|")
    lines.append(f"| OLS | {ols.r2:.3f} | {ols.aic:.1f} |")
    sm = r['spatial_model']
    if sm and r['model_type'] != 'OLS':
        aic_str = f"{sm.aic:.1f}" if hasattr(sm, 'aic') and sm.aic is not None else "—"
        lines.append(f"| {r['model_type']} (ML) | {sm.pr2:.3f} | {aic_str} |")
    lines.append("")

    # 係数テーブル
    if sm and r['model_type'] != 'OLS':
        lines.append(f"### 4.2 {r['model_type']} 係数テーブル")
        lines.append("")
        if r['model_type'] == 'SLM':
            lines.append(f"**空間自己回帰係数 ρ (rho) = {sm.rho:.4f}**")
        else:
            lines.append(f"**空間誤差係数 λ (lambda) = {sm.lam:.4f}**")
        lines.append("")
        lines.append("| 変数 | β係数 | z値 | p値 |")
        lines.append("|------|-------|-----|------|")
        for i, (name, coef) in enumerate(zip(['切片'] + COVARIATES, sm.betas.flatten())):
            if i < len(sm.z_stat):
                z_val, p_val = sm.z_stat[i]
                p_str = f'{p_val:.4f}' if p_val >= 0.001 else '<0.001'
                sig = '***' if p_val < 0.001 else ('**' if p_val < 0.01 else ('*' if p_val < 0.05 else ''))
                label = COV_LABELS[i-1] if i > 0 else '切片'
                lines.append(f"| {label} | {coef:+.4f} | {z_val:.2f} | {p_str} {sig} |")
        lines.append("")
        lines.append("> \\*p<0.05, \\*\\*p<0.01, \\*\\*\\*p<0.001")
        lines.append("")
        if r.get('standardized'):
            lines.append("> **注**: 全変数はZスコア標準化済み。β係数は効果量の相対比較として解釈してください。")
            lines.append("")

    # --- Figure一覧 ---
    lines.append("## 5. 生成Figure")
    lines.append("")
    lines.append("| ファイル | 内容 |")
    lines.append("|---------|------|")
    lines.append("| `figures/choropleth_cvd.png` | 都道府県別CVD処方量地図 |")
    lines.append("| `figures/moran_scatter.png`  | Moranの散布図 |")
    lines.append("| `figures/lisa_cluster.png`   | LISAクラスタマップ |")
    lines.append("")

    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[OK] 結果出力: {outpath.name}")


# ====================================================================
# Main
# ====================================================================
def main():
    print("=" * 60)
    print("Phase 8: 空間統計解析")
    print("=" * 60)

    # --- データ読み込み ---
    df = pd.read_csv(DATA_FILE, encoding='utf-8')
    print(f"[OK] データ読み込み: {df.shape}")
    set_japanese_font()

    # --- Step 1: 都道府県GDFを作成 ---
    gdf = build_prefecture_gdf(df)

    # --- 空間重み行列（Queen接触）---
    print("\n--- 空間重み行列 (Queen) ---")
    w = Queen.from_dataframe(gdf, silence_warnings=True)
    w.transform = 'R'   # 行標準化
    print(f"  n={w.n}, 平均近傍数={w.mean_neighbors:.2f}, 孤立地域={len(w.islands)}")

    # 孤立地域がある場合はKNNにフォールバック（Moran/LISA用 = 行標準化あり）
    if len(w.islands) > 0:
        print(f"  ! 孤立地域があるため KNN(k=4) に切り替えます")
        from libpysal.weights import KNN
        w = KNN.from_dataframe(gdf, k=4)
        w = w.symmetrize()
        w.transform = 'R'
        w_spreg = w
        w_desc = 'KNN(k=4) 対称化 + 行標準化'
    else:
        w_spreg = w
        w_desc = 'Queen接触 (行標準化)'

    # --- Step 2: Choropleth ---
    plot_choropleth(gdf)

    # --- Step 3: Global Moran's I ---
    moran_result = run_global_moran(gdf, w)
    plot_moran_scatter(moran_result, gdf, w)

    # --- Step 4: LISA ---
    gdf_lisa = run_local_moran(gdf, w)
    plot_lisa(gdf_lisa)

    # --- Step 5: 空間回帰 ---
    regression_result = run_spatial_regression(gdf, w_spreg)
    # 重み行列の説明をMarkdown出力用に追加
    regression_result['w_desc'] = w_desc

    # --- Step 6: 結果出力 ---
    print("\n--- Step 6: Markdown出力 ---")
    write_results_markdown(moran_result, gdf_lisa, regression_result)

    print("\n" + "=" * 60)
    print("[DONE] Phase 8 完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
