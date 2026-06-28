# GitHub / Zenodo 公開手順書

**プロジェクト**: NDB_XXX_temperature_CVD  
**投稿先**: Osong Public Health and Research Perspectives (PHRP)  
**作成日**: 2026-06-28

---

## 1. GitHub リポジトリのリネーム

### 現在の名前
`haruki00430/NDB_XXX_temperature_CVD`（Private）

### 新しい名前（推奨）
`haruki00430/ndb-cold-exposure-cardiovascular-japan`

**命名根拠**: 他の公開済みプロジェクトの命名規則に合わせる
- `haruki00430/ndb-unemployment-diabetes-japan`
- `haruki00430/greenspace-mental-health-japan`

### リネーム手順

1. GitHub.com にアクセス → リポジトリページ
2. **Settings** タブ → Repository name を変更
3. `ndb-cold-exposure-cardiovascular-japan` と入力 → **Rename** をクリック
4. ローカルのリモートURLを更新：
   ```bash
   cd C:/Users/user/.ag-cursor-common/research_workspace/projects/NDB_Research_Hub/projects/NDB_XXX_temperature_CVD
   git remote set-url origin https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan.git
   git remote -v  # 確認
   ```

---

## 2. Public リポジトリへの変更

### 手順
1. GitHub リポジトリ → **Settings** → **Danger Zone**
2. **Change repository visibility** → **Make public**
3. リポジトリ名を入力して確認

### 変更前の確認事項
- [ ] `02_Data/raw/` が `.gitignore` に記載されている（NDB生データ非公開）
- [ ] 個人情報・APIキーが含まれていない
- [ ] 実データ（都道府県別集計実数）がコードに直書きされていない
- [ ] `.claude/` `.venv/` 等の設定フォルダが `.gitignore` に記載されている

### .gitignore 確認コマンド
```bash
cd C:/Users/user/.ag-cursor-common/research_workspace/projects/NDB_Research_Hub/projects/NDB_XXX_temperature_CVD
cat .gitignore
# data/raw/ が除外されていることを確認
```

---

## 3. README.md の更新（英語版：Public リポジトリ向け）

リポジトリルートの `README.md` を下記の英語版に置き換える。
→ **`README_en.md`** として別ファイルも作成し、日本語版 `README_ja.md` も用意する。

**ファイル構成**:
```
README.md        ← 英語版（GitHubのデフォルト表示）
README_ja.md     ← 日本語版
```

---

## 4. Zenodo 登録手順

### 4.1 GitHub と Zenodo の連携（初回のみ）
1. https://zenodo.org → **Log in** → "Sign in with GitHub"
2. **Linked accounts** → GitHub を連携
3. **Settings → GitHub** → `ndb-cold-exposure-cardiovascular-japan` の toggle を ON

### 4.2 DOI の取得
1. GitHub リポジトリで **新しいリリース** を作成：
   - `git tag v1.0.0`
   - `git push origin v1.0.0`
   - GitHub の "Releases" → "Create a new release" → v1.0.0 を選択 → Publish
2. Zenodo が自動的にアーカイブ → DOI が発行される
3. 発行された DOI を記録する（例: `10.5281/zenodo.XXXXXXX`）

### 4.3 Zenodo メタデータ設定

| 項目 | 入力内容 |
|------|---------|
| Title | Association between Cold Month Exposure and Cardiovascular Disease Prescription Rate: A Nationwide Ecological Study in Japan |
| Authors | Saito, Haruki (ORCID: 0009-0009-7890-6068); Ohira, Tetsuya (ORCID: 0000-0003-4532-7165) |
| Description | Analysis code and data for: "Association between Cold Month Exposure and Cardiovascular Disease Prescription Rate: A Nationwide Ecological Study in Japan." Uses NDB Open Data (10th release, FY2023, released May 2025) and Japan Meteorological Agency climate data (reference period 2016–2020). Submitted to Osong Public Health and Research Perspectives (PHRP). |
| License | Creative Commons Attribution Non Commercial No Derivatives 4.0 (CC BY-NC-ND 4.0) |
| Keywords | cardiovascular disease, cold exposure, ecological study, NDB Open Data, Japan, prescription rate, spatial analysis |
| Related identifiers | (manuscript DOI が決まれば追加) |
| Communities | zenodo |

### 4.4 DOI バッジの README への追加
```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```
→ README.md の冒頭に追加する

---

## 5. 論文内のデータ可用性記述

TitlePage_PHRP.docx の "Availability of Data" を下記に更新（Zenodo DOI 取得後）：

```
NDB Open Data is publicly available from the Ministry of Health, Labour and Welfare of Japan
(https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000177221_00001.html).
Japan Meteorological Agency climate data are available from https://www.jma.go.jp/.
Analysis code and processed datasets are available on GitHub
(https://github.com/haruki00430/ndb-cold-exposure-cardiovascular-japan)
and archived on Zenodo (https://doi.org/10.5281/zenodo.XXXXXXX).
```

---

## 6. 最終確認チェックリスト

### GitHub
- [ ] リポジトリ名を `ndb-cold-exposure-cardiovascular-japan` に変更済み
- [ ] Visibility を Public に変更済み
- [ ] `README.md`（英語版）を更新済み
- [ ] `README_ja.md`（日本語版）を追加済み
- [ ] `data/raw/` が `.gitignore` に記載されていてプッシュされていない
- [ ] リポジトリの Description・Topics を設定
  - Description: "Analysis code for ecological study on cold exposure and CVD prescription rates in Japan (NDB Open Data)"
  - Topics: `epidemiology`, `cardiovascular-disease`, `ndb`, `japan`, `ecological-study`, `cold-exposure`
- [ ] GitHub Pages は不要（オフのまま）

### Zenodo
- [ ] GitHub 連携済み
- [ ] v1.0.0 リリースを作成してアーカイブ
- [ ] DOI が発行されている（10.5281/zenodo.XXXXXXX）
- [ ] メタデータ（著者・ORCID・ライセンス）を設定済み
- [ ] README のバッジを更新済み

### 論文
- [ ] TitlePage_PHRP.docx の Data Availability に Zenodo DOI を追加
- [ ] CoverLetter_PHRP.docx の GitHub URL を最終確認
- [ ] Manuscript_PHRP.docx の Methods/Ethics Statement に変更なし

---

*作成: Claude Sonnet 4.6 支援 / 2026-06-28*
