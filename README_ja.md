# ndb-cold-exposure-cardiovascular-japan

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

**[English version: README.md](README.md)**

## 概要

本リポジトリは以下の論文の解析コードおよび補足資料を収録しています。

> **齋藤春樹, 大平哲也.** 「寒冷月比率と循環器疾患処方率の関連：日本の全国エコロジカルスタディ」  
> *Osong Public Health and Research Perspectives* (投稿中, 2026年6月)

### 主要結果

- **寒冷月比率**（月平均気温 <10°C の月の割合）は、5つの気温指標の中で循環器薬処方率の最強の予測因子でした（単変量 R² = 0.390、*p* < 0.001）。
- 多変量OLS回帰（調整済み R² = 0.626）において、**寒冷月比率**・**高齢化率**・**失業率**が独立して有意な関連を示しました。
- 人口標準化後の処方率は空間的自己相関を示しませんでした（Global Moran's I = 0.091、*p* = 0.114）。
- 寒冷期が長い都道府県ほど、循環器疾患の薬剤負担が不均衡に大きいことが示されました。

---

## データソース

| データ | ソース | 内容 |
|--------|--------|------|
| NDB オープンデータ（第10回、2025年5月公開） | 厚生労働省 | 都道府県別循環器薬処方数（FY2023） |
| 月別気象データ（基準期間） | 気象庁（JMA） | 都道府県別月平均気温（2016–2020年） |
| 人口 | 2020年国勢調査（統計局） | 処方率標準化用人口 |
| 社会経済指標 | 内閣府・総務省・厚生労働省 | 所得・失業率・高齢化率・医師数 |

> **注意**: NDB生データは再配布できません。[厚生労働省ウェブサイト](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00001.html) から直接ダウンロードしてください。

---

## リポジトリ構成

```
ndb-cold-exposure-cardiovascular-japan/
├── README.md                    # 英語版 README
├── README_ja.md                 # このファイル（日本語版）
├── config/
│   └── config.yaml              # 解析設定（薬剤コード・閾値等）
├── 03_Analysis/
│   └── scripts/
│       ├── 00_preprocess_jma_data.py    # JMA CSV前処理
│       ├── 01_fetch_weather_data.py     # 気象変数集計
│       ├── 02_extract_cvd_data.py       # NDB循環器データ抽出
│       ├── 03_integrate_data.py         # データ統合
│       ├── 03b_collect_ses_data.py      # 社会経済指標収集
│       ├── 04_descriptive_analysis.py   # 記述統計・相関分析
│       ├── 05_regression_analysis.py    # OLS回帰・モデル選択
│       ├── 06_spatial_analysis.py       # 空間自己相関・LISA解析
│       ├── 07_percapita_reanalysis.py   # 人口当たり再解析
│       └── 08_percapita_choropleth.py   # コロプレスマップ作成
├── 04_Manuscripts/
│   ├── Manuscript_temperature_CVD.qmd   # Quarto 原稿ソース
│   ├── references.bib                   # 参考文献
│   └── submission_package_phrp/         # PHRP投稿一式
├── data/
│   ├── raw/weather/                     # JMA CSV（再配布不可）
│   └── interim/                         # 処理済み中間データ
├── results/
│   └── figures/                         # 生成された図
└── docs/
    └── DATA_SOURCES.md                  # データソース詳細
```

---

## 解析フロー

```
JMA CSV（生）  ──→ 00_preprocess ──→ 01_aggregate ──┐
NDB Excel（生）──→ 02_extract ─────────────────────────┤
SES データ   ──→ 03b_collect ─────────────────────────────┤
                                                         ↓
                                              03_integrate → analysis_dataset.csv
                                                         ↓
                                04_descriptive → 05_regression → 06_spatial
                                                         ↓
                                07_percapita_reanalysis → 08_choropleth
                                                         ↓
                                           Manuscript_temperature_CVD.qmd
```

---

## 環境構築

```bash
# リポジトリをクローン
git clone https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan.git
cd ndb-cold-exposure-cardiovascular-japan

# 仮想環境を作成
python -m venv .venv
.venv\Scripts\activate  # Windows

# 依存パッケージをインストール
pip install -r requirements.txt
```

---

## 解析の再現手順

```bash
# Step 1: JMA 気象データ前処理（data/raw/weather/ に JMA CSV を配置後）
python 03_Analysis/scripts/00_preprocess_jma_data.py
python 03_Analysis/scripts/01_fetch_weather_data.py

# Step 2: NDB CVD データ抽出（data/raw/ に NDB Excel を配置後）
python 03_Analysis/scripts/02_extract_cvd_data.py

# Step 3: データ統合
python 03_Analysis/scripts/03_integrate_data.py
python 03_Analysis/scripts/03b_collect_ses_data.py

# Step 4: 解析
python 03_Analysis/scripts/04_descriptive_analysis.py
python 03_Analysis/scripts/05_regression_analysis.py
python 03_Analysis/scripts/06_spatial_analysis.py

# Step 5: 人口当たり解析（主解析）
python 03_Analysis/scripts/07_percapita_reanalysis.py
python 03_Analysis/scripts/08_percapita_choropleth.py
```

---

## 引用

本コードを使用する場合は以下を引用してください：

```bibtex
@article{saito2026cold,
  title   = {Association between Cold Month Exposure and Cardiovascular Disease 
             Prescription Rate: A Nationwide Ecological Study in Japan},
  author  = {Saito, Haruki and Ohira, Tetsuya},
  journal = {Osong Public Health and Research Perspectives},
  year    = {2026},
  note    = {Submitted}
}
```

---

## 倫理について

本研究は公開集計データ（NDB オープンデータ）のみを使用しており、個人の患者データや人を対象とした研究は含まれません。日本の「人を対象とする生命科学・医学系研究に関する倫理指針」のもと、倫理審査委員会の承認は不要です。

---

## ライセンス

本リポジトリは [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/) のもと公開されています。

---

## 著者

- **齋藤春樹**（責任著者） — 福島県立医科大学医学部疫学講座 — ORCID: [0009-0009-7890-6068](https://orcid.org/0009-0009-7890-6068)
- **大平哲也** — 福島県立医科大学医学部疫学講座 — ORCID: [0000-0003-4532-7165](https://orcid.org/0000-0003-4532-7165)
