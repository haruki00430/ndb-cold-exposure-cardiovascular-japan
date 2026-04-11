#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 6: 記述統計・相関分析

都道府県別 analysis_dataset.csv を用いて以下を実施:
  1. 記述統計量（mean, SD, min, Q1, median, Q3, max）
  2. Shapiro-Wilk 正規性検定
  3. Pearson / Spearman 相関行列
  4. 相関係数ヒートマップ（Figure保存）
  5. 主要変数の散布図 + 回帰直線
  6. 結果をMarkdown形式で出力

出力:
  results/descriptive_statistics.md   — 記述統計・相関テーブル
  results/figures/correlation_heatmap.png
  results/figures/scatter_*.png

使用ライブラリ: pandas, numpy, scipy, matplotlib, seaborn, ndb_library
"""

import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import yaml

# --- プロジェクトパス ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT.parents[1] / 'src'))

from ndb_library.viz import set_japanese_font

# --- 設定読み込み ---
CONFIG_FILE = PROJECT_ROOT / 'config' / 'config.yaml'
with open(CONFIG_FILE, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

DATA_FILE   = PROJECT_ROOT / 'data' / 'interim' / 'analysis_dataset.csv'
RESULTS_DIR = PROJECT_ROOT / 'results'
FIG_DIR     = RESULTS_DIR / 'figures'

FIG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DPI = cfg.get('output', {}).get('figures_dpi', 300)

# --- 変数定義 ---
# 主要気温変数（config.yaml の weather_variables.primary）
TEMP_VARS = [
    'Temp_range_annual',   # 年間気温較差
    'Winter_temp_avg',     # 冬季平均気温
    'Temp_std',            # 月別平均気温SD
    'Cold_months_ratio',   # 寒冷月割合
    'Mean_Temp_avg',       # 年間平均気温
]

# 目的変数（CVD処方）
CVD_VARS = [
    'cvd_total_quantity',  # CVD処方量（総数量）
]

# SES共変量
SES_VARS = [
    'physicians_per_100k',  # 人口10万対医師数
    'unemployment_rate',    # 完全失業率
    'elderly_ratio',        # 高齢化率
    'income_per_capita',    # 一人当たり県民所得
]

# 日本語ラベル
VAR_LABELS = {
    'Temp_range_annual': '年間気温較差 (℃)',
    'Winter_temp_avg': '冬季平均気温 (℃)',
    'Temp_std': '気温変動SD (℃)',
    'Cold_months_ratio': '寒冷月割合',
    'Mean_Temp_avg': '年間平均気温 (℃)',
    'cvd_total_quantity': 'CVD処方量（総数量）',
    'physicians_per_100k': '医師数 (10万対)',
    'unemployment_rate': '完全失業率 (%)',
    'elderly_ratio': '高齢化率 (%)',
    'income_per_capita': '県民所得 (万円)',
}


def load_data() -> pd.DataFrame:
    """データ読み込みと基本確認。"""
    df = pd.read_csv(DATA_FILE, encoding='utf-8')
    print(f"[OK] データ読み込み: {df.shape}")
    print(f"  列: {list(df.columns)}")
    return df


def compute_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """記述統計量 + Shapiro-Wilk検定。"""
    all_vars = [v for v in TEMP_VARS + CVD_VARS + SES_VARS if v in df.columns]
    rows = []
    for var in all_vars:
        s = df[var].dropna()
        if len(s) < 3:
            continue
        sw_stat, sw_p = stats.shapiro(s)
        rows.append({
            '変数': VAR_LABELS.get(var, var),
            'N': len(s),
            '平均': round(s.mean(), 2),
            'SD': round(s.std(), 2),
            '最小': round(s.min(), 2),
            'Q1': round(s.quantile(0.25), 2),
            '中央値': round(s.median(), 2),
            'Q3': round(s.quantile(0.75), 2),
            '最大': round(s.max(), 2),
            'Shapiro-Wilk W': round(sw_stat, 4),
            'p値': f'{sw_p:.4f}' if sw_p >= 0.001 else '<0.001',
            '正規性': '○' if sw_p >= 0.05 else '×',
        })
    return pd.DataFrame(rows)


def compute_correlation_matrix(df: pd.DataFrame) -> tuple:
    """Pearson & Spearman 相関行列を計算。"""
    analysis_vars = [v for v in TEMP_VARS + CVD_VARS + SES_VARS if v in df.columns]
    df_sub = df[analysis_vars].dropna()

    pearson_corr = df_sub.corr(method='pearson')
    spearman_corr = df_sub.corr(method='spearman')

    # p値行列（Pearson）
    n = len(df_sub)
    p_matrix = pd.DataFrame(np.zeros((len(analysis_vars), len(analysis_vars))),
                             index=analysis_vars, columns=analysis_vars)
    for i, v1 in enumerate(analysis_vars):
        for j, v2 in enumerate(analysis_vars):
            if i == j:
                p_matrix.iloc[i, j] = 0.0
            else:
                _, p = stats.pearsonr(df_sub[v1], df_sub[v2])
                p_matrix.iloc[i, j] = p

    return pearson_corr, spearman_corr, p_matrix


def plot_correlation_heatmap(corr: pd.DataFrame, p_matrix: pd.DataFrame,
                              title: str, filename: str):
    """相関係数ヒートマップ（有意水準アスタリスク付き）。"""
    set_japanese_font()

    # ラベル変換
    labels = [VAR_LABELS.get(c, c) for c in corr.columns]

    fig, ax = plt.subplots(figsize=(12, 10))

    # アスタリスク付きアノテーション
    annot = np.full(corr.shape, '', dtype=object)
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            r = corr.iloc[i, j]
            p = p_matrix.iloc[i, j]
            stars = ''
            if i != j:
                if p < 0.001:
                    stars = '***'
                elif p < 0.01:
                    stars = '**'
                elif p < 0.05:
                    stars = '*'
            annot[i, j] = f'{r:.2f}{stars}'

    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

    sns.heatmap(corr, mask=mask, annot=annot, fmt='',
                xticklabels=labels, yticklabels=labels,
                cmap='RdBu_r', center=0, vmin=-1, vmax=1,
                square=True, linewidths=0.5, cbar_kws={'shrink': 0.8},
                ax=ax)

    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.yticks(fontsize=9)
    plt.tight_layout()

    outpath = FIG_DIR / filename
    fig.savefig(outpath, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] ヒートマップ保存: {outpath.name}")


def plot_scatter_with_regression(df: pd.DataFrame,
                                  x_var: str, y_var: str,
                                  filename: str):
    """散布図 + 回帰直線 + r, p表示。"""
    set_japanese_font()

    x = df[x_var].dropna()
    y = df.loc[x.index, y_var].dropna()
    common = x.index.intersection(y.index)
    x, y = x.loc[common], y.loc[common]

    if len(x) < 5:
        return

    slope, intercept, r, p, se = stats.linregress(x, y)

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.scatter(x, y, alpha=0.7, edgecolors='white', s=60, c='#2196F3')

    # 回帰直線
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_line, slope * x_line + intercept, 'r-', linewidth=2, alpha=0.8)

    # 95%信頼区間
    n = len(x)
    x_mean = x.mean()
    se_y = np.sqrt(np.sum((y - (slope * x + intercept)) ** 2) / (n - 2))
    ci = stats.t.ppf(0.975, n - 2) * se_y * np.sqrt(
        1 / n + (x_line - x_mean) ** 2 / np.sum((x - x_mean) ** 2)
    )
    ax.fill_between(x_line, slope * x_line + intercept - ci,
                     slope * x_line + intercept + ci,
                     alpha=0.15, color='red')

    # 統計量テキスト
    p_text = f'p < 0.001' if p < 0.001 else f'p = {p:.3f}'
    ax.text(0.05, 0.95, f'r = {r:.3f}\n{p_text}\nn = {n}',
            transform=ax.transAxes, fontsize=11,
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='wheat', alpha=0.8))

    ax.set_xlabel(VAR_LABELS.get(x_var, x_var), fontsize=12)
    ax.set_ylabel(VAR_LABELS.get(y_var, y_var), fontsize=12)
    ax.set_title(f'{VAR_LABELS.get(x_var, x_var)} vs {VAR_LABELS.get(y_var, y_var)}',
                 fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # 都道府県ラベル（外れ値のみ）
    if 'prefecture' in df.columns:
        residuals = y - (slope * x + intercept)
        threshold = residuals.std() * 1.5
        outliers = residuals[residuals.abs() > threshold].index
        for idx in outliers:
            ax.annotate(df.loc[idx, 'prefecture'],
                       (x.loc[idx], y.loc[idx]),
                       fontsize=7, alpha=0.7,
                       xytext=(5, 5), textcoords='offset points')

    plt.tight_layout()
    outpath = FIG_DIR / filename
    fig.savefig(outpath, dpi=DPI, bbox_inches='tight')
    plt.close(fig)
    print(f"[OK] 散布図保存: {outpath.name}")


def format_correlation_for_md(corr: pd.DataFrame, p_matrix: pd.DataFrame,
                                target_var: str) -> str:
    """特定の目的変数に対する相関係数テーブルをMarkdown形式で出力。"""
    labels = {v: VAR_LABELS.get(v, v) for v in corr.index}
    lines = []
    lines.append(f"| 変数 | Pearson r | p値 | 有意性 |")
    lines.append(f"|------|-----------|------|--------|")

    for var in corr.index:
        if var == target_var:
            continue
        r = corr.loc[var, target_var]
        p = p_matrix.loc[var, target_var]
        sig = ''
        if p < 0.001:
            sig = '***'
        elif p < 0.01:
            sig = '**'
        elif p < 0.05:
            sig = '*'
        p_str = f'{p:.4f}' if p >= 0.001 else '<0.001'
        lines.append(f"| {labels.get(var, var)} | {r:.3f} | {p_str} | {sig} |")

    return '\n'.join(lines)


def write_results_markdown(desc_stats: pd.DataFrame,
                            pearson_corr: pd.DataFrame,
                            p_matrix: pd.DataFrame,
                            df: pd.DataFrame):
    """結果をMarkdown形式で出力。"""
    outpath = RESULTS_DIR / 'descriptive_statistics.md'
    lines = []

    lines.append("# 記述統計・相関分析結果")
    lines.append("")
    lines.append(f"**データ**: analysis_dataset.csv (N={len(df)}, 47都道府県)")
    lines.append(f"**解析日**: {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # --- 1. 記述統計 ---
    lines.append("## 1. 記述統計量")
    lines.append("")
    lines.append(desc_stats.to_markdown(index=False))
    lines.append("")
    lines.append("> Shapiro-Wilk検定: ○ = p≥0.05（正規性を棄却できない）、× = p<0.05（正規性を棄却）")
    lines.append("")

    # --- 2. 目的変数との相関 ---
    target = 'cvd_total_quantity'
    if target in pearson_corr.columns:
        lines.append(f"## 2. CVD処方量（10万対）との相関")
        lines.append("")
        lines.append(format_correlation_for_md(pearson_corr, p_matrix, target))
        lines.append("")
        lines.append("> \\*p<0.05, \\*\\*p<0.01, \\*\\*\\*p<0.001")
        lines.append("")

    # --- 3. 主要な発見 ---
    lines.append("## 3. 主要な発見")
    lines.append("")

    # 高相関ペアを自動抽出
    if target in pearson_corr.columns:
        target_corrs = pearson_corr[target].drop(target, errors='ignore')
        significant = []
        for var, r in target_corrs.items():
            p = p_matrix.loc[var, target]
            if p < 0.05:
                label = VAR_LABELS.get(var, var)
                direction = '正の相関' if r > 0 else '負の相関'
                significant.append((label, r, p, direction))

        if significant:
            significant.sort(key=lambda x: abs(x[1]), reverse=True)
            for label, r, p, direction in significant:
                p_str = f'p < 0.001' if p < 0.001 else f'p = {p:.4f}'
                lines.append(f"- **{label}**: {direction} (r = {r:.3f}, {p_str})")
        else:
            lines.append("- CVD処方量と有意な相関を示す変数なし")
    lines.append("")

    # --- 4. Figure一覧 ---
    lines.append("## 4. 生成Figure")
    lines.append("")
    lines.append("| ファイル | 内容 |")
    lines.append("|---------|------|")
    lines.append("| `figures/correlation_heatmap.png` | Pearson相関行列ヒートマップ |")
    for t_var in TEMP_VARS:
        if t_var in df.columns and target in df.columns:
            safe = t_var.lower()
            lines.append(f"| `figures/scatter_{safe}_vs_cvd.png` | {VAR_LABELS.get(t_var, t_var)} vs CVD処方量 |")
    lines.append("")

    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"[OK] 結果出力: {outpath.name}")


def main():
    print("=" * 60)
    print("Phase 6: 記述統計・相関分析")
    print("=" * 60)

    # --- データ読み込み ---
    df = load_data()

    # --- 日本語フォント設定 ---
    set_japanese_font()

    # --- 1. 記述統計 ---
    print("\n--- 1. 記述統計量 ---")
    desc_stats = compute_descriptive_stats(df)
    print(desc_stats.to_string(index=False))

    # --- 2. 相関分析 ---
    print("\n--- 2. 相関分析 ---")
    pearson_corr, spearman_corr, p_matrix = compute_correlation_matrix(df)

    # 目的変数との相関を表示
    target = 'cvd_total_quantity'
    if target in pearson_corr.columns:
        print(f"\n  {VAR_LABELS.get(target, target)} との相関:")
        for var in TEMP_VARS + SES_VARS:
            if var in pearson_corr.index:
                r = pearson_corr.loc[var, target]
                p = p_matrix.loc[var, target]
                sig = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else ''))
                print(f"    {VAR_LABELS.get(var, var):25s}: r={r:+.3f} (p={p:.4f}) {sig}")

    # --- 3. ヒートマップ ---
    print("\n--- 3. 相関ヒートマップ ---")
    plot_correlation_heatmap(pearson_corr, p_matrix,
                              '気温変動 × CVD処方 × SES 相関行列 (Pearson)',
                              'correlation_heatmap.png')

    # --- 4. 散布図 ---
    print("\n--- 4. 散布図（気温指標 vs CVD処方量）---")
    if target in df.columns:
        for t_var in TEMP_VARS:
            if t_var in df.columns:
                safe_name = t_var.lower()
                plot_scatter_with_regression(df, t_var, target,
                                             f'scatter_{safe_name}_vs_cvd.png')

        # SES vs CVD散布図も追加
        for s_var in SES_VARS:
            if s_var in df.columns:
                safe_name = s_var.lower()
                plot_scatter_with_regression(df, s_var, target,
                                             f'scatter_{safe_name}_vs_cvd.png')

    # --- 5. 結果出力 ---
    print("\n--- 5. 結果Markdown出力 ---")
    write_results_markdown(desc_stats, pearson_corr, p_matrix, df)

    print("\n" + "=" * 60)
    print("[DONE] Phase 6 完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
