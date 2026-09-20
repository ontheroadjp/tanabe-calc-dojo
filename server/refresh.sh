#!/bin/sh
# デプロイ後の更新処理。nginx 設定を生成し、依存を入れ直して API を再起動する。
#
# CD からは ssh 経由で呼ばれる。authorized_keys の forced command
# (deploy-shell.sh) が許可する唯一の「コマンド」でもある。
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
API="$ROOT/api"
CONF="$ROOT/server/calc-dojo.conf"

# --- nginx 設定 -------------------------------------------------------
# alias と proxy_pass は絶対パスを要求するが、このリポジトリは public なので
# サーバーのパスを含む実ファイルは置けない。デプロイのたびにテンプレートから
# 生成し、/etc からはこのファイルを symlink して使う。
#
# 反映には nginx の reload が必要で、それには root 権限が要る。ここでは
# 行わないので、変更があった場合はその旨を出力して知らせる。
if [ -f "$CONF.example" ]; then
  sed "s|__ROOT__|$ROOT|g" "$CONF.example" > "$CONF.tmp"
  if cmp -s "$CONF.tmp" "$CONF" 2>/dev/null; then
    rm -f "$CONF.tmp"
  else
    mv "$CONF.tmp" "$CONF"
    echo "nginx 設定を更新しました。反映するには:"
    echo "  sudo nginx -t && sudo systemctl reload nginx"
  fi
fi

# --- API --------------------------------------------------------------
cd "$API"

# 初回のみ venv を作る
if [ ! -x .venv/bin/python ]; then
  /usr/bin/python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
fi

.venv/bin/pip install --quiet -r requirements.txt

# 起動していなければ start、していれば restart
PM2_HOME="$API/.pm2" /usr/bin/pm2 startOrRestart "$ROOT/server/ecosystem.config.js"
