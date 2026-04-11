#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 7: 回帰分析

analysis_dataset.csv を用いて以下を実施:
  1. 単変量OLS — 各気温指標 → CVD処方量（10万対）
  2. 多変量OLS — 気温指標 + SES共変量 → CVD処方量
  3. VIF（分散拡大係数）による多重共線性チェック
  4. 残差診断（正規性、等分散性、外れ値）
  5. モデル比較サマリー
  6. 結果をMarkdown形式で出力

出力:
  results/regression_analysis.md              — 全結果テーブル
  results/figures/residual_diagnostics_*.png   — 残差診断図
"""

import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import yaml

import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan, normal_ad

# --- プロジェクトパス ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT.parents[1] / 'src'))

from ndb_library.viz import set_japanese_font

# --- 設定読み込み ---
with open(PROJECT_ROOT / 'config' / 'config.yaml', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

DATA_FILE   = PROJECT_ROOT / 'data' / 'interim' / 'analysis_dataset.csv'
RESULTS_DIR = PROJECT_ROOT / 'results'
FIG_DIR     = RESULTS_DIR / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

DPI = cfg.get('output', {}).get('figures_dpi', 300)

# --- 変数定義 ---
TARGET = 'cvd_total_quantity'
TARGET_LABEL = 'CVD処方量（総数量）'

TEMP_VARS = [
    'Temp_range_annual',
    'Winter_temp_avg',
    'Temp_std',
    'Cold_months_ratio',
    'Mean_Temp_avg',
]

SES_VARS = [
    'physicians_per_100k',
    'unemployment_rate',
    'elderly_ratio',
    'income_per_capita',
]

VAR_LABELS = {
    'Temp_range_annual': '年間気温較差 (℃)',
    'Winter_temp_avg': '冬季平均気温 (℃)',
    'Temp_std': '気温変動SD (℃)',
    'Cold_months_ratio': '寒冷月割合',
    'Mean_Temp_avg': '年間平均気温 (℃)',
    'physicians_per_100k': '医師数 (10万対)',
    'unemployment_rate': '完全失業率 (%)',
    'elderly_ratio': '高齢化率 (%)',
    'income_per_capita': '県民所得 (万円)',
    'cvd_prescription_per_100k': 'CVD処方量 (10万対)',
}


# ====================================================================
# 1. 単変量OLS
# ====================================================================
def run_univariate_ols(df: pd.DataFrame) -> list:
    """各気温指標で単変量OLSを実行。"""
    print("\n--- 1. 単変量OLS ---")
    results = []
    for var in TEMP_VARS:
        if var not in df.columns:
            continue
        sub = df[[var, TARGET]].dropna()
        X = sm.add_constant(sub[var])
        model = sm.OLS(sub[TARGET], X).fit()

        results.append({
            'variable': var,
            'label': VAR_LABELS.get(var, var),
            'n': int(model.nobs),
            'coef': model.params[var],
            'se': model.bse[var],
            'ci_lower': model.conf_int().loc[var, 0],
            'ci_upper': model.conf_int().loc[var, 1],
            't': model.tvalues[var],
            'p': model.pvalues[var],
            'r_squared': model.rsquared,
            'adj_r_squared': model.rsquared_adj,
            'aic': model.aic,
            'bic': model.bic,
            'model': model,
        })
        sig = '***' if model.pvalues[var] < 0.001 else ('**' if model.pvalues[var] < 0.01 else ('*' if model.pvalues[var] < 0.05 else ''))
        print(f"  {VAR_LABELS.get(var, var):25s}: β={model.params[var]:+8.3f} (p={model.pvalues[var]:.4f}) R²={model.rsquared:.3f} {sig}")

    return results


# ====================================================================
# 2. 多変量OLS
# ====================================================================
def run_multivariate_ols(df: pd.DataFrame, temp_var: str) -> dict:
    """気温指標 + SES共変量で多変量OLSを実行。"""
    all_vars = [temp_var] + [v for v in SES_VARS if v in df.columns]
    sub = df[[TARGET] + all_vars].dropna()

    X = sm.add_constant(sub[all_vars])
    model = sm.OLS(sub[TARGET], X).fit()

    return {
        'temp_var': temp_var,
        'model': model,
        'n': int(model.nobs),
        'r_squared': model.rsquared,
        'adj_r_squared': model.rsquared_adj,
        'aic': model.aic,
        'bic': model.bic,
        'f_stat': model.fvalue,
        'f_pvalue': model.f_pvalue,
        'all_vars': all_vars,
    }


def run_all_multivariate(df: pd.DataFrame) -> list:
    """全気温指標で多変量OLSを実行。"""
    print("\n--- 2. 多変量OLS（気温指標 + SES共変量）---")
    results = []
    for var in TEMP_VARS:
        if var not in df.columns:
            continue
        res = run_multivariate_ols(df, var)
        model = res['model']
        temp_p = model.pvalues.get(var, 1.0)
        sig = '***' if temp_p < 0.001 else ('**' if temp_p < 0.01 else ('*' if temp_p < 0.05 else ''))
        print(f"  {VAR_LABELS.get(var, var):25s}: β={model.params.get(var, 0):+8.3f} (p={temp_p:.4f}) Adj.R²={res['adj_r_squared']:.3f} {sig}")
        results.append(res)
    return results


# ====================================================================
# 3. VIF（多重共線性チェック）
# ====================================================================
def compute_vif(df: pd.DataFrame, vars_list: list) -> pd.DataFrame:
    """VIF計算。"""
    sub = df[vars_list].dropna()
    X = sm.add_constant(sub)
    vif_data = []
    for i, col in enumerate(X.columns):
        if col == 'const':
            continue
        vif = variance_inflation_factor(X.values, i)
        vif_data.append({
            '変数': VAR_LABELS.get(col, col),
            'VIF': round(vif, 2),
            '判定': '⚠ 多重共線性の疑い' if vif > 10 else ('△ 注意' if vif > 5 else '○'),
        })
    return pd.DataFrame(vif_data)


# ====================================================================
# 4. 残差診断
# ====================================================================
def residual_diagnostics(model, model_name: str, filename: str):
    """残差診断図（4パネル）を作成。"""
    set_japanese_font()

    resid = model.resid
    fitted = model.fittedvalues
    std_resid = model.get_influence().resid_studentized_internal

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # (1) Residuals vs Fitted
    ax = axes[0, 0]
    ax.scatter(fitted, resid, alpha=0.7, edgecolors='white', s=50)
    ax.axhline(0, color='red', linestyle='--', alpha=0.7)
    ax.set_xlabel('予測値', fontsize=10)
    ax.set_ylabel('残差', fontsize=10)
    ax.set_title('残差 vs 予測値', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # (2) Q-Q plot
    ax = axes[0, 1]
    sp_stats.probplot(std_resid, dist='norm', plot=ax)
    ax.set_title('正規Q-Qプロット', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # (3) Scale-Location (√|standardized residuals|)
    ax = axes[1, 0]
    ax.scatter(fitted, np.sqrt(np.abs(std_resid)), alpha=0.7, edgecolors='white', s=50)
    ax.set_xlabel('予測値', fontsize=10)
    ax.set_ylabel('√|標準化残差|', fontsize=10)
    ax.set_title('Scale-Location', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # (4) Cook's Distance
    ax = axes[1, 1]
    influence = model.get_influence()
    cooks_d = influence.cooks_distance[0]
    ax.stem(range(len(cooks_d)), cooks_d, markerfmt=',', linefmt='C0-', basefmt='k-')
    ax.axhline(4 / len(cooks_d), color='red', linestyle='--', alpha=0.7, label=f'4/n = {4/len(cooks_d):.3f}')
    ax.set_xlabel('観測番号', fontsize=10)
    ax.set_ylabel("Cook's D", fontsize=10)
    ax.set_title("Cook's Distance", fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.suptitle(f'残差診断: {model_name}', fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()

    outpath = FIG_DIR / filename
    fig.savefig(outpath, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"  [OK] 残差診断図: {outpath.name}")


def run_diagnostic_tests(model) -> dict:
    """統計的残差診断テスト。"""
    resid = model.resid

    # Shapiro-Wilk（正規性）
    sw_stat, sw_p = sp_stats.shapiro(resid)

    # Breusch-Pagan（等分散性）
    bp_stat, bp_p, _, _ = het_breuschpagan(resid, model.model.exog)

    # Durbin-Watson（自己相関）
    from statsmodels.stats.stattools import durbin_watson
    dw = durbin_watson(resid)

    # Cook's Distance 外れ値
    influence = model.get_influence()
    cooks_d = influence.cooks_distance[0]
    n_outliers = int(np.sum(cooks_d > 4 / len(cooks_d)))

    return {
        'shapiro_w': sw_stat,
        'shapiro_p': sw_p,
        'bp_stat': bp_stat,
        'bp_p': bp_p,
        'durbin_watson': dw,
        'n_cooks_outliers': n_outliers,
    }


# ====================================================================
# 5. 結果Markdown出力
# ====================================================================
def write_results_markdown(univar_results: list,
                            multivar_results: list,
                            vif_df: pd.DataFrame,
                            best_multivar: dict,
                            diagnostics: dict,
                            df: pd.DataFrame):
    """結果をMarkdown形式で出力。"""
    outpath = RESULTS_DIR / 'regression_analysis.md'
    lines = []

    lines.append("# 回帰分析結果")
    lines.append("")
    lines.append(f"**データ**: analysis_dataset.csv (N={len(df)}, 47都道府県)")
    lines.append(f"**目的変数**: {TARGET_LABEL}")
    lines.append(f"**解析日**: {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # --- 単変量OLS ---
    lines.append("## 1. 単変量OLS（各気温指標 → CVD処方量）")
    lines.append("")
    lines.append("| 説明変数 | β係数 | 95% CI | t値 | p値 | R² | Adj. R² |")
    lines.append("|---------|-------|--------|-----|------|-----|---------|")
    for r in univar_results:
        p_str = f'{r["p"]:.4f}' if r['p'] >= 0.001 else '<0.001'
        sig = '***' if r['p'] < 0.001 else ('**' if r['p'] < 0.01 else ('*' if r['p'] < 0.05 else ''))
        lines.append(
            f"| {r['label']} | {r['coef']:+.3f} | [{r['ci_lower']:.3f}, {r['ci_upper']:.3f}] "
            f"| {r['t']:.2f} | {p_str} {sig} | {r['r_squared']:.3f} | {r['adj_r_squared']:.3f} |"
        )
    lines.append("")
    lines.append("> \\*p<0.05, \\*\\*p<0.01, \\*\\*\\*p<0.001")
    lines.append("")

    # --- 多変量OLS ---
    lines.append("## 2. 多変量OLS（気温指標 + SES共変量）")
    lines.append("")

    # 各モデルの比較表
    lines.append("### 2.1 モデル比較")
    lines.append("")
    lines.append("| 気温指標 | β (気温) | p (気温) | Adj. R² | AIC | BIC | F統計量 |")
    lines.append("|---------|----------|----------|---------|-----|-----|---------|")
    for r in multivar_results:
        m = r['model']
        tv = r['temp_var']
        beta = m.params.get(tv, 0)
        p_val = m.pvalues.get(tv, 1)
        p_str = f'{p_val:.4f}' if p_val >= 0.001 else '<0.001'
        sig = '***' if p_val < 0.001 else ('**' if p_val < 0.01 else ('*' if p_val < 0.05 else ''))
        lines.append(
            f"| {VAR_LABELS.get(tv, tv)} | {beta:+.3f} | {p_str} {sig} "
            f"| {r['adj_r_squared']:.3f} | {r['aic']:.1f} | {r['bic']:.1f} | {r['f_stat']:.2f} |"
        )
    lines.append("")

    # ベストモデルの詳細
    if best_multivar:
        bm = best_multivar['model']
        tv = best_multivar['temp_var']
        lines.append(f"### 2.2 最良モデル詳細（{VAR_LABELS.get(tv, tv)}）")
        lines.append("")
        lines.append(f"**選択基準**: 調整R²が最大のモデル (Adj. R² = {best_multivar['adj_r_squared']:.3f})")
        lines.append("")
        lines.append("| 変数 | β係数 | SE | t値 | p値 |")
        lines.append("|------|-------|-----|-----|------|")
        for var_name in bm.params.index:
            if var_name == 'const':
                label = '切片'
            else:
                label = VAR_LABELS.get(var_name, var_name)
            beta = bm.params[var_name]
            se = bm.bse[var_name]
            t = bm.tvalues[var_name]
            p = bm.pvalues[var_name]
            p_str = f'{p:.4f}' if p >= 0.001 else '<0.001'
            sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))
            lines.append(f"| {label} | {beta:+.4f} | {se:.4f} | {t:.2f} | {p_str} {sig} |")
        lines.append("")

    # --- VIF ---
    lines.append("## 3. 多重共線性診断（VIF）")
    lines.append("")
    lines.append(vif_df.to_markdown(index=False))
    lines.append("")
    lines.append("> VIF > 10: 深刻な多重共線性、VIF > 5: 注意、VIF ≤ 5: 問題なし")
    lines.append("")

    # --- 残差診断 ---
    lines.append("## 4. 残差診断（最良モデル）")
    lines.append("")
    lines.append("| 検定 | 統計量 | p値 | 判定 |")
    lines.append("|------|--------|------|------|")

    sw_p = diagnostics.get('shapiro_p', 1.0)
    sw_str = f'{sw_p:.4f}' if sw_p >= 0.001 else '<0.001'
    sw_judge = '○ 正規性あり' if sw_p >= 0.05 else '× 正規性なし'
    lines.append(f"| Shapiro-Wilk（正規性） | W = {diagnostics.get('shapiro_w', 0):.4f} | {sw_str} | {sw_judge} |")

    bp_p = diagnostics.get('bp_p', 1.0)
    bp_str = f'{bp_p:.4f}' if bp_p >= 0.001 else '<0.001'
    bp_judge = '○ 等分散' if bp_p >= 0.05 else '× 不等分散'
    lines.append(f"| Breusch-Pagan（等分散性） | χ² = {diagnostics.get('bp_stat', 0):.3f} | {bp_str} | {bp_judge} |")

    dw = diagnostics.get('durbin_watson', 2.0)
    dw_judge = '○ 自己相関なし' if 1.5 < dw < 2.5 else '△ 自己相関の疑い'
    lines.append(f"| Durbin-Watson（自己相関） | DW = {dw:.3f} | — | {dw_judge} |")

    n_out = diagnostics.get('n_cooks_outliers', 0)
    lines.append(f"| Cook's Distance 外れ値 | {n_out}件 (閾値: 4/n) | — | {'△ 外れ値あり' if n_out > 0 else '○'} |")
    lines.append("")

    # --- Figure一覧 ---
    lines.append("## 5. 生成Figure")
    lines.append("")
    lines.append("| ファイル | 内容 |")
    lines.append("|---------|------|")
    if best_multivar:
        tv = best_multivar['temp_var']
        lines.append(f"| `figures/residual_diagnostics_{tv.lower()}_multi.png` | 最良多変量モデルの残差診断 |")
    for r in univar_results:
        v = r['variable']
        lines.append(f"| `figures/residual_diagnostics_{v.lower()}_uni.png` | {r['label']} 単変量モデルの残差診断 |")
    lines.append("")

    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[OK] 結果出力: {outpath.name}")


# ====================================================================
# Main
# ====================================================================
def main():
    print("=" * 60)
    print("Phase 7: 回帰分析")
    print("=" * 60)

    # --- データ読み込み ---
    df = pd.read_csv(DATA_FILE, encoding='utf-8')
    print(f"[OK] データ読み込み: {df.shape}")
    set_japanese_font()

    # --- 1. 単変量OLS ---
    univar_results = run_univariate_ols(df)

    # --- 2. 多変量OLS ---
    multivar_results = run_all_multivariate(df)

    # ベストモデル選択（Adj. R²最大）
    best_multivar = max(multivar_results, key=lambda x: x['adj_r_squared'])
    best_tv = best_multivar['temp_var']
    print(f"\n  → 最良モデル: {VAR_LABELS.get(best_tv, best_tv)} (Adj.R²={best_multivar['adj_r_squared']:.3f})")

    # --- 3. VIF ---
    print("\n--- 3. VIF（多重共線性）---")
    vif_vars = [best_tv] + [v for v in SES_VARS if v in df.columns]
    vif_df = compute_vif(df, vif_vars)
    print(vif_df.to_string(index=False))

    # --- 4. 残差診断 ---
    print("\n--- 4. 残差診断 ---")

    # 最良多変量モデル
    best_model = best_multivar['model']
    residual_diagnostics(best_model,
                         f'多変量: {VAR_LABELS.get(best_tv, best_tv)} + SES',
                         f'residual_diagnostics_{best_tv.lower()}_multi.png')
    diagnostics = run_diagnostic_tests(best_model)
    print(f"  Shapiro-Wilk: W={diagnostics['shapiro_w']:.4f}, p={diagnostics['shapiro_p']:.4f}")
    print(f"  Breusch-Pagan: χ²={diagnostics['bp_stat']:.3f}, p={diagnostics['bp_p']:.4f}")
    print(f"  Durbin-Watson: {diagnostics['durbin_watson']:.3f}")
    print(f"  Cook's D 外れ値: {diagnostics['n_cooks_outliers']}件")

    # 単変量モデルの残差診断図（有意なもののみ）
    for r in univar_results:
        if r['p'] < 0.05:
            residual_diagnostics(r['model'],
                                 f'単変量: {r["label"]}',
                                 f'residual_diagnostics_{r["variable"].lower()}_uni.png')

    # --- 5. 結果出力 ---
    print("\n--- 5. 結果Markdown出力 ---")
    write_results_markdown(univar_results, multivar_results, vif_df,
                            best_multivar, diagnostics, df)

    print("\n" + "=" * 60)
    print("[DONE] Phase 7 完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
