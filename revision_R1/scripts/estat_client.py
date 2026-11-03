# -*- coding: utf-8 -*-
"""
e-Stat API の最小クライアント。
- アプリケーションIDは、パッケージ直下（revision_R1）の .env（git管理対象外）の E_STAT_APP_ID、または環境変数から読む。
- IDも、IDを含むURLも、決して print / ログ出力しない（例外メッセージにもURLを含めない）。
- 取得するのは公開統計のみ（研究データは送信しない）。
"""
import os, json, time, urllib.request, urllib.parse, urllib.error
from pathlib import Path

import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent)); import paths as _P
PROJ = _P.PROJ; R1 = _P.R1
BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/"


class EStatError(RuntimeError): pass


def _load_key():
    k = os.environ.get("E_STAT_APP_ID", "").strip()
    env = R1 / ".env"
    if not k and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("E_STAT_APP_ID="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k:
        raise EStatError("E_STAT_APP_ID が見つかりません（環境変数、または revision_R1 直下の .env に設定してください）")
    return k


def call(endpoint, **params):
    q = {"appId": _load_key(), "lang": "J", **params}
    url = BASE + endpoint + "?" + urllib.parse.urlencode(q)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                j = json.load(r)
            break
        except urllib.error.HTTPError as e:
            raise EStatError(f"HTTP {e.code}（{endpoint}）") from None      # URL（=キー）を例外に残さない
        except urllib.error.URLError:
            if attempt == 2: raise EStatError(f"接続エラー（{endpoint}）") from None
            time.sleep(2)
    root = next(iter(j.values()))
    res = root.get("RESULT", {})
    if res.get("STATUS", 0) not in (0, 1):                                 # 0=正常, 1=該当データなし
        raise EStatError(f"e-Stat status={res.get('STATUS')}: {res.get('ERROR_MSG')}")
    return root


def check():
    """キーの有効性だけを確認（IDは表示しない）。"""
    root = call("getStatsList", searchWord="人口推計", limit=1)
    return root.get("RESULT", {}).get("STATUS"), root.get("RESULT", {}).get("ERROR_MSG")
