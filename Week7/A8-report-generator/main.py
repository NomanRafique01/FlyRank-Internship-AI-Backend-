from datetime import datetime
import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from report import getReportData
from renderer import generate_html, render_pdf

DB_PATH = "report.db"

app = FastAPI(title="PDF Report Generator")


class ReportRequest(BaseModel):
    force: Optional[bool] = False


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports")
async def create_report(req: Optional[ReportRequest] = None):
    init_db()
    force = req.force if req else False
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Stage 5 Idempotency check: if report already exists for today and not forced, return existing
    if not force:
        cur.execute(
            "SELECT id, path FROM reports WHERE date(created_at) = ? ORDER BY id DESC LIMIT 1",
            (today,),
        )
        existing = cur.fetchone()
        if existing and os.path.exists(existing[1]):
            conn.close()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"id": existing[0], "file": f"/reports/{existing[0]}/file"},
            )

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO reports (path, created_at) VALUES (?, ?)", ("", now_str)
    )
    report_id = cur.lastrowid
    pdf_path = f"reports/{report_id}.pdf"
    cur.execute(
        "UPDATE reports SET path = ? WHERE id = ?", (pdf_path, report_id)
    )
    conn.commit()
    conn.close()

    report_data = getReportData(DB_PATH)
    html_content = generate_html(report_data)
    await render_pdf(html_content, pdf_path)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": report_id, "file": f"/reports/{report_id}/file"},
    )


@app.get("/reports/{id}")
def get_report(id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, path, created_at FROM reports WHERE id = ?", (id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Report {id} not found")

    return {
        "id": row[0],
        "path": row[1],
        "created_at": row[2],
        "file": f"/reports/{row[0]}/file",
    }


@app.get("/reports/{id}/file")
def get_report_file(id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT path FROM reports WHERE id = ?", (id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Report {id} not found")

    file_path = row[0]
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail=f"Report file {file_path} not found on disk"
        )

    return FileResponse(
        file_path, media_type="application/pdf", filename=f"report-{id}.pdf"
    )
