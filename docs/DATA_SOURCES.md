# データソース一覧 — NDB_XXX_temperature_CVD

## 自動取得・共有データ（追加ダウンロード不要）

| データ | パス | 備考 |
|--------|------|------|
| NDB Open Data 第10回 | `../../02_Data/raw/NDB_OpenData/No.10/` | 読み取り専用・変更禁止 |
| 国勢調査2020 人口 | `../../02_Data/raw/Statistics_Bureau/Census_2020/` | tblT001141・tblT001194 |
| 市区町村民税SESデータ | `../../02_Data/raw/ses_data/` | 課税所得・失業率 |
| 都道府県GeoJSON | `../../02_Data/raw/GIS/japan.geojson` | 空間解析用 |

## 手動ダウンロード必要なデータ

### 気象庁（JMA）月別気象データ
- **URL**: https://www.data.jma.go.jp/risk/obsdl/index.php
- **対象期間**: 2016年1月〜2020年12月（60ヶ月）
- **対象要素**: 月別平均気温、降水量、日照時間、雲量、湿度
- **対象地点**: 47都道府県代表地点（札幌〜那覇）
- **形式**: CSV（Shift-JIS、横長）
- **保存先**: `data/raw/weather/jma_monthly_YYYY_YYYY.csv`

> ⚠️ rainfall_depressionプロジェクト（`jma_monthly_2016_2018.csv`, `jma_monthly_2019_2020.csv`）の
> 気象CSVをそのままコピーして再利用可能。

### ダウンロード手順（JMA）
1. 上記URLにアクセス
2. 「地点を選ぶ」→「都道府県を選ぶ」で全47地点を選択
3. 「項目を選ぶ」→ 気温（平均）・降水量・日照時間・雲量・湿度
4. 「期間を選ぶ」→ 2016年1月〜2020年12月
5. CSVダウンロード → `data/raw/weather/` に保存

## 中間データ（スクリプト実行で自動生成）

| ファイル | 生成スクリプト | 内容 |
|---------|--------------|------|
| `data/interim/weather_monthly_long.csv` | `00_preprocess_jma_data.py` | 縦長気象データ |
| `data/interim/weather_data_prefecture.csv` | `01_fetch_weather_data.py` | 都道府県別気温変動指標 |
| `data/interim/cvd_prescription.csv` | `02_extract_cvd_data.py` | 循環器薬処方数 |
| `data/interim/analysis_dataset.csv` | `03_integrate_data.py` | 統合解析データセット |
