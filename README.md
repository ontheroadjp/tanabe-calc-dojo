# 計算力 講義サイト

中学受験算数の「計算力」を講義形式で体系的に学ぶ静的サイトです。

## 暗算力トレーニング

- 暗算の土台
  - 補数
  - 九九
  - 逆九九
- 暗算
  - たし算・ひき算
  - 11×11〜19×19
  - 2桁×1桁
  - 1桁で割るわり算

ほかに「倍数判定トレーニング」「数の見方トレーニング」があります。
ビルド工程のない静的HTML/CSS構成です。数式表示に MathJax、フィードバック送信に
小さなスクリプトを使います。

## 開発

よく使うコマンドです。すべてリポジトリのルートで実行します。

| したいこと | コマンド |
|---|---|
| 開発サーバーを起動する | `api/.venv/bin/python scripts/dev-server.py` |
| HTML を整形する | `npx prettier --write "**/*.html"` |
| 管理ユーザーを作る | `cd api && .venv/bin/python manage_user.py add <メール> --role admin` |
| 本番へ反映する | `git push origin main`（CD が自動でデプロイ） |

### 準備（最初の一度だけ）

MathJax は外部CDNではなく自サーバーから配信します（CDNの不調がそのまま
表示遅延になるため）。取得物は git 管理外なので、最初に取得します。

```sh
./scripts/fetch-mathjax.sh          # assets/mathjax/ に配置

cd api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ..
```

デプロイ時は CD が同じ手順を実行するので、サーバー側の手動準備は不要です。

### 開発サーバーを起動する

```sh
api/.venv/bin/python scripts/dev-server.py
```

| URL | 内容 |
|---|---|
| http://127.0.0.1:8000/calc-dojo/ | サイト |
| http://127.0.0.1:8000/calc-dojo/admin/login | 管理画面 |

停止は `Ctrl+C` です。ポートは 8000 で固定しています。

本番では nginx が `/calc-dojo/` 配下で静的ファイルと API を振り分けています。
`scripts/dev-server.py` は同じ振り分けを1プロセスで再現するので、管理画面まで
含めて本番と同じパス構成で確認できます。

静的ファイルだけを配信する `python3 -m http.server` でも講義ページは見られますが、
パス構成が違うため管理画面は動かず、フィードバック送信も失敗します。

### HTML を整形する

手で編集しやすいよう、HTML はタグごとに改行し、4文字でインデントしています。
編集して崩れたら、次のコマンドで揃えられます。

```sh
npx prettier --write "**/*.html"
```

設定は `.prettierrc` にあるので、引数は不要です。特定のファイルだけ整形するなら
パスを渡します。

```sh
npx prettier --write mental/addition-subtraction.html
```

設定の意図は次のとおりです。

| 設定 | 理由 |
|---|---|
| `tabWidth: 4` | インデント幅 |
| `printWidth: 100000` | 日本語の文章を折り返させないため。折り返すと改行が空白として描画され、文字間が開く可能性がある |
| `htmlWhitespaceSensitivity: "css"` | 既定値。インライン要素の前後に空白を入れず、描画を変えないため |

手で編集するときも、`<p>` の中身など**文章の途中では改行しない**でください。
同じ理由で文字間が開くことがあります。

### 管理画面にログインする

ローカル用のユーザーを作ります。パスワードは対話入力です（引数には渡しません）。

```sh
cd api && .venv/bin/python manage_user.py add your-email@example.com --role admin
```

DB は `api/data/feedback.sqlite3` に作られます（git 管理外）。
別の場所を使うなら `FEEDBACK_DB` を指定します。

運用や本番構成の詳細は `api/README.md` を参照してください。

## フィードバック機能

各講義末尾に「👍 役に立った / 🤔 もう少し説明がほしい」を追加。`api/` の FastAPI API が SQLite に匿名保存します。詳しくは `api/README.md` を参照してください。
