#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NDB処方薬Excelの構造調査用スクリプト（一時使用）"""
import pandas as pd
from pathlib import Path

NDB_ROOT = Path(r'C:\Users\user\SharedWorkspace\projects\NDB_Research_Hub\02_Data\raw\NDB_OpenData\No.10\05_処方薬\01_公費レセプトを含まないデータ')

# 外来院外の内服Excelを探す
for d in NDB_ROOT.iterdir():
    if not d.is_dir():
        continue
    for f in d.iterdir():
        if '都道府県' in f.name and '院外' in f.name and f.suffix == '.xlsx':
            print(f"=== {f.name} ===")
            df = pd.read_excel(f, header=None, engine='openpyxl')
            print(f"Shape: {df.shape}")
            
            # ヘッダ行（1-4行目）
            print("\n--- Header rows (0-3) ---")
            for r in range(min(4, len(df))):
                row = df.iloc[r, :8].tolist()
                print(f"  R{r}: {[str(v)[:30] if pd.notna(v) else '' for v in row]}")
            
            # 薬効分類コードが入るCol0-3のユニーク値パターン
            print(f"\n--- Col0 unique (first 30): ---")
            col0 = df.iloc[4:, 0].dropna().unique()
            for v in col0[:30]:
                print(f"  '{v}'")
            
            # 循環器関連キーワード検索
            print(f"\n--- CVD keyword search ---")
            keywords = ['血管拡張', '不整脈', '血圧降下', '降圧', 'Ca拮抗', 'カルシウム拮抗',
                       'アンジオテンシン', 'ARB', 'ACE', '利尿', '抗血栓', '抗血小板',
                       '抗凝固', 'ワルファリン', 'スタチン', 'HMG-CoA', '脂質異常', 
                       '高脂血', 'アムロジピン', 'ニフェジピン', 'バルサルタン', 'カンデサルタン']
            for col_idx in range(min(5, df.shape[1])):
                col_str = df.iloc[:, col_idx].astype(str)
                for kw in keywords:
                    matches = df[col_str.str.contains(kw, na=False)]
                    if not matches.empty:
                        for _, row in matches.head(2).iterrows():
                            vals = [str(row.iloc[c])[:25] for c in range(min(8, len(row)))]
                            print(f"  KW='{kw}' Col{col_idx}: {vals}")
                        break
            break
    break
