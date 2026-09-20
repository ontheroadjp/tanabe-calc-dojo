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

## ローカルで動かす

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

### 起動

本番では nginx が `/calc-dojo/` 配下で静的ファイルと API を振り分けています。
開発用サーバーは同じ振り分けを1プロセスで再現するので、管理画面も含めて
本番と同じパス構成で確認できます。

```sh
api/.venv/bin/python scripts/dev-server.py
```

| URL | 内容 |
|---|---|
| http://127.0.0.1:8000/calc-dojo/ | サイト |
| http://127.0.0.1:8000/calc-dojo/admin/login | 管理画面 |

静的ファイルだけを配信する `python3 -m http.server` でも講義ページは見られますが、
管理画面は動かず、フィードバック送信も失敗します。

### 管理画面にログインする

ローカル用のユーザーを作ります。パスワードは対話入力です。

```sh
cd api && .venv/bin/python manage_user.py add your-email@example.com --role admin
```

DB は `api/data/feedback.sqlite3` に作られます（git 管理外）。
別の場所を使うなら `FEEDBACK_DB` を指定します。

## HTML の整形

手で編集しやすいよう、HTML はタグごとに改行・インデントしています。整形には
prettier を使い、設定は `.prettierrc` にあります。

```sh
npx prettier --write "**/*.html"
```

`printWidth` を大きくしているのは、日本語の文章が折り返されるのを防ぐためです。
折り返すと改行が空白として描画され、文字間が開いてしまう可能性があります。
`htmlWhitespaceSensitivity: "css"` は既定値で、インライン要素の前後に
空白を入れないための設定です。

## フィードバック機能

各講義末尾に「👍 役に立った / 🤔 もう少し説明がほしい」を追加。`api/` の FastAPI API が SQLite に匿名保存します。詳しくは `api/README.md` を参照してください。
