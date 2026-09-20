"""パスワードとセッション。

外部ライブラリを増やさず、標準ライブラリの scrypt と secrets で構成する。
scrypt はメモリ困難なハッシュで、パスワード保存に適している。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from db import connect, now

# scrypt のコスト。n を上げるほど安全だが検証も遅くなる。
# 必要メモリは 128 * N * r で約32MB。OpenSSL の既定上限がちょうど32MBで
# 超過扱いになるため、maxmem を明示して余裕を持たせる。
_N, _R, _P = 2**15, 8, 1
_MAXMEM = 128 * _N * _R * 2
_SALT_BYTES = 16

SESSION_COOKIE = "calc_dojo_session"
SESSION_DAYS = 14
# 管理画面だけに送られるようにする。静的ページやフィードバック送信には付かない。
SESSION_PATH = "/calc-dojo/admin"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, maxmem=_MAXMEM)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, dk_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), maxmem=128 * int(n) * int(r) * 2,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


def create_session(user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now(), expires.isoformat(timespec="seconds")),
        )
    return token, expires


def delete_session(token: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def user_for_session(token: str | None):
    """有効なセッションに対応する user 行を返す。無効なら None。"""
    if not token:
        return None
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now(),))
        return conn.execute(
            """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at >= ?""",
            (token, now()),
        ).fetchone()


def authenticate(email: str, password: str):
    """メールとパスワードが合っていれば user 行を返す。合わなければ None。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()

    # ユーザーが無い場合もハッシュ計算を行い、応答時間から存在を推測されないようにする
    stored = row["password_hash"] if row else hash_password("dummy")
    if not verify_password(password, stored) or row is None:
        return None

    with connect() as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now(), row["id"]))
    return row
