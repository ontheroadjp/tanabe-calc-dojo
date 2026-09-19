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
cd server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 10889
```

DB は初回起動時に `server/data/feedback.sqlite3` として自動作成されます。
別の場所に置く場合:

```sh
FEEDBACK_DB=/var/lib/calculation-power/feedback.sqlite3 \
  uvicorn app:app --host 127.0.0.1 --port 10889
```

## nginx

静的ファイルを nginx で配信し、API だけ FastAPI へ渡します。

```nginx
location = /api/feedback {
    proxy_pass http://127.0.0.1:10889;
    proxy_set_header Host $host;
}

location = /healthz {
    proxy_pass http://127.0.0.1:10889;
}
```

Web と API が同一オリジンになるので CORS 設定は不要です。

## 集計

公開管理画面は用意していません。サーバー上で:

```sh
python3 server/feedback_report.py
```

を実行すると、ページ別集計と最近の任意コメントを確認できます。

## バックアップ

SQLite なので、運用時は `feedback.sqlite3` と WAL を意識して
SQLite の backup API または `.backup` コマンドでバックアップしてください。
単純な稼働中ファイルコピーは避けるのが安全です。
