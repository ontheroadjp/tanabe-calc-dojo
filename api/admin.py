"""管理画面。フィードバックの閲覧と MathJax のバージョン確認。

認証が必要なのでサーバー側でHTMLを組み立てて返す。公開ディレクトリには置かない。
"""
from __future__ import annotations

import html
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import mathjax
from auth import (SESSION_COOKIE, SESSION_DAYS, SESSION_PATH, authenticate,
                  create_session, delete_session, user_for_session)
from db import connect

router = APIRouter(prefix="/admin")

BASE_PATH = "/calc-dojo/admin"
STYLE = "/calc-dojo/assets/style.css"


def e(v) -> str:
    return html.escape("" if v is None else str(v))


def page(title: str, body: str, user=None) -> HTMLResponse:
    nav = ""
    if user is not None:
        nav = f"""<nav class="site-nav"><span class="badge">{e(user['email'])}</span>
        <form method="post" action="{BASE_PATH}/logout" style="display:inline">
        <button class="linklike" type="submit">ログアウト</button></form></nav>"""
    return HTMLResponse(f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>{e(title)}｜管理</title><link rel="stylesheet" href="{STYLE}">
<style>
.admin-table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:15px}}
.admin-table th,.admin-table td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
.admin-table th{{font-size:13px;color:var(--muted);font-weight:700}}
.admin-table td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.admin-scroll{{overflow-x:auto}}
.linklike{{background:none;border:none;color:var(--accent);font:inherit;cursor:pointer;padding:0;text-decoration:underline}}
.note{{color:var(--muted);font-size:14px}}
.pill{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:700}}
.pill.ok{{background:var(--accent2);color:var(--accent)}}
.pill.warn{{background:var(--warm);color:#7a5b1e}}
.field{{display:block;margin:12px 0}}
.field input{{width:100%;padding:10px;border:1px solid var(--line);border-radius:10px;font:inherit}}
.btn{{padding:10px 18px;border:1px solid var(--line);border-radius:12px;background:#fff;font:inherit;cursor:pointer}}
pre.cmd{{background:#fafafa;border:1px solid var(--line);border-radius:10px;padding:12px;overflow-x:auto;font-size:14px}}
</style></head><body><main class="wrap">
<header class="sitehead"><a class="brand" href="{BASE_PATH}">たなべ式計算道場 管理</a>{nav}</header>
<section class="lesson">{body}</section>
<p class="footer-note">管理画面（非公開）</p></main></body></html>""")


def current_user(request: Request):
    return user_for_session(request.cookies.get(SESSION_COOKIE))


def require_admin(request: Request):
    user = current_user(request)
    if user is None or user["role"] != "admin":
        return None
    return user


# --- ログイン ---------------------------------------------------------

LOGIN_BODY = """<h1>ログイン</h1>
<form method="post" action="{base}/login">
<label class="field">メールアドレス<input type="email" name="email" required autocomplete="username"></label>
<label class="field">パスワード<input type="password" name="password" required autocomplete="current-password"></label>
{error}<button class="btn" type="submit">ログイン</button></form>"""


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> HTMLResponse:
    if require_admin(request):
        return RedirectResponse(BASE_PATH, status_code=303)
    return page("ログイン", LOGIN_BODY.format(base=BASE_PATH, error=""))


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = authenticate(email, password)
    if user is None or user["role"] != "admin":
        body = LOGIN_BODY.format(
            base=BASE_PATH,
            error='<p class="note">メールアドレスまたはパスワードが違います。</p>',
        )
        return page("ログイン", body)

    token, _expires = create_session(user["id"])
    res = RedirectResponse(BASE_PATH, status_code=303)
    res.set_cookie(
        SESSION_COOKIE, token,
        # expires に整数を渡すと「現在からの秒数」と解釈されるので max_age を使う
        max_age=SESSION_DAYS * 24 * 3600,
        path=SESSION_PATH,
        httponly=True,
        secure=request.headers.get("x-forwarded-proto", "http") == "https",
        samesite="lax",
    )
    return res


@router.post("/logout")
def logout(request: Request):
    if token := request.cookies.get(SESSION_COOKIE):
        delete_session(token)
    res = RedirectResponse(f"{BASE_PATH}/login", status_code=303)
    res.delete_cookie(SESSION_COOKIE, path=SESSION_PATH)
    return res


# --- ダッシュボード ---------------------------------------------------

def mathjax_section(force: bool) -> str:
    s = mathjax.status(force=force)
    current, latest = s["current"], s["latest"]

    if current is None:
        state = '<span class="pill warn">配信中のバージョンを取得できません</span>'
    elif latest is None:
        state = f'<span class="pill ok">{e(current)}</span> <span class="note">最新版を確認できませんでした</span>'
    elif s["update_available"]:
        state = (f'<span class="pill warn">更新あり</span> '
                 f'<span class="note">配信中 {e(current)} → 最新 {e(latest)}</span>')
    else:
        state = f'<span class="pill ok">最新です（{e(current)}）</span>'

    checked = f'<p class="note">最終確認: {e(s["checked_at"])}（UTC）</p>' if s["checked_at"] else ""

    how = ""
    if s["update_available"]:
        how = f"""<p>更新するには、リポジトリの <code>{e(s['pin_file'])}</code> にある
<code>{e(s['pin_line'])}</code> の行を書き換えて push してください。CD が自動で反映します。</p>
<pre class="cmd">-{e(s['pin_line'])}{e(current)}
+{e(s['pin_line'])}{e(latest)}</pre>
<p class="note">表示が崩れた場合は <code>git revert</code> で戻せます。
反映後、数式を含むページ（例: 倍数判定トレーニング）で表示を確認してください。</p>"""

    return f"""<h2>MathJax</h2><p>{state}</p>{checked}{how}
<form method="post" action="{BASE_PATH}/mathjax/check">
<button class="btn" type="submit">今すぐ確認する</button></form>"""


def feedback_section() -> str:
    with connect() as conn:
        summary = conn.execute("""
            SELECT page_slug,
                   SUM(feedback = 'helpful') AS helpful,
                   SUM(feedback = 'needs_more') AS needs_more,
                   COUNT(*) AS total
            FROM feedback GROUP BY page_slug ORDER BY total DESC, page_slug
        """).fetchall()
        comments = conn.execute("""
            SELECT created_at, page_slug, page_title, feedback, comment
            FROM feedback WHERE comment IS NOT NULL AND trim(comment) <> ''
            ORDER BY id DESC LIMIT 100
        """).fetchall()
        totals = conn.execute("""
            SELECT SUM(feedback = 'helpful') AS helpful,
                   SUM(feedback = 'needs_more') AS needs_more,
                   COUNT(*) AS total FROM feedback
        """).fetchone()

    if not totals["total"]:
        return "<h2>フィードバック</h2><p class=\"note\">まだ回答はありません。</p>"

    rows = "".join(
        f"<tr><td>{e(r['page_slug'])}</td><td class=\"num\">{r['helpful']}</td>"
        f"<td class=\"num\">{r['needs_more']}</td><td class=\"num\">{r['total']}</td></tr>"
        for r in summary
    )
    table = f"""<div class="admin-scroll"><table class="admin-table">
<tr><th>ページ</th><th>👍 役に立った</th><th>🤔 説明がほしい</th><th>合計</th></tr>
{rows}</table></div>"""

    if comments:
        crows = "".join(
            f"<tr><td class=\"num\">{e(r['created_at'])}</td><td>{e(r['page_title'])}"
            f"<br><span class=\"note\">{e(r['page_slug'])}</span></td>"
            f"<td>{e(r['comment'])}</td></tr>"
            for r in comments
        )
        clist = f"""<h3>コメント（新しい順・最大100件）</h3><div class="admin-scroll">
<table class="admin-table"><tr><th>日時 (UTC)</th><th>ページ</th><th>内容</th></tr>
{crows}</table></div>"""
    else:
        clist = '<p class="note">コメント付きの回答はまだありません。</p>'

    return (f"<h2>フィードバック</h2>"
            f"<p>合計 {totals['total']} 件（👍 {totals['helpful']} / 🤔 {totals['needs_more']}）</p>"
            f"{table}{clist}")


def dashboard(user, force: bool = False) -> HTMLResponse:
    body = (f'<span class="eyebrow">ADMIN</span><h1>管理画面</h1>'
            f'{mathjax_section(force)}{feedback_section()}')
    return page("管理画面", body, user=user)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    user = require_admin(request)
    if user is None:
        return RedirectResponse(f"{BASE_PATH}/login", status_code=303)
    return dashboard(user)


@router.post("/mathjax/check")
def mathjax_check(request: Request):
    user = require_admin(request)
    if user is None:
        return RedirectResponse(f"{BASE_PATH}/login", status_code=303)
    mathjax.latest_version(force=True)
    return RedirectResponse(BASE_PATH, status_code=303)
