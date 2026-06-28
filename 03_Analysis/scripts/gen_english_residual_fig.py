# -*- coding: utf-8 -*-
"""
gen_english_residual_fig.py
per capita CVD prescription rate × cold month ratio + SES モデルの
残差診断図を英語ラベルで生成する。
出力: results/figures/residual_diagnostics_cold_months_ratio_percapita_en.png
"""
import sys, warnings
warnings.filterwarnings('ignore')
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_ROOT / "data" / "interim" / "analysis_dataset.csv"
FIG_OUT = PROJECT_ROOT / "results" / "figures" / "residual_diagnostics_cold_months_ratio_percapita_en.png"

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

# --- Load & prepare ---
df = pd.read_csv(DATA_FILE, encoding='utf-8')
df['population'] = df['prefecture'].map(POPULATION_2020)
df['cvd_rate_per100k'] = df['cvd_total_quantity'] / df['population'] * 100000

dep_var = 'cvd_rate_per100k'
exp_var = 'Cold_months_ratio'
ses_vars = ['physicians_per_100k', 'unemployment_rate', 'elderly_ratio', 'income_per_capita']
all_vars = [exp_var] + ses_vars

sub = df[[dep_var] + all_vars].dropna()
X = sm.add_constant(sub[all_vars])
model = sm.OLS(sub[dep_var], X).fit()

print(f"Model: {dep_var} ~ {exp_var} + SES (N={int(model.nobs)})")
print(f"R2={model.rsquared:.4f}, Adj.R2={model.rsquared_adj:.4f}")
for v in all_vars:
    print(f"  {v}: β={model.params[v]:.4f}, p={model.pvalues[v]:.4f}")

sw_stat, sw_p = sp_stats.shapiro(model.resid)
bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, model.model.exog)
dw = durbin_watson(model.resid)
print(f"Shapiro-Wilk W={sw_stat:.4f} p={sw_p:.4f}")
print(f"Breusch-Pagan chi2={bp_stat:.3f} p={bp_p:.4f}")
print(f"Durbin-Watson={dw:.3f}")

# --- English residual diagnostics figure ---
resid = model.resid
fitted = model.fittedvalues
influence = model.get_influence()
std_resid = influence.resid_studentized_internal
cooks_d = influence.cooks_distance[0]

matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})

fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# (1) Residuals vs Fitted
ax = axes[0, 0]
ax.scatter(fitted, resid, alpha=0.7, edgecolors='white', s=50, color='steelblue')
ax.axhline(0, color='red', linestyle='--', alpha=0.7)
ax.set_xlabel('Fitted Values', fontsize=10)
ax.set_ylabel('Residuals', fontsize=10)
ax.set_title('Residuals vs Fitted', fontsize=11, fontweight='bold')
ax.grid(True, alpha=0.3)

# (2) Normal Q-Q
ax = axes[0, 1]
sp_stats.probplot(std_resid, dist='norm', plot=ax)
ax.set_title('Normal Q-Q Plot', fontsize=11, fontweight='bold')
ax.get_lines()[1].set_color('red')
ax.grid(True, alpha=0.3)

# (3) Scale-Location
ax = axes[1, 0]
ax.scatter(fitted, np.sqrt(np.abs(std_resid)), alpha=0.7, edgecolors='white', s=50, color='steelblue')
ax.set_xlabel('Fitted Values', fontsize=10)
ax.set_ylabel('√|Standardized Residuals|', fontsize=10)
ax.set_title('Scale-Location', fontsize=11, fontweight='bold')
ax.grid(True, alpha=0.3)

# (4) Cook's Distance
ax = axes[1, 1]
ax.stem(range(len(cooks_d)), cooks_d, markerfmt=',', linefmt='C0-', basefmt='k-')
threshold = 4 / len(cooks_d)
ax.axhline(threshold, color='red', linestyle='--', alpha=0.7,
           label=f'4/n = {threshold:.3f}')
ax.set_xlabel('Observation Index', fontsize=10)
ax.set_ylabel("Cook's Distance", fontsize=10)
ax.set_title("Cook's Distance", fontsize=11, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)

fig.suptitle(
    'Residual Diagnostics: Multivariable OLS\n'
    '(Cold Month Ratio + SES → CVD Prescription Rate per 100,000)',
    fontsize=12, fontweight='bold', y=1.02
)
plt.tight_layout()
fig.savefig(FIG_OUT, dpi=300, bbox_inches='tight')
plt.close(fig)
print(f"Saved: {FIG_OUT}")
