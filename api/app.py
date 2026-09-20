from __future__ import annotations

import sqlite3
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import admin
from db import connect, init_db, now

app = FastAPI(title="Calculation Dojo API", docs_url=None, redoc_url=None)
app.include_router(admin.router)


class FeedbackIn(BaseModel):
    page_slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-zA-Z0-9_./-]+$")
    page_title: str = Field(min_length=1, max_length=200)
    feedback: Literal["helpful", "needs_more"]
    comment: str | None = Field(default=None, max_length=1000)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/api/feedback", status_code=201)
def create_feedback(item: FeedbackIn) -> dict[str, bool]:
    comment = item.comment.strip() if item.comment else None
    if comment == "":
        comment = None

    try:
        with connect() as conn:
            conn.execute(
                """INSERT INTO feedback
                   (page_slug, page_title, feedback, comment, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item.page_slug, item.page_title, item.feedback, comment, now()),
            )
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Could not save feedback") from exc

    return {"ok": True}


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}
