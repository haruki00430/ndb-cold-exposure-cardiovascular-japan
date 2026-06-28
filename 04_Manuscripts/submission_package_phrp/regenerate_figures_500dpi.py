"""
PHRP投稿用: Figure 1を500 DPIで再生成する
(08_percapita_choropleth.py の dpi=150 → 500 に変更)
"""
import pickle, warnings, os, sys
warnings.filterwarnings('ignore')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, '..', '..', '..', 'src'))

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path(PROJECT_ROOT) / "data" / "interim"
OUT_DIR = Path(SCRIPT_DIR)

POP = {
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

print("Loading data...")
df = pd.read_csv(DATA_DIR / "analysis_dataset.csv", encoding="utf-8")
df['population'] = df['prefecture'].map(POP)
df['cvd_rate_per100k'] = df['cvd_total_quantity'] / df['population'] * 100000

gdf = pickle.load(open(DATA_DIR / "pref_gdf_cache.pkl", 'rb'))
if not isinstance(gdf, gpd.GeoDataFrame):
    gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
gdf = gdf.merge(df[['prefecture', 'cvd_rate_per100k']], on='prefecture', how='inner')

plt.rcParams['font.family'] = ['MS Gothic', 'Yu Gothic', 'Meiryo', 'sans-serif']

print("Generating Figure 1 at 500 DPI...")
fig, ax = plt.subplots(1, 1, figsize=(10, 12))
gdf.plot(column='cvd_rate_per100k', cmap='YlOrRd', linewidth=0.5,
         edgecolor='gray', legend=True, ax=ax,
         legend_kwds={'label': 'CVD Prescription Rate (per 100,000)', 'shrink': 0.6})
ax.set_title('CVD Prescription Rate per 100,000 Population\nby Japanese Prefecture (FY2023)',
             fontsize=14)
ax.axis('off')
plt.tight_layout()

out = OUT_DIR / "Figure1_choropleth_cvd_percapita.png"
plt.savefig(str(out), dpi=500, bbox_inches='tight')
plt.close()
print(f"[OK] Saved: {out}")
print("Figure 1 regenerated at 500 DPI.")
