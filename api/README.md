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

nginx 設定は `server/refresh.sh` がデプロイのたびに
`calc-dojo.conf.example` から `calc-dojo.conf` を生成します。`alias` と
`proxy_pass` は絶対パスを要求しますが、このリポジトリは public なので
サーバーのパスを含む実ファイルは置けません。そのためテンプレート方式です。

`/etc` 側は生成された `calc-dojo.conf` への symlink なので、初回に一度
symlink を張れば以降の更新は自動で反映されます。

```
/etc/nginx/conf.d/<site>/calc-dojo.conf
  -> <root>/server/calc-dojo.conf
```

ただし nginx の reload には root 権限が必要で、デプロイ鍵では実行できません。
設定に変更があったときは `refresh.sh` が次のように出力するので、手動で
reload してください。

```
nginx 設定を更新しました。反映するには:
  sudo nginx -t && sudo systemctl reload nginx
```

内容が変わっていないときは何も出力せず、ファイルも書き換えません。

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

## CD (GitHub Actions)

`main` への push で `.github/workflows/deploy.yml` が走り、静的サイトと API を
配信して pm2 を再起動します。手動実行は Actions タブの workflow_dispatch から。

リポジトリが public なので、サーバー固有の情報はワークフローに書かず
Secrets から渡します。

| Secret | 内容 |
|---|---|
| `DEPLOY_HOST` | サーバーのホスト名 |
| `DEPLOY_USER` | ssh ユーザー名 |
| `DEPLOY_SSH_KEY` | 秘密鍵 (パスフレーズなし) |
| `DEPLOY_KNOWN_HOSTS` | `ssh-keyscan <host>` の出力 |
| `DEPLOY_BASE_URL` | 任意。設定するとデプロイ後に疎通確認を行う |

`DEPLOY_ROOT` (設置先の絶対パス) も登録されているが、forced command の
導入でワークフローからは参照しなくなった。forced command を外して
転送先を絶対パス指定に戻す場合に備えて残してある。

初期設定:

```sh
# 1. デプロイ専用の鍵を作る
ssh-keygen -t ed25519 -N '' -C 'github-actions-calc-dojo' -f ~/.ssh/calc_dojo_deploy

# 2. 公開鍵をサーバーの ~/.ssh/authorized_keys に追記する。
#    -f は必須。付けないと ssh-copy-id が「新しい鍵でログインできるか」で
#    判定するため、ssh_config の IdentityFile など既存の鍵でログインが
#    成功してしまい「登録済み」と誤判定して何もしない。
ssh-copy-id -f -i ~/.ssh/calc_dojo_deploy.pub <server>

# 3. Secrets を登録する
gh secret set DEPLOY_SSH_KEY < ~/.ssh/calc_dojo_deploy
ssh-keyscan <host> | gh secret set DEPLOY_KNOWN_HOSTS
gh secret set DEPLOY_HOST --body '<host>'
gh secret set DEPLOY_USER --body '<user>'
gh secret set DEPLOY_BASE_URL --body 'https://<host>/calc-dojo'
```

`.venv` `data/` `run/` `.pm2` は転送対象外です。サーバー側で生成・保持され、
デプロイで上書きされません。`requirements.txt` の差分はデプロイのたびに
`pip install` で反映されます。

### デプロイ鍵の制限 (forced command)

このサーバーは他のコンテンツもホストしているため、デプロイ鍵には
シェルを渡さない。`authorized_keys` の該当行に `command=` を付け、
`server/deploy-shell.sh` を強制実行させる。

```
command="<root>/server/deploy-shell.sh",restrict ssh-ed25519 AAAA... github-actions-calc-dojo
```

`command=` は**その鍵で認証したときだけ**適用される。同じ
`authorized_keys` にある他の鍵や、他サービスの rsync には影響しない。

許可されるのは2つだけで、それ以外は拒否される。

| 要求 | 動作 |
|---|---|
| `rsync --server ...` | `rrsync` に渡す。転送先が `<root>` 配下に強制される |
| `refresh` | `server/refresh.sh` を実行 |

そのためワークフローの転送先は `<root>` からの相対パス (`/web/` など) で
指定する。`DEPLOY_ROOT` が不要なのはこのため。

検証するときは `-F /dev/null` で ssh_config を無視すること。`-i` と
`IdentitiesOnly=yes` だけでは ssh_config の `IdentityFile` が併用され、
個人鍵にフォールバックして「制限が効いていない」ように見える。

```sh
ssh -F /dev/null -i ~/.ssh/calc_dojo_deploy -o IdentityAgent=none \
  <user>@<host> whoami
# => This key is restricted to calc-dojo deployment.
```

なお、これでシェルアクセスは塞げるが任意コード実行が完全に防げるわけでは
ない。デプロイは `api/requirements.txt` を転送してから `pip install` するので、
鍵を奪われれば細工した requirements.txt 経由でコードを実行させられる。
効果があるのは書き込み範囲が `<root>` 配下に限定される点と、`/etc` や
他アプリのディレクトリ、ポート転送による踏み台化が塞がれる点。

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
