#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3b: SES（社会経済）データ収集 — e-Stat API使用

都道府県別の社会経済共変量をe-Stat APIから取得し、
既存の analysis_dataset.csv に統合する。

取得データ（全てe-Stat API経由、ハードコード値なし）:
  1. 医師数（人口10万対）   : 医療施設調査 令和2年  statsDataId=0004002104
  2. 完全失業率             : 国勢調査2020 就業状態等基本集計 statsDataId=0003450538
  3. 高齢化率（65歳以上%）  : 国勢調査2020 人口等基本集計   statsDataId=0003410381
  4. 一人当たり県民所得      : 内閣府「令和2年度県民経済計算」※APIなし、公式CSV値

出力:
  data/interim/ses_data.csv          (47×5)
  data/interim/analysis_dataset.csv  (上書き更新)
"""

import requests
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE  = PROJECT_ROOT / 'config/config.yaml'

with open(CONFIG_FILE, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

E_STAT_APP_ID    = '8ee5a987b9ec70631de1977bde3afd7ebc11140d'
E_STAT_BASE_URL  = 'https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData'

ANALYSIS_FILE    = PROJECT_ROOT / 'data/interim/analysis_dataset.csv'
OUTPUT_SES_FILE  = PROJECT_ROOT / 'data/interim/ses_data.csv'

# 都道府県コードマッピング（e-Stat area codes: XX000形式）
PREF_AREA_CODES = {
    '01000': '北海道', '02000': '青森県', '03000': '岩手県', '04000': '宮城県',
    '05000': '秋田県', '06000': '山形県', '07000': '福島県', '08000': '茨城県',
    '09000': '栃木県', '10000': '群馬県', '11000': '埼玉県', '12000': '千葉県',
    '13000': '東京都', '14000': '神奈川県', '15000': '新潟県', '16000': '富山県',
    '17000': '石川県', '18000': '福井県', '19000': '山梨県', '20000': '長野県',
    '21000': '岐阜県', '22000': '静岡県', '23000': '愛知県', '24000': '三重県',
    '25000': '滋賀県', '26000': '京都府', '27000': '大阪府', '28000': '兵庫県',
    '29000': '奈良県', '30000': '和歌山県', '31000': '鳥取県', '32000': '島根県',
    '33000': '岡山県', '34000': '広島県', '35000': '山口県', '36000': '徳島県',
    '37000': '香川県', '38000': '愛媛県', '39000': '高知県', '40000': '福岡県',
    '41000': '佐賀県', '42000': '長崎県', '43000': '熊本県', '44000': '大分県',
    '45000': '宮崎県', '46000': '鹿児島県', '47000': '沖縄県',
}

# 医療施設調査用コード体系（2〜48）
STAT_PREF_CODES_MED = {str(i+1): pref for i, (k, pref) in enumerate(sorted(PREF_AREA_CODES.items()))}


def fetch_estat_data(stats_data_id: str, params_extra: dict = None) -> list:
    """e-Stat APIからデータを取得する。"""
    params = {
        'appId': E_STAT_APP_ID,
        'statsDataId': stats_data_id,
        'limit': 100000,
    }
    if params_extra:
        params.update(params_extra)
    resp = requests.get(E_STAT_BASE_URL, params=params, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    result = data.get('GET_STATS_DATA', {})
    status = result.get('RESULT', {}).get('STATUS', -1)
    if status != 0:
        msg = result.get('RESULT', {}).get('ERROR_MSG', 'Unknown error')
        raise RuntimeError(f"e-Stat API error (status={status}): {msg}")
    values = result.get('STATISTICAL_DATA', {}).get('DATA_INF', {}).get('VALUE', [])
    return values


# ====================================================================
# 1. 医師数（人口10万対）
# ====================================================================
def get_physicians_per_100k() -> pd.DataFrame:
    """
    医療施設調査 令和2年（2020年）— 人口10万対常勤換算医師数
    statsDataId: 0004002104
    cat02=110 → 人口10万対常勤換算医師数
    cat01=170 → 令和2年
    cat03 → 都道府県
    """
    print("[INFO] 医師数（人口10万対）をe-Stat APIから取得中...")
    values = fetch_estat_data('0004002104')
    records = []
    for v in values:
        if v.get('@cat02') == '110' and v.get('@cat01') == '170':
            pref_code = v.get('@cat03', '')
            if pref_code in STAT_PREF_CODES_MED:
                val = v.get('$', '')
                if val and val not in ['-', '...', '…', '　', '・']:
                    records.append({
                        'prefecture': STAT_PREF_CODES_MED[pref_code],
                        'physicians_per_100k': float(val),
                    })
    df = pd.DataFrame(records)
    print(f"[OK] 医師数データ取得: {len(df)}都道府県 (e-Stat ID:0004002104)")
    return df


# ====================================================================
# 2. 完全失業率 — 国勢調査2020 就業状態等基本集計
# ====================================================================
def get_unemployment_rate() -> pd.DataFrame:
    """
    国勢調査2020 就業状態等基本集計
    statsDataId: 0003450538

    フィルタ:
      cat01=0  → 国籍総数
      cat02=0  → 男女総数
      cat03=00 → 年齢総数（15歳以上）
      cat04=1  → 労働力人口
      cat04=12 → 完全失業者
      area=XX000 → 都道府県

    失業率 = 完全失業者 / 労働力人口 × 100
    """
    print("[INFO] 完全失業率をe-Stat APIから取得中...")
    values = fetch_estat_data('0003450538', {
        'cdCat01': '0',
        'cdCat02': '0',
        'cdCat03': '00',
    })
    print(f"  取得レコード数: {len(values)}")

    pref_labor = {}
    pref_unemployed = {}
    for v in values:
        area = v.get('@area', '')
        cat04 = v.get('@cat04', '')
        val_str = v.get('$', '')

        if area not in PREF_AREA_CODES:
            continue
        if val_str in ['-', '...', '*', '', 'x', 'X']:
            continue
        try:
            val = float(val_str)
        except ValueError:
            continue

        pref = PREF_AREA_CODES[area]
        if cat04 == '1':
            pref_labor[pref] = val
        elif cat04 == '12':
            pref_unemployed[pref] = val

    records = []
    for pref in sorted(pref_labor.keys()):
        if pref in pref_unemployed and pref_labor[pref] > 0:
            rate = round(pref_unemployed[pref] / pref_labor[pref] * 100, 1)
            records.append({
                'prefecture': pref,
                'unemployment_rate': rate,
            })

    df = pd.DataFrame(records)
    print(f"[OK] 完全失業率: {len(df)}都道府県 (e-Stat ID:0003450538, 国勢調査2020)")
    return df


# ====================================================================
# 3. 高齢化率（65歳以上人口割合）
# ====================================================================
def get_elderly_ratio() -> pd.DataFrame:
    """
    国勢調査2020 人口等基本集計（時系列）
    statsDataId: 0003410381

    コード体系（2026-03-04確認済み）:
      tab=020        → 人口
      cat01=100      → 総数（男女計）
      cat02=100      → 総数（全年齢）
      cat02=400      → （再掲）65歳以上
      time=2020000000 → 2020年
      area=XX000     → 都道府県

    高齢化率 = 65歳以上人口 / 総人口 × 100
    """
    print("[INFO] 高齢化率をe-Stat APIから取得中...")
    values = fetch_estat_data('0003410381', {
        'cdTab': '020',           # 人口
        'cdCat01': '100',         # 男女総数
        'cdCat02': '100,400',     # 総数 + 65歳以上
        'cdTime': '2020000000',   # 2020年
    })
    print(f"  取得レコード数: {len(values)}")

    pref_total = {}
    pref_65plus = {}

    for v in values:
        area = v.get('@area', '')
        cat02 = v.get('@cat02', '')
        val_str = v.get('$', '')

        if area not in PREF_AREA_CODES:
            continue
        if val_str in ['-', '...', '*', '', 'x', 'X']:
            continue
        try:
            val = float(val_str)
        except ValueError:
            continue

        pref = PREF_AREA_CODES[area]
        if cat02 == '100':
            pref_total[pref] = val
        elif cat02 == '400':
            pref_65plus[pref] = val

    records = []
    for pref in sorted(pref_total.keys()):
        if pref in pref_65plus and pref_total[pref] > 0:
            ratio = round(pref_65plus[pref] / pref_total[pref] * 100, 1)
            records.append({
                'prefecture': pref,
                'elderly_ratio': ratio,
            })

    df = pd.DataFrame(records)
    print(f"[OK] 高齢化率: {len(df)}都道府県 (e-Stat ID:0003410381, 国勢調査2020)")
    return df


# ====================================================================
# 4. 一人当たり県民所得（万円）
# ====================================================================
def get_income_per_capita() -> pd.DataFrame:
    """
    都道府県別一人当たり県民所得（万円）
    出典: 内閣府「令和2年度県民経済計算」総括表7
    https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/main_2020.html
    ファイル: data/raw/soukatu7.xlsx (Sheet: 実数)

    Excel構造（2026-03-04確認済み）:
      Row 3: ヘッダー行（都道府県, 平成23年度, ..., 令和2年度）
      Row 4+: データ行（都道府県コード01〜47, 1人当たり県民所得（千円））
      Col 0: 都道府県コード
      Col 1: 都道府県名（結合セルのためNaN、Col 0に名前が入る場合もあり）
      Col 12: 令和2年度（2020年度）の値（千円単位）
    """
    INCOME_FILE = PROJECT_ROOT / 'data/raw/soukatu7.xlsx'
    print(f"[INFO] 一人当たり県民所得を公式Excelから読み込み: {INCOME_FILE.name}")

    if not INCOME_FILE.exists():
        raise FileNotFoundError(
            f"県民所得Excelが見つかりません: {INCOME_FILE}\n"
            "  → https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2020/soukatu7.xlsx\n"
            "    からダウンロードし、data/raw/ に配置してください。"
        )

    df_raw = pd.read_excel(INCOME_FILE, sheet_name='実数', header=None)

    # ヘッダー行（Row 3）から令和2年度の列インデックスを特定
    header_row = df_raw.iloc[3]
    col_2020 = None
    for i, h in enumerate(header_row):
        if pd.notna(h) and '令和2年度' in str(h):
            col_2020 = i
            break
    if col_2020 is None:
        raise ValueError("令和2年度の列が見つかりません。Excelの構造を確認してください。")

    # 都道府県コード（01〜47）とマッピング
    PREF_CODE_TO_NAME = {
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

    records = []
    for i in range(4, len(df_raw)):
        code_raw = df_raw.iloc[i, 0]
        if pd.isna(code_raw):
            continue
        code = str(int(code_raw)).zfill(2) if isinstance(code_raw, (int, float)) else str(code_raw).strip().zfill(2)
        if code not in PREF_CODE_TO_NAME:
            continue
        val = df_raw.iloc[i, col_2020]
        if pd.isna(val):
            continue
        # 千円 → 万円 に変換（例: 2682千円 → 268.2万円）
        income_man = round(float(val) / 10, 1)
        records.append({
            'prefecture': PREF_CODE_TO_NAME[code],
            'income_per_capita': income_man,
        })

    df = pd.DataFrame(records)
    print(f"[OK] 県民所得データ: {len(df)}都道府県（出典: 内閣府 県民経済計算2020, soukatu7.xlsx）")
    return df


# ====================================================================
# Main
# ====================================================================
def main():
    print("=" * 60)
    print("Step 3b: SESデータ収集・統合（e-Stat API版）")
    print("=" * 60)

    # --- SESデータ取得 ---
    df_physicians = get_physicians_per_100k()
    time.sleep(1)

    df_unemployment = get_unemployment_rate()
    time.sleep(1)

    df_elderly = get_elderly_ratio()
    time.sleep(1)

    df_income = get_income_per_capita()

    # --- SESデータ統合 ---
    df_ses = df_physicians.copy()
    df_ses = df_ses.merge(df_unemployment, on='prefecture', how='outer')
    df_ses = df_ses.merge(df_elderly,     on='prefecture', how='outer')
    df_ses = df_ses.merge(df_income,      on='prefecture', how='outer')

    missing = df_ses.isnull().sum().sum()
    if missing > 0:
        print(f"\n[WARN] SESデータに欠損値あり: {missing}件")
        print(df_ses[df_ses.isnull().any(axis=1)])
    else:
        print(f"\n[OK] SESデータ統合完了: {df_ses.shape} (欠損なし)")

    # SES単体を保存
    OUTPUT_SES_FILE.parent.mkdir(parents=True, exist_ok=True)
    df_ses.to_csv(OUTPUT_SES_FILE, index=False, encoding='utf-8')
    print(f"[OK] SESデータ出力: {OUTPUT_SES_FILE}")

    # --- analysis_dataset.csv に統合 ---
    if not ANALYSIS_FILE.exists():
        print(f"[ERROR] {ANALYSIS_FILE} が存在しません。先に 03_integrate_data.py を実行してください。")
        return

    df_main = pd.read_csv(ANALYSIS_FILE, encoding='utf-8')
    print(f"\n[INFO] 既存データセット: {df_main.shape}")

    # 既存列にSESが含まれていれば上書きのため一旦除去
    ses_cols = ['physicians_per_100k', 'unemployment_rate', 'elderly_ratio', 'income_per_capita']
    df_main = df_main.drop(columns=[c for c in ses_cols if c in df_main.columns])

    df_merged = pd.merge(df_main, df_ses, on='prefecture', how='left')

    missing_after = df_merged[ses_cols].isnull().sum().sum()
    if missing_after > 0:
        print(f"[WARN] 統合後のSES欠損: {missing_after}件（prefecture名の不一致を確認してください）")
        unmatched = df_merged[df_merged[ses_cols[0]].isnull()]['prefecture'].tolist()
        print(f"       未マッチ: {unmatched}")
    else:
        print(f"[OK] 統合後 analysis_dataset.csv: {df_merged.shape} (欠損なし)")

    df_merged.to_csv(ANALYSIS_FILE, index=False, encoding='utf-8')
    print(f"[OK] analysis_dataset.csv 更新完了: {ANALYSIS_FILE}")
    print(f"     列: {list(df_merged.columns)}")
    print()
    print("[OK] ---- データソース記録 ----")
    print("  physicians_per_100k : 医療施設調査 令和2年（e-Stat API, ID:0004002104）")
    print("  unemployment_rate   : 国勢調査2020 就業状態等基本集計（e-Stat API, ID:0003450538）")
    print("  elderly_ratio       : 国勢調査2020 人口等基本集計（e-Stat API, ID:0003410381）")
    print("  income_per_capita   : 県民経済計算2020年度（内閣府, 公式発表値）")


if __name__ == '__main__':
    main()
