#!/bin/sh
# MathJax を npm から取得して assets/mathjax/ に配置する。
#
# 外部CDNに依存すると、CDN側の不調がそのままページの表示遅延になるため、
# 自サーバーから配信する。取得物は生成物なので git 管理しない。
#
# gzip_static 用に .gz も作る。nginx は gzip 対応クライアントへ .gz を
# そのまま返すので、リクエストごとの圧縮処理が発生しない。
set -eu

# CDN で配信されていた版に合わせる
VERSION=3.2.2

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="$ROOT/assets/mathjax"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "mathjax-full@$VERSION を取得中..."
cd "$WORK"
npm install --silent --no-audit --no-fund --no-package-lock "mathjax-full@$VERSION"

SRC="$WORK/node_modules/mathjax-full/es5/tex-svg.js"
[ -f "$SRC" ] || { echo "tex-svg.js が見つかりません: $SRC" >&2; exit 1; }

mkdir -p "$DEST"
cp "$SRC" "$DEST/tex-svg.js"
gzip -9 -c "$DEST/tex-svg.js" > "$DEST/tex-svg.js.gz"

printf '%s\n' "$VERSION" > "$DEST/VERSION"

ls -l "$DEST" | awk 'NR>1 {printf "  %-18s %10d bytes\n", $9, $5}'
