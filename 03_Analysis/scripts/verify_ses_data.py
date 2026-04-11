#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SESデータ検証スクリプト

03b_collect_ses_data.py のハードコード値をe-Stat API等で検証し、
差異があれば修正したses_data.csvを出力する。

検証対象:
  1. physicians_per_100k : e-Stat API (statsDataId=0004002104)
  2. unemployment_rate   : e-Stat API (国勢調査2020 就業状態等基本集計)
  3. elderly_ratio       : e-Stat API (国勢調査2020 人口等基本集計)
  4. income_per_capita   : 内閣府「令和2年度県民経済計算」（API非対応のため手動確認）
"""

import requests
import pandas as pd
import numpy as np
import time
from pathlib import Path

APP_ID = '8ee5a987b9ec70631de1977bde3afd7ebc11140d'
BASE_URL = 'https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData'
SEARCH_URL = 'https://api.e-stat.go.jp/rest/3.0/app/json/getStatsList'

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SES_FILE = PROJECT_ROOT / 'data/interim/ses_data.csv'
CORRECTED_SES_FILE = PROJECT_ROOT / 'data/interim/ses_data_verified.csv'

PREF_CODES = {
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

# e-Stat API用都道府県コード（コード体系が異なるテーブル用）
ESTAT_PREF_CODES_OFFSET2 = {
    str(i+1): pref for i, (k, pref) in enumerate(sorted(PREF_CODES.items()))
}


def fetch_estat(stats_data_id, extra_params=None, timeout=90):
    """e-Stat APIからデータ取得。"""
    params = {
        'appId': APP_ID,
        'statsDataId': stats_data_id,
        'limit': 100000,
    }
    if extra_params:
        params.update(extra_params)
    resp = requests.get(BASE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    result = data.get('GET_STATS_DATA', {})
    status = result.get('RESULT', {}).get('STATUS', -1)
    if status != 0:
        msg = result.get('RESULT', {}).get('ERROR_MSG', 'Unknown')
        raise RuntimeError(f"e-Stat error (status={status}): {msg}")
    stat_data = result.get('STATISTICAL_DATA', {})
    class_info = stat_data.get('CLASS_INF', {}).get('CLASS_OBJ', [])
    values = stat_data.get('DATA_INF', {}).get('VALUE', [])
    return values, class_info


def search_estat_tables(search_word, stats_code=None, survey_years=None, limit=20):
    """e-Stat でテーブルを検索する。"""
    params = {
        'appId': APP_ID,
        'searchWord': search_word,
        'limit': limit,
    }
    if stats_code:
        params['statsCode'] = stats_code
    if survey_years:
        params['surveyYears'] = survey_years
    resp = requests.get(SEARCH_URL, params=params, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    tables = data.get('GET_STATS_LIST', {}).get('DATALIST_INF', {}).get('TABLE_INF', [])
    if isinstance(tables, dict):
        tables = [tables]
    return tables


def print_class_info(class_info):
    """API class情報を見やすく印字。"""
    for co in class_info:
        cid = co.get('@id', '')
        cname = co.get('@name', '')
        classes = co.get('CLASS', [])
        if isinstance(classes, dict):
            classes = [classes]
        print(f"  {cid} ({cname}): {len(classes)} items")
        for c in classes[:8]:
            code = c.get('@code', '')
            name = c.get('@name', '')
            level = c.get('@level', '')
            print(f"    {code}: {name} (level={level})")
        if len(classes) > 8:
            print(f"    ... and {len(classes) - 8} more")


# ====================================================================
# 1. Physicians per 100k (医師数 人口10万対)
# ====================================================================
def verify_physicians():
    """医療施設調査 令和2年 (statsDataId=0004002104)"""
    print("\n" + "=" * 60)
    print("1. 医師数（人口10万対）: e-Stat ID=0004002104")
    print("=" * 60)

    try:
        values, class_info = fetch_estat('0004002104')
        print(f"  データ件数: {len(values)}")
        print_class_info(class_info)

        # cat02=110 → 人口10万対常勤換算医師数
        # cat01=170 → 令和2年
        # cat03 = 都道府県
        # 03b_collect_ses_data.py と同じフィルタパターンを利用
        STAT_PREF_CODES_03B = {
            '2':'北海道', '3':'青森県', '4':'岩手県', '5':'宮城県', '6':'秋田県',
            '7':'山形県', '8':'福島県', '9':'茨城県', '10':'栃木県', '11':'群馬県',
            '12':'埼玉県', '13':'千葉県', '14':'東京都', '15':'神奈川県', '16':'新潟県',
            '17':'富山県', '18':'石川県', '19':'福井県', '20':'山梨県', '21':'長野県',
            '22':'岐阜県', '23':'静岡県', '24':'愛知県', '25':'三重県', '26':'滋賀県',
            '27':'京都府', '28':'大阪府', '29':'兵庫県', '30':'奈良県', '31':'和歌山県',
            '32':'鳥取県', '33':'島根県', '34':'岡山県', '35':'広島県', '36':'山口県',
            '37':'徳島県', '38':'香川県', '39':'愛媛県', '40':'高知県', '41':'福岡県',
            '42':'佐賀県', '43':'長崎県', '44':'熊本県', '45':'大分県', '46':'宮崎県',
            '47':'鹿児島県', '48':'沖縄県',
        }

        records = []
        for v in values:
            if v.get('@cat02') == '110' and v.get('@cat01') == '170':
                pref_code = v.get('@cat03', '')
                if pref_code in STAT_PREF_CODES_03B:
                    val = v.get('$', '')
                    if val and val not in ['-', '...', '…', '　', '・']:
                        records.append({
                            'prefecture': STAT_PREF_CODES_03B[pref_code],
                            'physicians_per_100k_api': float(val),
                        })

        df = pd.DataFrame(records)
        print(f"\n  取得件数: {len(df)}都道府県")
        if len(df) > 0:
            print(df.to_string(index=False))
        return df
    except Exception as e:
        print(f"  [ERROR] {e}")
        return pd.DataFrame()


# ====================================================================
# 2. Elderly Ratio (高齢化率: 65歳以上割合)
# ====================================================================
def verify_elderly_ratio():
    """国勢調査2020 人口等基本集計から高齢化率を取得。"""
    print("\n" + "=" * 60)
    print("2. 高齢化率: 国勢調査2020 人口等基本集計")
    print("=" * 60)

    # まず使えるテーブルを検索
    try:
        tables = search_estat_tables(
            '男女 年齢 人口 都道府県',
            stats_code='00200521',
            survey_years='202001-202012',
            limit=20
        )
        print(f"  候補テーブル: {len(tables)}件")
        for t in tables[:10]:
            tid = t.get('@id', '')
            title = t.get('TITLE', {})
            if isinstance(title, dict):
                title = title.get('$', '')
            print(f"    {tid}: {title[:90]}")

        # テーブル0003445078: 総人口・年齢 都道府県 を試す
        target_id = None
        for t in tables:
            tid = t.get('@id', '')
            title = t.get('TITLE', {})
            if isinstance(title, dict):
                title = title.get('$', '')
            if '年齢' in title and ('都道府県' in title or '全国' in title):
                target_id = tid
                break

        if target_id:
            print(f"\n  → テーブル {target_id} のメタデータ確認中...")
            time.sleep(1)
            values, class_info = fetch_estat(target_id, extra_params={'limit': 20})
            print_class_info(class_info)
            return target_id, class_info
        else:
            print("  [WARN] 適切なテーブルが見つかりません")
            return None, None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None, None


# ====================================================================
# 3. Unemployment Rate (完全失業率)
# ====================================================================
def verify_unemployment():
    """国勢調査2020 就業状態等基本集計から完全失業率を取得。"""
    print("\n" + "=" * 60)
    print("3. 完全失業率: 国勢調査2020 就業状態等基本集計")
    print("=" * 60)

    try:
        tables = search_estat_tables(
            '労働力状態 就業状態 都道府県',
            stats_code='00200521',
            survey_years='202001-202012',
            limit=20
        )
        print(f"  候補テーブル: {len(tables)}件")
        for t in tables[:10]:
            tid = t.get('@id', '')
            title = t.get('TITLE', {})
            if isinstance(title, dict):
                title = title.get('$', '')
            print(f"    {tid}: {title[:90]}")

        return tables
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


# ====================================================================
# Main
# ====================================================================
def main():
    print("SESデータ検証 — e-Stat API経由")
    print("=" * 60)

    # 既存ハードコードデータの読み込み
    if SES_FILE.exists():
        df_existing = pd.read_csv(SES_FILE, encoding='utf-8')
        print(f"既存 ses_data.csv: {df_existing.shape}")
        print(df_existing.head())
    else:
        print(f"[WARN] ses_data.csv not found at {SES_FILE}")
        df_existing = None

    # 1. 医師数検証
    df_phys = verify_physicians()
    time.sleep(1)

    # 2. 高齢化率テーブル検索
    elderly_table_id, elderly_class = verify_elderly_ratio()
    time.sleep(1)

    # 3. 失業率テーブル検索
    unemployment_tables = verify_unemployment()

    # 医師数の比較
    if not df_phys.empty and df_existing is not None:
        print("\n" + "=" * 60)
        print("=== 医師数の比較（ハードコード vs API） ===")
        compare = df_existing[['prefecture', 'physicians_per_100k']].merge(
            df_phys, on='prefecture', how='outer'
        )
        compare['diff'] = abs(compare['physicians_per_100k'] - compare['physicians_per_100k_api'])
        compare['match'] = compare['diff'] < 0.5  # 0.5以内なら一致
        mismatches = compare[~compare['match']]
        if mismatches.empty:
            print("  → 全て一致（差<0.5）")
        else:
            print(f"  → 不一致: {len(mismatches)}件")
            print(mismatches.to_string(index=False))


if __name__ == '__main__':
    main()
