#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3: データ統合

気象データ（weather_data_prefecture.csv）と
CVD処方データ（cvd_prescription.csv）を都道府県名で結合し、
解析用データセットを作成する。

入力:
  data/interim/weather_data_prefecture.csv   (47行×8列)
  data/interim/cvd_prescription.csv          (47行×7列)

出力:
  data/interim/analysis_dataset.csv
"""

import pandas as pd
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE  = PROJECT_ROOT / 'config/config.yaml'

with open(CONFIG_FILE, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

WEATHER_FILE = PROJECT_ROOT / 'data/interim/weather_data_prefecture.csv'
CVD_FILE     = PROJECT_ROOT / 'data/interim/cvd_prescription.csv'
OUTPUT_FILE  = PROJECT_ROOT / 'data/interim/analysis_dataset.csv'


def main():
    # --- 気象データ ---
    weather = pd.read_csv(WEATHER_FILE, encoding='utf-8')
    print(f"[OK] 気象データ: {weather.shape}")
    print(f"  列: {list(weather.columns)}")

    # --- CVD処方データ ---
    cvd = pd.read_csv(CVD_FILE, encoding='utf-8')
    print(f"[OK] CVD処方データ: {cvd.shape}")
    print(f"  列: {list(cvd.columns)}")

    # --- 気象 × CVD 結合 ---
    dataset = pd.merge(weather, cvd, on='prefecture', how='inner')
    print(f"\n[INFO] 気象×CVD結合結果: {dataset.shape}")

    if len(dataset) < 47:
        missing_w = set(weather['prefecture']) - set(dataset['prefecture'])
        missing_c = set(cvd['prefecture']) - set(dataset['prefecture'])
        if missing_w:
            print(f"  [WARN] 気象側のみ: {missing_w}")
        if missing_c:
            print(f"  [WARN] CVD側のみ: {missing_c}")

    # --- SESデータ統合 ---
    SES_FILE = PROJECT_ROOT / 'data/interim/ses_data.csv'
    if SES_FILE.exists():
        ses = pd.read_csv(SES_FILE, encoding='utf-8')
        print(f"\n[OK] SESデータ: {ses.shape}")
        print(f"  列: {list(ses.columns)}")
        dataset = pd.merge(dataset, ses, on='prefecture', how='left')
        ses_cols = ['physicians_per_100k', 'unemployment_rate', 'elderly_ratio', 'income_per_capita']
        ses_missing = dataset[ses_cols].isnull().sum().sum()
        if ses_missing > 0:
            print(f"  [WARN] SES欠損: {ses_missing}件")
        else:
            print(f"  [OK] SES統合完了（欠損なし）")
    else:
        print(f"\n[WARN] SESデータが見つかりません: {SES_FILE}")
        print("  → 先に 03b_collect_ses_data.py を実行してください")

    # --- 出力 ---
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"\n[OK] 出力: {OUTPUT_FILE}  shape={dataset.shape}")
    print(f"  列一覧: {list(dataset.columns)}")
    print(f"\n--- 基本統計量（気温指標＋CVD合計） ---")
    key_cols = [c for c in ['Temp_range_annual', 'Winter_temp_avg', 'Temp_std',
                            'Cold_months_ratio', 'cvd_total_quantity'] if c in dataset.columns]
    if key_cols:
        print(dataset[key_cols].describe().to_string())


if __name__ == '__main__':
    main()
