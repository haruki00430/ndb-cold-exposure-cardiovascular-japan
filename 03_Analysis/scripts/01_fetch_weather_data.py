#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1: 気象変数集計（都道府県別）

縦長気象データから気温変動指標を計算する。

入力:  data/interim/weather_monthly_long.csv
出力:  data/interim/weather_data_prefecture.csv

主要変数:
  - Temp_range_annual  : 年間気温較差（最高月平均 − 最低月平均、℃）
  - Winter_temp_avg    : 冬季平均気温（12〜2月平均、℃）
  - Temp_std           : 月別平均気温の標準偏差（変動大きさの指標）
  - Cold_months_ratio  : 月平均気温 < threshold ℃ の月数比率
  - Mean_Temp_avg      : 年間平均気温（℃）
  - Sunshine_hours_annual: 年間日照時間（時間/年）
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE  = PROJECT_ROOT / 'config/config.yaml'

with open(CONFIG_FILE, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

INPUT_FILE  = PROJECT_ROOT / 'data/interim/weather_monthly_long.csv'
OUTPUT_FILE = PROJECT_ROOT / 'data/interim/weather_data_prefecture.csv'

WINTER_MONTHS      = cfg['analysis']['winter_months']
COLD_THRESHOLD     = cfg['analysis']['cold_temp_threshold']


def main():
    if not INPUT_FILE.exists():
        print(f"[ERROR] {INPUT_FILE} が存在しません。先に 00_preprocess_jma_data.py を実行してください。")
        return

    df = pd.read_csv(INPUT_FILE, encoding='utf-8')

    # rainfallのCSVは大文字列名（Prefecture, Month等）
    pref_col  = 'Prefecture' if 'Prefecture' in df.columns else 'prefecture'
    month_col = 'Month'      if 'Month'      in df.columns else 'month'
    temp_col  = 'Mean_Temp'
    sun_col   = 'Sunshine_hours'
    rain_col  = 'Precipitation_mm'

    records = []
    for pref, grp in df.groupby(pref_col):
        temp_monthly = grp[temp_col].values

        # 気温較差: 月平均最高 − 月平均最低
        temp_max = grp.groupby(month_col)[temp_col].mean().max()
        temp_min = grp.groupby(month_col)[temp_col].mean().min()

        # 冬季
        winter = grp[grp[month_col].isin(WINTER_MONTHS)]
        winter_temp = winter[temp_col].mean()

        # 冷月比率
        cold_ratio = (temp_monthly < COLD_THRESHOLD).sum() / len(temp_monthly)

        records.append({
            'prefecture':              pref,
            'Mean_Temp_avg':           grp[temp_col].mean(),
            'Temp_range_annual':       temp_max - temp_min,
            'Winter_temp_avg':         winter_temp,
            'Temp_std':                grp[temp_col].std(),
            'Cold_months_ratio':       cold_ratio,
            'Sunshine_hours_annual':   grp[sun_col].sum() / len(grp) * 12,
            'Precipitation_mm_annual': grp[rain_col].sum() / len(grp) * 12,
        })

    result = pd.DataFrame(records).sort_values('prefecture').reset_index(drop=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"[OK] 出力: {OUTPUT_FILE}  shape={result.shape}")
    print(result[['prefecture', 'Temp_range_annual', 'Winter_temp_avg', 'Temp_std']].to_string(index=False))


if __name__ == '__main__':
    main()
