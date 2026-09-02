from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select, text
from typing import Optional
import os
import time
from dotenv import load_dotenv

# ── Load environment variables ────────────────────
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev@db:5432/tasks")

# ── Database setup ────────────────────────────────
engine = create_engine(DATABASE_URL, echo=True)

# ── SQLModel table ────────────────────────────────
class Task(SQLModel, table=True):
    __tablename__ = "tasks"
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
    for i in range(15):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("DB is ready!")
            break
        except Exception as e:
            print(f"DB not ready ({i+1}/15), retrying in 2s... {e}")
            time.sleep(2)

    SQLModel.metadata.create_all(engine)
    print("Tables created!")

    with Session(engine) as session:
        count = len(session.exec(select(Task)).all())
        if count == 0:
            for t in SEED_TASKS:
                session.add(Task(**t))
            session.commit()
            print("Seeded 3 tasks!")

create_db_and_seed()

# ── App ───────────────────────────────────────────
app = FastAPI(
    title="Task API",
    description="CRUD API backed by Postgres in Docker",
    version="3.0"
)

@app.get("/")
def root():
    return {"name": "Task API", "version": "3.0", "storage": "PostgreSQL (Docker)"}

@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "db": str(e)})

@app.get("/tasks")
def get_tasks():
    with Session(engine) as session:
        return session.exec(select(Task)).all()

@app.get("/tasks/{id}")
def get_task(id: int):
    with Session(engine) as session:
        task = session.get(Task, id)
        if not task:
            return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
        return task

@app.post("/tasks", status_code=201)
def create_task(task: TaskInput):
    if not task.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
    with Session(engine) as session:
        new_task = Task(title=task.title.strip(), done=task.done)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return new_task

@app.put("/tasks/{id}")
def update_task(id: int, task: TaskInput):
    if not task.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})
    with Session(engine) as session:
        existing = session.get(Task, id)
        if not existing:
            return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
        existing.title = task.title.strip()
        existing.done  = task.done
        session.commit()
        session.refresh(existing)
        return existing

@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    with Session(engine) as session:
        task = session.get(Task, id)
        if not task:
            return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
        session.delete(task)
        session.commit()