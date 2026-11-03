# -*- coding: utf-8 -*-
"""
paths: パッケージ内のパスを1か所に集約する（絶対パスをコードに書かない）。
既定では、このファイルの2つ上の階層（revision_R1）を基準にする。環境変数 R1_ROOT で変更できる。

  R1       : パッケージのルート（revision_R1）
  INPUTS   : data/inputs（入力データ。下記）
  PROJ     : 元プロジェクトの複製（data/interim の元データ、03_Analysis/scripts、config）。環境変数 NDB_PROJ で変更可
  NDB_DIR  : NDBオープンデータ第10回（公費レセプトを含まない）の Excel 2点（外来・院外の内服。都道府県別、性年齢別）
  OFFICIAL : 公式統計の原表（人口・高齢化・医師・失業・所得）と Codex 編纂のデータセット
  SUB_V4   : 初回投稿版（Manuscript_PHRP_v4.docx など）と査読コメントのPDF
"""
import os
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
R1 = Path(os.environ.get("R1_ROOT", SCRIPTS.parent)).resolve()
INPUTS = R1 / "data" / "inputs"
PROJ = Path(os.environ.get("NDB_PROJ", INPUTS / "original_project")).resolve()
NDB_DIR = INPUTS / "NDB"
OFFICIAL = INPUTS / "official"
SUB_V4 = INPUTS / "submission_v4"
DATA = R1 / "data"
RESULTS = R1 / "results"
