# NDB_XXX_temperature_CVD
## 気温変動と循環器疾患の地域格差：NDBオープンデータによる都道府県別空間疫学解析

**ステータス**: 進行中 (In Progress)
**開始日**: 2026-03-03

## ステータス（2026-04-05 リポジトリ照合）

- **原稿**: `04_Manuscripts/Manuscript_temperature_CVD.qmd`
- **備考**: 上記「進行中」表記と `analysis/`・結果ファイルの実体がずれる場合は実体を正とする。

---

## 概要

気温の季節変動・日較差が脳卒中（I60-I69）・心筋梗塞（I20-I25）の受診率に与える影響を、
都道府県レベルの空間疫学手法で定量化する。

NDB Open Dataの処方・医療処置データと気象庁（JMA）の月別気象データを結合し、
社会経済指標を調整した上で、気温変動と循環器疾患受診格差の関係を検証する。

## 研究仮説

- **主仮説**: 気温較差（年間・冬季）が大きい都道府県ほど、循環器疾患の標準化受診比（SCR）が高い
- **副仮説**: この関連は高齢化率・所得水準・医療アクセスで一部説明される

## データソース

| データ | ソース | 内容 |
|--------|--------|------|
| NDB Open Data 第10回 | 厚生労働省 | 循環器薬（降圧薬・抗血栓薬）処方数 |
| 気象月別データ | 気象庁（JMA） | 月別気温・降水量・日照時間（47地点） |
| 国勢調査2020 | 統計局 | 性・年齢別人口（標準化用） |
| 社会生活統計指標 | 総務省 | 所得・失業率・教育水準 |
| GIS | MLIT / 共有 | 都道府県境界 (`japan.geojson`) |

## 気象変数（主要）

- `Temp_range_annual`: 年間気温較差（最高－最低、℃）
- `Winter_temp_avg`: 冬季平均気温（12〜2月、℃）
- `Temp_std`: 月別平均気温の標準偏差（変動指標）
- `Cold_months_ratio`: 月平均気温＜5℃ の月数比率

## 転用元パイプライン

`NDB_XXX_rainfall_depression` の気象データ取得・前処理スクリプトを再利用。

## ディレクトリ構成

```
NDB_XXX_temperature_CVD/
├── README.md
├── config/
│   └── config.yaml          # 解析設定（薬剤コード・期間・閾値）
├── 03_Analysis/
│   └── scripts/
│       ├── 00_preprocess_jma_data.py    # JMA CSV前処理（横長→縦長）
│       ├── 01_fetch_weather_data.py     # 気象変数集計（都道府県別）
│       ├── 02_extract_cvd_data.py       # NDB循環器データ抽出
│       ├── 03_integrate_data.py         # データ統合
│       ├── 04_descriptive_analysis.py   # 記述統計・相関分析
│       ├── 05_regression_analysis.py    # 重回帰分析
│       ├── 06_spatial_analysis.py       # 空間自己相関・空間回帰
│       └── 07_sensitivity_analysis.py   # 感度分析
├── 04_Manuscripts/
│   └── Manuscript_temperature_CVD.qmd
├── data/
│   ├── raw/
│   │   └── weather/                     # JMA CSVを配置
│   └── interim/                         # 処理済み中間データ
├── results/
│   └── figures/
├── docs/
│   └── DATA_SOURCES.md
└── logs/
```

## 解析フロー

```
JMA CSV (Shift-JIS) → 00_preprocess → 01_aggregate
NDB Excel          → 02_extract
国勢調査/SES       → (共有データ再利用)
                       ↓
                    03_integrate → analysis_dataset.csv
                       ↓
          04_descriptive → 05_regression → 06_spatial → 07_sensitivity
                       ↓
               Manuscript_temperature_CVD.qmd
```

## 実行方法

```bash
# 仮想環境を有効化
.venv\Scripts\activate

# Phase 0-1: 気象データ準備（JMA CSVをdata/raw/weather/に配置後）
python 03_Analysis/scripts/00_preprocess_jma_data.py
python 03_Analysis/scripts/01_fetch_weather_data.py

# Phase 2: NDBデータ抽出
python 03_Analysis/scripts/02_extract_cvd_data.py

# Phase 3以降
python 03_Analysis/scripts/03_integrate_data.py
python 03_Analysis/scripts/04_descriptive_analysis.py
python 03_Analysis/scripts/05_regression_analysis.py
```
