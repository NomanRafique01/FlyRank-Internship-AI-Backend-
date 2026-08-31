from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import Optional

# ── Database setup ────────────────────────────────
DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL, echo=False)

# ── SQLModel table (schema) ───────────────────────
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

def create_db_and_seed():
    SQLModel.metadata.create_all(engine)          # Stage 0: create table if missing
    with Session(engine) as session:
        count = len(session.exec(select(Task)).all())
        if count == 0:                            # Seed only once
            for t in SEED_TASKS:
                session.add(Task(**t))
            session.commit()

create_db_and_seed()

# ── App ───────────────────────────────────────────
app = FastAPI(
    title="Task API",
    description="A simple CRUD API to manage your to-do list",
    version="2.0"
)

# ── Root & health ─────────────────────────────────
@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "2.0",
        "storage": "SQLite (tasks.db)",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Stage 1: Read ─────────────────────────────────
@app.get("/tasks")
def get_tasks():
    with Session(engine) as session:
        tasks = session.exec(select(Task)).all()
        return tasks

@app.get("/tasks/{id}")
def get_task(id: int):
    with Session(engine) as session:
        task = session.get(Task, id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {id} not found")
        return task

# ── Stage 2: Create ───────────────────────────────
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

# ── Stage 3: Update ───────────────────────────────
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

# ── Stage 3: Delete ───────────────────────────────
@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    with Session(engine) as session:
        task = session.get(Task, id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {id} not found")
        session.delete(task)
        session.commit()