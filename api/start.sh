#!/bin/sh
# フィードバックAPIの起動スクリプト。
#
# サーバー全体で共有するリソース（TCPポート番号など）を使わず、
# calc-dojo/api/ の中だけで完結させる:
#   - listen は unix socket (run/api.sock)
#   - DB は data/feedback.sqlite3
#   - Python は .venv
set -e

BASE=$(cd "$(dirname "$0")" && pwd)
SOCK="$BASE/run/api.sock"

mkdir -p "$BASE/run" "$BASE/data"
rm -f "$SOCK"

# uvicorn が作るソケットは umask 由来の 0755 になり、
# nginx (www-data) が connect できない。生成直後に 0666 へ変更する。
(
  i=0
  while [ ! -S "$SOCK" ] && [ "$i" -lt 100 ]; do
    sleep 0.1
    i=$((i + 1))
  done
  [ -S "$SOCK" ] && chmod 0666 "$SOCK"
) &

export FEEDBACK_DB="${FEEDBACK_DB:-$BASE/data/feedback.sqlite3}"

exec "$BASE/.venv/bin/uvicorn" app:app --app-dir "$BASE" --uds "$SOCK"
