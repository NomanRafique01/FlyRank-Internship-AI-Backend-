from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(
    title="Task API",
    description="A simple CRUD API to manage your to-do list",
    version="1.0"
)

# ── in-memory "database" ──────────────────────────
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Read a book",   "done": False},
    {"id": 3, "title": "Go for a walk", "done": True},
]


# ── Stage 1 endpoints ─────────────────────────────
@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Stage 2 endpoints ─────────────────────────────
@app.get("/tasks")
def get_tasks():
    return tasks

@app.get("/tasks/{id}")
def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {id} not found")

# add this class after your tasks list
class TaskInput(BaseModel):
    title: str

# add this endpoint at the bottom
@app.post("/tasks", status_code=201)
def create_task(task: TaskInput):
    if not task.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    new_task = {
        "id": len(tasks) + 1,
        "title": task.title,
        "done": False
    }
    tasks.append(new_task)
    return new_task