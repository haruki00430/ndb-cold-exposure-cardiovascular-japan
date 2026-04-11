# HANDOVER.md — NDB_XXX_temperature_CVD

**最終更新**: 2026-03-04  
**ステータス**: SES共変量統合完了・解析スクリプト（04〜06）作成待ち

---

## 1. プロジェクト概要

気温変動（年間気温較差・冬季平均気温・気温標準偏差）と循環器疾患受診（脳卒中・虚血性心疾患を代理する処方薬）の都道府県別地域格差を空間疫学手法で検証する。

| 項目 | 内容 |
|------|------|
| アウトカム | 循環器関連薬剤処方数（NDB第10回・外来院外） |
| 主説明変数 | 気温較差・冬季気温・Temp_std・Cold_months_ratio |
| 空間単位 | 都道府県（n=47） |
| 気象データ期間 | 2016年1月〜2020年12月（60ヶ月） |

---

## 2. 完了済み作業

### フェーズ0：プロジェクト立ち上げ (2026-03-03)
- `README.md`, `config/config.yaml`, `docs/DATA_SOURCES.md` を新規作成
- `04_Manuscripts/Manuscript_temperature_CVD.qmd` テンプレート作成
- `rainfall_depression` プロジェクトをテンプレートとして全体構成を設計

### フェーズ1：気象データ前処理
- JMA月別気象CSV（`jma_monthly_2016_2018.csv`, `jma_monthly_2019_2020.csv`）を
  `data/raw/weather/` にコピー（rainfall_depressionから転用）
- `00_preprocess_jma_data.py` でShift-JIS CSVを縦長UTF-8に変換
  - **バグ修正済み**: `skiprows=5` → `skiprows=6`（データは7行目から）
  - **バグ修正済み**: `[-2:]` → `split('/')` による月パース（1〜9月が欠落していた）
  - 出力: `data/interim/weather_monthly_long.csv` (2820行 = 47×60ヶ月) ✅

### フェーズ2：気温変動指標集計
- `01_fetch_weather_data.py` で都道府県別の気温変動指標を算出
  - `Temp_range_annual`, `Winter_temp_avg`, `Temp_std`, `Cold_months_ratio` 等
  - 出力: `data/interim/weather_data_prefecture.csv` (47×8) ✅

### フェーズ3：NDB循環器薬抽出
- `02_extract_cvd_data.py` で `【内服】外来（院外）_都道府県別薬効分類別数量.xlsx` から抽出
  - 対象薬効: 抗血小板薬・抗凝固薬・Ca拮抗薬・ARB/ACE・スタチン・硝酸薬・β遮断薬
  - 出力: `data/interim/cvd_prescription.csv` (47×10) ✅

### フェーズ4：データ統合
- `03_integrate_data.py` で気象・CVD・SESを結合
  - 出力: `data/interim/analysis_dataset.csv` (47×18) ✅

### フェーズ5：SES共変量統合 (2026-03-04)
- `03b_collect_ses_data.py` でSES共変量を取得・統合
  - `physicians_per_100k`  : e-Stat APIから取得（医療施設調査令和2年、ID: 0004002104）
  - `unemployment_rate`    : 国勢調査2020（総務省、令和2年就業状態等基本集計）
  - `elderly_ratio`        : 国勢調査2020（総務省、令和2年人口等基本集計）
  - `income_per_capita`    : 内閣府「令和2年度県民経済計算」
  - 出力: `data/interim/ses_data.csv` (47×5) ✅
  - 出力: `data/interim/analysis_dataset.csv` 更新 (47×21, 欠損なし) ✅

---

## 3. 中間ファイル一覧

| ファイル | 行数 | 内容 |
|---------|------|------|
| `data/interim/weather_monthly_long.csv` | 2820 | 月別気象（縦長） |
| `data/interim/weather_data_prefecture.csv` | 47 | 都道府県別気温指標 |
| `data/interim/cvd_prescription.csv` | 47 | 都道府県別循環器薬処方数 |
| `data/interim/analysis_dataset.csv` | 47 | 統合解析データセット |

---

## 4. 未完了タスク（次セッションで実施）

- [ ] `04_descriptive_analysis.py` — 記述統計・相関行列・散布図
- [ ] `05_regression_analysis.py` — 単変量・多変量重回帰
- [ ] `06_spatial_analysis.py` — Moran's I・空間回帰（SLM/SEM）
- [ ] `07_sensitivity_analysis.py` — 感度分析・Cook's D
- [ ] SESデータ（課税所得・失業率）の正式統合（現在は気象+CVDのみ）
- [ ] 論文草稿（`Manuscript_temperature_CVD.qmd`）執筆

---

## 5. 既知の注意点

### NDB Excelパス
```
02_Data/raw/NDB_OpenData/No.10/05_処方薬/
01_公費レセプトを含まないデータ/
01_処方薬（内服／外用／注射）/
【内服】外来（院外）_都道府県別薬効分類別数量.xlsx
```
- ヘッダー行: 4行目（0-indexed: 3）、都道府県名: 47列

### JMA CSVのパース仕様
- エンコーディング: Shift-JIS
- データ開始: **7行目（`skiprows=6`）**
- 年月列: `"2016/1"` 形式 → `split('/')` で分割（`[-2:]` は使わない）

### SESデータ統合
- `data/interim/cvd_prescription.csv` のprefecture列は小文字
- `weather_data_prefecture.csv` のprefecture列も小文字
- SES（課税所得）は `第11表*合計*.xlsx` から取得予定だが列構造の確認が必要

---

## 6. 実行コマンド（フルパイプライン）

```bash
# 作業ディレクトリ
cd projects/NDB_XXX_temperature_CVD

# Phase 0-3: 実行済み（再実行可）
python 03_Analysis/scripts/00_preprocess_jma_data.py
python 03_Analysis/scripts/01_fetch_weather_data.py
python 03_Analysis/scripts/02_extract_cvd_data.py
python 03_Analysis/scripts/03_integrate_data.py

# Phase 4以降: 未作成
python 03_Analysis/scripts/04_descriptive_analysis.py
python 03_Analysis/scripts/05_regression_analysis.py
python 03_Analysis/scripts/06_spatial_analysis.py
```
