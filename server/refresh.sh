#!/bin/sh
# デプロイ後の更新処理。依存を入れ直して API を再起動する。
#
# CD からは ssh 経由で呼ばれる。authorized_keys の forced command
# (deploy-shell.sh) が許可する唯一の「コマンド」でもある。
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
API="$ROOT/api"

cd "$API"

# 初回のみ venv を作る
if [ ! -x .venv/bin/python ]; then
  /usr/bin/python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
fi

.venv/bin/pip install --quiet -r requirements.txt

# 起動していなければ start、していれば restart
PM2_HOME="$API/.pm2" /usr/bin/pm2 startOrRestart "$ROOT/server/ecosystem.config.js"
