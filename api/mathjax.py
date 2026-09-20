"""MathJax のバージョン確認。

配信中のバージョンは scripts/fetch-mathjax.sh が書き出す VERSION ファイルから読む。
最新版は npm レジストリに問い合わせる。結果は1日キャッシュする。

更新はこの画面からは行わない。リポジトリの固定値を変えて push する運用にし、
「いつ誰がどのバージョンに上げたか」を git の履歴に残す。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import BASE_DIR, get_state, set_state

REGISTRY_URL = "https://registry.npmjs.org/mathjax-full/latest"
STATE_KEY = "mathjax_latest"
CHECK_INTERVAL = timedelta(days=1)

# リポジトリ内で固定値を書いている場所（管理画面に手順として表示する）
PIN_FILE = "scripts/fetch-mathjax.sh"
PIN_LINE = "VERSION="


def _version_file() -> Path | None:
    """配信中の VERSION ファイルを探す。

    サーバーでは <root>/web/assets/、ローカルでは <root>/assets/ に置かれる。
    """
    if env := os.environ.get("MATHJAX_VERSION_FILE"):
        p = Path(env)
        return p if p.is_file() else None
    root = BASE_DIR.parent
    for candidate in (root / "web" / "assets" / "mathjax" / "VERSION",
                      root / "assets" / "mathjax" / "VERSION"):
        if candidate.is_file():
            return candidate
    return None


def installed_version() -> str | None:
    f = _version_file()
    if not f:
        return None
    v = f.read_text().strip()
    return v or None


def _fetch_latest() -> str | None:
    try:
        req = urllib.request.Request(REGISTRY_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.load(res).get("version")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def latest_version(force: bool = False) -> tuple[str | None, str | None]:
    """(最新版, 確認日時) を返す。確認に失敗したら前回の値をそのまま返す。"""
    cached = get_state(STATE_KEY)
    if cached and not force:
        _, checked_at = cached
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(checked_at)
            if age < CHECK_INTERVAL:
                return cached
        except ValueError:
            pass

    latest = _fetch_latest()
    if latest is None:
        return cached if cached else (None, None)

    set_state(STATE_KEY, latest)
    return get_state(STATE_KEY)


def status(force: bool = False) -> dict:
    current = installed_version()
    latest, checked_at = latest_version(force=force)
    return {
        "current": current,
        "latest": latest,
        "checked_at": checked_at,
        "update_available": bool(current and latest and current != latest),
        "pin_file": PIN_FILE,
        "pin_line": PIN_LINE,
    }
