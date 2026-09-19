#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
db = Path(os.environ.get("FEEDBACK_DB", BASE / "data" / "feedback.sqlite3"))

if not db.exists():
    raise SystemExit(f"DB not found: {db}")

with sqlite3.connect(db) as conn:
    print("=== page summary ===")
    for row in conn.execute("""
        SELECT page_slug,
               SUM(feedback='helpful') AS helpful,
               SUM(feedback='needs_more') AS needs_more,
               COUNT(*) AS total
        FROM feedback
        GROUP BY page_slug
        ORDER BY total DESC, page_slug
    """):
        print(f"{row[0]:45} helpful={row[1]:3} needs_more={row[2]:3} total={row[3]:3}")

    print("\n=== recent comments ===")
    for row in conn.execute("""
        SELECT created_at, page_slug, comment
        FROM feedback
        WHERE comment IS NOT NULL AND trim(comment) <> ''
        ORDER BY id DESC
        LIMIT 30
    """):
        print(f"[{row[0]}] {row[1]}\n  {row[2]}")
