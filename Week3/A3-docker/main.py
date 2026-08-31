from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional
import os
from dotenv import load_dotenv

# ── Load environment variables ────────────────────
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# ── Database setup ────────────────────────────────
engine = create_engine(DATABASE_URL, echo=False)

# ── SQLModel table ────────────────────────────────
class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    done: bool = False

# ── Pydantic input model ──────────────────────────
class TaskInput(BaseModel):
    title: str
    done: Optional[bool] = False

# ── Seed data ─────────────────────────────────────
SEED_TASKS = [
    {"title": "Buy groceries", "done": False},
    {"title": "Read a book",   "done": False},
    {"title": "Go for a walk", "done": True},
]

import time

def create_db_and_seed():
    for i in range(10):
        try:
            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                count = len(session.exec(select(Task)).all())
                if count == 0:
                    for t in SEED_TASKS:
                        session.add(Task(**t))
                    session.commit()
            break
        except Exception:
            print(f"DB not ready, retrying in 2s... ({i+1}/10)")
            time.sleep(2)
# ── App ───────────────────────────────────────────
app = FastAPI(
    title="Task API",
    description="CRUD API backed by Postgres in Docker",
    version="3.0"
)

# ── Root & health ─────────────────────────────────
@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "3.0",
        "storage": "PostgreSQL (Docker)",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Read ──────────────────────────────────────────
@app.get("/tasks")
def get_tasks():
    with Session(engine) as session:
        return session.exec(select(Task)).all()

@app.get("/tasks/{id}")
def get_task(id: int):
    with Session(engine) as session:
        task = session.get(Task, id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {id} not found")
        return task

# ── Create ────────────────────────────────────────
@app.post("/tasks", status_code=201)
def create_task(task: TaskInput):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    with Session(engine) as session:
        new_task = Task(title=task.title.strip(), done=task.done)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return new_task

# ── Update ────────────────────────────────────────
@app.put("/tasks/{id}")
def update_task(id: int, task: TaskInput):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    with Session(engine) as session:
        existing = session.get(Task, id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Task {id} not found")
        existing.title = task.title.strip()
        existing.done  = task.done
        session.commit()
        session.refresh(existing)
        return existing

# ── Delete ────────────────────────────────────────
@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    with Session(engine) as session:
        task = session.get(Task, id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {id} not found")
        session.delete(task)
        session.commit()