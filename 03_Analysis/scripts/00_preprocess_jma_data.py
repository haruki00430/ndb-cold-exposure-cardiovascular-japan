#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 0: JMA気象データ前処理（横長→縦長変換）
rainfall_depressionプロジェクトの同名スクリプトをほぼ転用。
気温変数の集計列を追加。

入力:
  data/raw/weather/jma_monthly_YYYY_YYYY.csv (Shift-JIS, 横長)

出力:
  data/interim/weather_monthly_long.csv (UTF-8, 縦長)

  列: prefecture, year, month, Precipitation_mm, Sunshine_hours,
      Cloud_Amount, Mean_Temp, Mean_Humidity
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yaml

# ================================================
# 設定
# ================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE  = PROJECT_ROOT / 'config/config.yaml'

with open(CONFIG_FILE, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

OUTPUT_FILE = PROJECT_ROOT / 'data/interim/weather_monthly_long.csv'

# 地点→都道府県マッピング（rainfall_depressionから転用）
STATION_TO_PREF = {
    '札幌': '北海道', '青森': '青森県', '盛岡': '岩手県', '仙台': '宮城県',
    '秋田': '秋田県', '山形': '山形県', '福島': '福島県', '水戸': '茨城県',
    '宇都宮': '栃木県', '前橋': '群馬県', '熊谷': '埼玉県', '千葉': '千葉県',
    '東京': '東京都', '横浜': '神奈川県', '新潟': '新潟県', '富山': '富山県',
    '金沢': '石川県', '福井': '福井県', '甲府': '山梨県', '長野': '長野県',
    '岐阜': '岐阜県', '静岡': '静岡県', '名古屋': '愛知県', '津': '三重県',
    '彦根': '滋賀県', '京都': '京都府', '大阪': '大阪府', '神戸': '兵庫県',
    '奈良': '奈良県', '和歌山': '和歌山県', '鳥取': '鳥取県', '松江': '島根県',
    '岡山': '岡山県', '広島': '広島県', '下関': '山口県', '徳島': '徳島県',
    '高松': '香川県', '松山': '愛媛県', '高知': '高知県', '福岡': '福岡県',
    '佐賀': '佐賀県', '長崎': '長崎県', '熊本': '熊本県', '大分': '大分県',
    '宮崎': '宮崎県', '鹿児島': '鹿児島県', '那覇': '沖縄県'
}
STATION_ORDER = list(STATION_TO_PREF.keys())

# JMA CSV列インデックス定義（各地点17列）
COL_PRECIP   = 0
COL_SUNSHINE = 4
COL_CLOUD    = 8
COL_TEMP     = 11
COL_HUMIDITY = 14
COLS_PER_STATION = 17


def parse_jma_csv(filepath: Path) -> pd.DataFrame:
    """JMA横長CSV→縦長DataFrameに変換"""
    # データは7行目（1-indexed）から始まる → 0-indexで6行スキップ
    raw = pd.read_csv(filepath, encoding='shift-jis', header=None, skiprows=6, low_memory=False)
    records = []
    for _, row in raw.iterrows():
        try:
            ym = str(row.iloc[0]).strip()
            if '/' not in ym:
                continue
            year, month = ym.split('/')
            year, month = int(year), int(month)
        except (ValueError, IndexError):
            continue

        for i, station in enumerate(STATION_ORDER):
            base = 1 + i * COLS_PER_STATION
            def safe_float(idx):
                try:
                    return float(str(row.iloc[base + idx]).replace(')', '').strip())
                except (ValueError, IndexError):
                    return np.nan

            records.append({
                'prefecture': STATION_TO_PREF[station],
                'station':    station,
                'year':       year,
                'month':      month,
                'Precipitation_mm': safe_float(COL_PRECIP),
                'Sunshine_hours':   safe_float(COL_SUNSHINE),
                'Cloud_Amount':     safe_float(COL_CLOUD),
                'Mean_Temp':        safe_float(COL_TEMP),
                'Mean_Humidity':    safe_float(COL_HUMIDITY),
            })
    return pd.DataFrame(records)


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 入力CSV探索（data/raw/weather/*.csv を全て読む）
    weather_dir = PROJECT_ROOT / 'data/raw/weather'
    csv_files = sorted(weather_dir.glob('*.csv'))
    if not csv_files:
        print(f"[ERROR] 気象CSVが見つかりません: {weather_dir}")
        print("  気象庁サイトからダウンロードして data/raw/weather/ に配置してください。")
        return

    dfs = [parse_jma_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.sort_values(['prefecture', 'year', 'month']).reset_index(drop=True)

    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"[OK] 出力: {OUTPUT_FILE}  shape={df.shape}")
    print(f"  都道府県数: {df['prefecture'].nunique()}")
    print(f"  期間: {df['year'].min()}/{df['month'].min():02d} 〜 {df['year'].max()}/{df['month'].max():02d}")


if __name__ == '__main__':
    main()
