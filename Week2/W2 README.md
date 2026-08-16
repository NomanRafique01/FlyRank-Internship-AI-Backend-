# W2 · A1 — Todo CRUD API

A fully functional REST API to manage a to-do list, built from scratch as part of the FlyRank AI Backend Internship (Week 2, Assignment 1).

**Author:** Noman Rafique · [@NomanRafique01](https://github.com/NomanRafique01)

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Language |
| FastAPI | Web framework |
| Uvicorn | ASGI server |
| Pydantic | Request validation |
| Swagger UI | Interactive API docs (built-in) |

---

## How to Install & Run

```bash
# 1. Install dependencies
pip install fastapi uvicorn

# 2. Start the server
python -m uvicorn main:app --reload
```

Server runs at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

---

## Endpoints

| Method | Path | Status Code | Description |
|--------|------|-------------|-------------|
| GET | `/` | 200 | API info |
| GET | `/health` | 200 | Health check |
| GET | `/tasks` | 200 | List all tasks |
| GET | `/tasks/{id}` | 200 / 404 | Get one task |
| POST | `/tasks` | 201 / 400 | Create a task |
| PUT | `/tasks/{id}` | 200 / 400 / 404 | Update a task |
| DELETE | `/tasks/{id}` | 204 / 404 | Delete a task |

---

## Data Model

Each task has three fields:

```json
{
  "id": 1,
  "title": "Buy groceries",
  "done": false
}
```

---

## Validation Rules

- `POST /tasks` — `title` is required and cannot be empty → `400`
- `PUT /tasks/{id}` — at least one field (`title` or `done`) must be provided → `400`
- `PUT /tasks/{id}` — `title` cannot be an empty string → `400`
- Any unknown `id` on GET, PUT, DELETE → `404`

---

## Sample curl Output

```bash
$ curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy milk"}'

HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

---

## Swagger UI

FastAPI generates interactive documentation automatically at `/docs`.
Every endpoint is listed with a **Try it out** button that sends real requests.

![Swagger UI](swagger-screenshot.png)

---

## Commit History

| Commit | Description |
|--------|-------------|
| `Stage 0: hello server` | FastAPI server running on localhost:8000 |
| `Stage 1: root and health endpoints` | GET / and GET /health |
| `Stage 2: read endpoints with 404` | GET /tasks and GET /tasks/{id} |
| `Stage 3: create with validation` | POST /tasks with Pydantic validation |
| `Stage 4: full CRUD` | PUT and DELETE endpoints |
| `Stage 5: Swagger UI` | FastAPI title and description added |
| `Stage 6: publish and docs` | README and GitHub publish |

---

## Storage Note

This API uses **in-memory storage** — data lives in a Python list and resets every time the server restarts. This is intentional for Week 2. A real database (Week 3) solves this permanently.
