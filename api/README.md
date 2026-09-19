# Feedback API

講義末尾のフィードバックを SQLite に保存する最小構成です。

保存する項目:

- `page_slug`
- `page_title`
- `feedback`: `helpful` / `needs_more`
- `comment`: 任意
- `created_at`: UTC

IP アドレス、Cookie、User-Agent などは保存しません。

## 起動

```sh
cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./start.sh
```

`start.sh` は unix socket (`api/run/api.sock`) で listen します。
TCP ポート番号はサーバー全体で共有される資源なので、他サービスと
衝突しないよう socket を使い、すべて `api/` 配下で完結させています。

DB は起動時に `api/data/feedback.sqlite3` として自動作成されます。
別の場所に置く場合は `FEEDBACK_DB` を渡します:

```sh
FEEDBACK_DB=/var/lib/calc-dojo/feedback.sqlite3 ./start.sh
```

TCP で動かしたい場合は `start.sh` を使わず直接:

```sh
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 10889
```

## nginx

静的ファイルを nginx で配信し、API だけ FastAPI へ渡します。
サブディレクトリ配信の場合、完全一致 (`=`) の location は `^~` より
優先されるため、静的配信の location と併記できます。

```nginx
location ^~ /calc-dojo/ {
    alias <root>/web/;
    index index.html;
    try_files $uri $uri/ =404;
}

location = /calc-dojo/api/feedback {
    proxy_pass http://unix:<root>/api/run/api.sock:/api/feedback;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Web と API が同一オリジンになるので CORS 設定は不要です。
`assets/feedback.js` は自身のスクリプトURLから API の位置を求めるので、
ドキュメントルート配信でもサブディレクトリ配信でもそのまま動きます。

## デプロイ

サーバー上では `calc-dojo/` の下をリポジトリと同じ3つに分けます。

```
<root>/                       サーバー上の設置先
├── web/      静的サイト (nginx が alias で配信するのはここだけ)
├── api/      FastAPI 本体・.venv・run/api.sock・data/feedback.sqlite3・.pm2
└── server/   nginx 設定と pm2 の ecosystem ファイル
```

API は他サービスから独立して動きます。共有しているのは OS の python3 だけで、
依存パッケージは `api/.venv`、listen は `api/run/api.sock`、pm2 の状態は
`api/.pm2` と、すべて `calc-dojo/` の中に閉じています。

| サーバー上 | リポジトリ |
|---|---|
| `calc-dojo/web/` | `index.html` `about.html` `assets/` `mental/` `multiple/` `view/` |
| `calc-dojo/api/` | `api/` + `.venv` + `data/` |
| `calc-dojo/server/` | `server/` |

alias が指すのは `web/` なので、`api/` と `server/` は同じ親ディレクトリに
ありながら web からは一切参照できません。alias を `calc-dojo/` に向けると
`app.py` や SQLite DB が直接ダウンロードできてしまうので注意してください。

nginx 設定はテンプレートから実ファイルを生成し、nginx の設定ディレクトリ
から symlink します。生成物 `server/calc-dojo.conf` はサーバー固有の絶対パスを
含むため git 管理外です。

```sh
cd <root>/server
sed "s|__ROOT__|$(cd .. && pwd)|g" calc-dojo.conf.example > calc-dojo.conf
# 生成した calc-dojo.conf を nginx の設定ディレクトリから symlink し、reload
```

symlink にしておけば、設定を変えたときは rsync して nginx を reload するだけで
反映されます。

プロセス管理は systemd を使わず pm2 で行います。既定の pm2 デーモン
(`~/.pm2`) は他サービスと共有なので、必ず専用の `PM2_HOME` を指定します。

```sh
export PM2_HOME=<root>/api/.pm2

pm2 start <root>/server/ecosystem.config.js
pm2 save                       # 再起動後の復元用
pm2 logs calc-dojo-feedback
pm2 restart calc-dojo-feedback # api/ を更新したら実行する
```

再起動後の自動復帰は user crontab で行います (`pm2 startup` は systemd
ユニットを作るので使いません)。

```
@reboot PM2_HOME=<root>/api/.pm2 /usr/bin/pm2 resurrect
```

更新時:

```sh
# 静的サイト
rsync -avz --delete index.html about.html assets mental multiple view \
  <server>:<root>/web/

# API (更新後に pm2 restart calc-dojo-feedback)
rsync -avz --exclude='__pycache__' --exclude='data' --exclude='.venv' api/ \
  <server>:<root>/api/

# 設定ファイル
rsync -avz server/ <server>:<root>/server/
```

## 集計

公開管理画面は用意していません。サーバー上で:

```sh
cd <root>/api && python3 feedback_report.py
```

を実行すると、ページ別集計と最近の任意コメントを確認できます。

## バックアップ

SQLite なので、運用時は `feedback.sqlite3` と WAL を意識して
SQLite の backup API または `.backup` コマンドでバックアップしてください。
単純な稼働中ファイルコピーは避けるのが安全です。
