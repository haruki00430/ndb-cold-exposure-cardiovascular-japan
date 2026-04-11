#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 2: NDB循環器疾患関連処方データ抽出

NDB Open Data 第10回 05_処方薬 から循環器関連の薬効分類を
都道府県別に集計する。

NDB処方薬Excelの構造（inspect_ndb_structure.py で確認済み）:
  - Shape: (8285, 56)
  - Col0: 薬効分類コード（3桁: 112, 214, 217, ...）
  - Col1: 薬効分類名称
  - Col2: 医薬品コード
  - Col3: 医薬品名
  - Col4: 単位, Col5: 薬価基準コード, Col6: 薬価, Col7: 後発品区分
  - Col8-54: 都道府県別数量（47列）+ 全国計 etc.
  - Row0: メタ, Row2: ヘッダ, Row3: 空行, Row4以降: データ

対象薬効分類コード:
  214: 血圧降下剤（Ca拮抗薬・ARB・ACE阻害薬含む）
  217: 血管拡張剤（アムロジピン等）
  218: 高脂血症用剤（スタチン等）
  219: その他の循環器官用薬
  333: 血液凝固阻止剤（抗凝固薬）

入力: ../../02_Data/raw/NDB_OpenData/No.10/05_処方薬/01_公費レセプトを含まないデータ/
出力: data/interim/cvd_prescription.csv

NOTE: NDB生データはAIに送信しない。スクリプトのみ保管。
"""

import pandas as pd
import numpy as np
from pathlib import Path
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE  = PROJECT_ROOT / 'config/config.yaml'

with open(CONFIG_FILE, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

NDB_ROOT = (PROJECT_ROOT / '../../02_Data/raw/NDB_OpenData/No.10/05_処方薬/01_公費レセプトを含まないデータ').resolve()
OUTPUT_FILE = PROJECT_ROOT / 'data/interim/cvd_prescription.csv'

# 循環器関連の薬効分類コード
CVD_DRUG_CODES = {
    '214': '血圧降下剤',
    '217': '血管拡張剤',
    '218': '高脂血症用剤',
    '219': 'その他循環器官用薬',
    '333': '血液凝固阻止剤',
}

# 都道府県名リスト（NDB Excelの列順序）
PREF_NAMES = [
    '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
    '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
    '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県',
    '岐阜県', '静岡県', '愛知県', '三重県', '滋賀県', '京都府',
    '大阪府', '兵庫県', '奈良県', '和歌山県', '鳥取県', '島根県',
    '岡山県', '広島県', '山口県', '徳島県', '香川県', '愛媛県', '高知県',
    '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'
]


def find_target_excel() -> Path | None:
    """外来（院外）の内服薬都道府県別Excelを探す"""
    for d in NDB_ROOT.iterdir():
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if '都道府県' in f.name and '院外' in f.name and f.suffix == '.xlsx':
                return f
    return None


def extract_cvd_by_prefecture(filepath: Path) -> pd.DataFrame:
    """
    NDB処方薬Excelから循環器関連薬効分類の都道府県別処方数量を集計。
    """
    print(f"[INFO] 読み込み: {filepath.name}")
    df = pd.read_excel(filepath, header=None, engine='openpyxl')
    print(f"  Shape: {df.shape}")

    # ヘッダ構造確認: Row2がカラムヘッダ
    # Row0: メタ, Row1: 空, Row2: ヘッダ, Row3: 都道府県名行
    # Row4以降: データ

    # 都道府県名の列位置を自動検出（Row3の行から）
    pref_row = df.iloc[3]
    pref_cols = {}
    for col_idx in range(8, df.shape[1]):
        cell_val = str(pref_row.iloc[col_idx]).strip()
        if cell_val in PREF_NAMES:
            pref_cols[cell_val] = col_idx

    if len(pref_cols) < 40:
        # Row3で見つからなければRow2も試す
        for row_idx in [2, 3, 4]:
            pref_row = df.iloc[row_idx]
            pref_cols = {}
            for col_idx in range(8, df.shape[1]):
                cell_val = str(pref_row.iloc[col_idx]).strip()
                if cell_val in PREF_NAMES:
                    pref_cols[cell_val] = col_idx
            if len(pref_cols) >= 40:
                break

    print(f"  都道府県列: {len(pref_cols)}件検出")
    if len(pref_cols) < 40:
        print(f"  [WARN] 都道府県列が不足（{len(pref_cols)}件）。ヘッダ構造を手動確認してください。")
        # デバッグ: 各行のcol8-10を表示
        for r in range(min(5, len(df))):
            vals = [str(df.iloc[r, c])[:15] for c in range(8, min(12, df.shape[1]))]
            print(f"    R{r} col8-11: {vals}")
        return pd.DataFrame()

    # データ行: Row4以降
    data = df.iloc[4:].copy()
    data.columns = range(df.shape[1])

    # 薬効分類コード列 = Col0
    # NaN の行は前の薬効分類の続き → ffill
    data[0] = data[0].astype(str).replace('nan', np.nan)
    data[0] = data[0].ffill()

    # 循環器関連のみフィルタ
    cvd_mask = data[0].isin(CVD_DRUG_CODES.keys())
    cvd_data = data[cvd_mask].copy()
    print(f"  循環器関連行数: {len(cvd_data)}")

    if cvd_data.empty:
        print("  [WARN] 循環器関連データが見つかりません")
        return pd.DataFrame()

    # 都道府県別に薬効分類コード単位で合計
    records = []
    for drug_code, drug_name in CVD_DRUG_CODES.items():
        code_data = cvd_data[cvd_data[0] == drug_code]
        if code_data.empty:
            continue

        for pref_name, col_idx in pref_cols.items():
            # 数値変換（全角数字・マスク値対応）
            values = pd.to_numeric(code_data.iloc[:, col_idx], errors='coerce')
            total = values.sum()
            count = values.notna().sum()

            records.append({
                'prefecture':    pref_name,
                'drug_code':     drug_code,
                'drug_name':     drug_name,
                'total_quantity': total,
                'drug_count':    count,  # マッチした医薬品数
            })

    result = pd.DataFrame(records)
    print(f"  集計レコード数: {len(result)}")
    return result


def main():
    if not NDB_ROOT.exists():
        print(f"[ERROR] NDBデータが見つかりません: {NDB_ROOT}")
        return

    excel_file = find_target_excel()
    if excel_file is None:
        print("[ERROR] 外来院外の都道府県別薬効分類Excelが見つかりません")
        return

    result = extract_cvd_by_prefecture(excel_file)
    if result.empty:
        print("[ERROR] データ抽出結果が空です")
        return

    # 都道府県×薬効分類 → 都道府県単位のサマリに変換（ピボット）
    pivot = result.pivot_table(
        index='prefecture',
        columns='drug_name',
        values='total_quantity',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # 全循環器薬の合計列を追加
    quantity_cols = [c for c in pivot.columns if c != 'prefecture']
    pivot['cvd_total_quantity'] = pivot[quantity_cols].sum(axis=1)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pivot.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"\n[OK] 出力: {OUTPUT_FILE}  shape={pivot.shape}")
    print(pivot[['prefecture', 'cvd_total_quantity']].head(10).to_string(index=False))

    # 詳細データも保存
    detail_file = OUTPUT_FILE.parent / 'cvd_prescription_detail.csv'
    result.to_csv(detail_file, index=False, encoding='utf-8')
    print(f"[OK] 詳細: {detail_file}")


if __name__ == '__main__':
    main()
