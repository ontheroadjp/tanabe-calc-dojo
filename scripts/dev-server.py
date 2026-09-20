#!/usr/bin/env python3
"""ローカル開発用サーバー。

本番は nginx が次のように振り分けている:

    /calc-dojo/admin...        -> API (/admin...)
    /calc-dojo/api/feedback    -> API (/api/feedback)
    /calc-dojo/...             -> 静的ファイル

静的ファイルだけを配信すると管理画面が動かず、API だけを起動すると
CSS が当たらない。両方を1プロセスでまとめ、同じパス構成で動かす。

    api/.venv/bin/python scripts/dev-server.py
    http://127.0.0.1:8000/calc-dojo/
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

import uvicorn  # noqa: E402
from starlette.staticfiles import StaticFiles  # noqa: E402

from app import app as api_app  # noqa: E402

PREFIX = "/calc-dojo"
static_app = StaticFiles(directory=ROOT, html=True)


async def dispatch(scope, receive, send):
    """nginx と同じ規則でAPIと静的配信に振り分ける。"""
    if scope["type"] not in ("http", "websocket"):
        return await api_app(scope, receive, send)

    path = scope.get("path", "")

    if path == PREFIX:
        await send({"type": "http.response.start", "status": 307,
                    "headers": [(b"location", f"{PREFIX}/".encode())]})
        await send({"type": "http.response.body", "body": b""})
        return

    if not path.startswith(PREFIX + "/"):
        await send({"type": "http.response.start", "status": 404,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body",
                    "body": f"{PREFIX}/ を開いてください".encode()})
        return

    # nginx の proxy_pass と同じく、/calc-dojo を取り除いてアプリへ渡す
    inner = path[len(PREFIX):]
    scope = dict(scope, path=inner, raw_path=inner.encode())

    if inner.startswith("/admin") or inner.startswith("/api/"):
        return await api_app(scope, receive, send)
    return await static_app(scope, receive, send)


def main() -> None:
    if not (ROOT / "assets" / "mathjax" / "tex-svg.js").is_file():
        print("警告: assets/mathjax/ がありません。数式が表示されません。", flush=True)
        print("      先に ./scripts/fetch-mathjax.sh を実行してください。\n", flush=True)
    # uvicorn のログより先に出したいので、明示的に流す
    print(f"起動しました: http://127.0.0.1:8000{PREFIX}/", flush=True)
    print(f"管理画面:     http://127.0.0.1:8000{PREFIX}/admin/login", flush=True)
    print("停止するには Ctrl+C\n", flush=True)
    uvicorn.run(dispatch, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
