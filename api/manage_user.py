#!/usr/bin/env python3
"""ユーザーの作成・更新・一覧。

パスワードは対話的に入力する。引数には渡さない（シェル履歴やプロセス一覧に
残るため）。サーバー上で実行する:

    cd <root>/api && .venv/bin/python manage_user.py add your-email@example.com --role admin
    cd <root>/api && .venv/bin/python manage_user.py passwd your-email@example.com
    cd <root>/api && .venv/bin/python manage_user.py list
"""
from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys

from auth import hash_password
from db import connect, init_db, now

ROLES = ("admin", "free", "paid")


def ask_password() -> str:
    pw = getpass.getpass("パスワード: ")
    if len(pw) < 12:
        sys.exit("パスワードは12文字以上にしてください。")
    if pw != getpass.getpass("確認のためもう一度: "):
        sys.exit("一致しません。")
    return pw


def cmd_add(args) -> None:
    email = args.email.strip().lower()
    pw = ask_password()
    try:
        with connect() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (email, hash_password(pw), args.role, now()),
            )
    except sqlite3.IntegrityError:
        sys.exit(f"{email} は既に登録されています。パスワード変更は passwd を使ってください。")
    print(f"作成しました: {email} (role={args.role})")


def cmd_passwd(args) -> None:
    email = args.email.strip().lower()
    with connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone() is None:
            sys.exit(f"{email} は登録されていません。")
    pw = ask_password()
    with connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE email = ?",
                     (hash_password(pw), email))
        # パスワードを変えたら既存のセッションは無効にする
        conn.execute(
            "DELETE FROM sessions WHERE user_id = (SELECT id FROM users WHERE email = ?)",
            (email,),
        )
    print(f"変更しました: {email}（既存のログインは無効化されました）")


def cmd_role(args) -> None:
    email = args.email.strip().lower()
    with connect() as conn:
        cur = conn.execute("UPDATE users SET role = ? WHERE email = ?", (args.role, email))
        if cur.rowcount == 0:
            sys.exit(f"{email} は登録されていません。")
    print(f"変更しました: {email} -> {args.role}")


def cmd_list(_args) -> None:
    with connect() as conn:
        rows = conn.execute(
            "SELECT email, role, created_at, last_login_at FROM users ORDER BY id"
        ).fetchall()
    if not rows:
        print("ユーザーは登録されていません。")
        return
    print(f"{'email':40} {'role':6} {'created':20} last_login")
    for r in rows:
        print(f"{r['email']:40} {r['role']:6} {r['created_at']:20} {r['last_login_at'] or '-'}")


def main() -> None:
    init_db()
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="ユーザーを作成する")
    a.add_argument("email")
    a.add_argument("--role", choices=ROLES, default="free")
    a.set_defaults(func=cmd_add)

    c = sub.add_parser("passwd", help="パスワードを変更する")
    c.add_argument("email")
    c.set_defaults(func=cmd_passwd)

    r = sub.add_parser("role", help="権限を変更する")
    r.add_argument("email")
    r.add_argument("role", choices=ROLES)
    r.set_defaults(func=cmd_role)

    sub.add_parser("list", help="一覧を表示する").set_defaults(func=cmd_list)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
