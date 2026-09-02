"""
AI-generated version of the Task CRUD API.
Generated via the prompt in ai-vs-me.md.
Placed in ai-version/ as instructed — the hand-built version in the parent folder
is the actual submission.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psycopg
import os
from dotenv import load_dotenv
import time

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev@db:5432/tasks")

app = FastAPI(title="Task API (AI-generated)", version="3.0-ai")

# ── Wait for DB ───────────────────────────────────
def get_conn():
    return psycopg.connect(DATABASE_URL)

def wait_for_db(retries: int = 15, delay: int = 2):
    for i in range(retries):
        try:
            with get_conn() as conn:
                conn.execute("SELECT 1")
            print("DB ready!")
            return
        except Exception as e:
            print(f"DB not ready ({i+1}/{retries}): {e}")
            time.sleep(delay)
    raise RuntimeError("Could not connect to DB after retries")

def init_db():
    wait_for_db()
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id   SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done  BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        row = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()
        if row[0] == 0:
            seeds = [
                ("Buy groceries", False),
                ("Read a book",   False),
                ("Go for a walk", True),
            ]
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (%s, %s)",
                seeds
            )
        conn.commit()

init_db()

# ── Models ────────────────────────────────────────
class TaskInput(BaseModel):
    title: str
    done: bool = False

# ── Routes ───────────────────────────────────────
@app.get("/")
def root():
    return {"name": "Task API (AI)", "version": "3.0-ai", "storage": "PostgreSQL"}

@app.get("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "db": str(e)})

@app.get("/tasks")
def get_tasks():
    with get_conn() as conn:
        rows = conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [{"id": r[0], "title": r[1], "done": r[2]} for r in rows]

@app.get("/tasks/{id}")
def get_task(id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT id, title, done FROM tasks WHERE id = %s", (id,)).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    return {"id": row[0], "title": row[1], "done": row[2]}

@app.post("/tasks", status_code=201)
def create_task(task: TaskInput):
    if not task.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
            (task.title.strip(), task.done)
        ).fetchone()
        conn.commit()
    return {"id": row[0], "title": row[1], "done": row[2]}

@app.put("/tasks/{id}")
def update_task(id: int, task: TaskInput):
    if not task.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
    with get_conn() as conn:
        row = conn.execute(
            "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
            (task.title.strip(), task.done, id)
        ).fetchone()
        conn.commit()
    if not row:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    return {"id": row[0], "title": row[1], "done": row[2]}

@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    with get_conn() as conn:
        result = conn.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (id,)).fetchone()
        conn.commit()
    if not result:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
