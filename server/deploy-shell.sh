#!/bin/sh
# authorized_keys の forced command。
#
# デプロイ鍵で ssh 接続すると、クライアントが何を要求しても必ずこれが実行される。
# 本来のコマンドは SSH_ORIGINAL_COMMAND に入るので、それを検査して
# 許可したものだけを通す。シェルは渡さない。
#
# authorized_keys への登録例 (1行):
#
#   command="<root>/server/deploy-shell.sh",restrict ssh-ed25519 AAAA... github-actions-calc-dojo
#
# restrict は port/agent/X11 転送と pty 割り当てをまとめて禁止する
# (OpenSSH 7.2 以降)。
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CMD=${SSH_ORIGINAL_COMMAND:-}

log() {
  logger -t calc-dojo-deploy -- "$1" 2>/dev/null || true
}

case "$CMD" in
  refresh)
    log "allow: refresh"
    exec "$ROOT/server/refresh.sh"
    ;;
  "rsync --server "*)
    # rrsync が SSH_ORIGINAL_COMMAND を自前で再検査し、
    # 転送先を ROOT 配下に限定する。クライアントは ROOT からの
    # 相対パス (/web/ など) を指定する。
    log "allow: rsync"
    exec /usr/bin/rrsync "$ROOT"
    ;;
  *)
    log "reject: $CMD"
    echo "This key is restricted to calc-dojo deployment." >&2
    exit 1
    ;;
esac
