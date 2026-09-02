# A3 — Containerize your stack

A FastAPI task CRUD API backed by **PostgreSQL running in Docker**.  
The entire stack (app + database) starts with a single command.

---

## One-command startup

```bash
# 1. Copy the example env file
cp .env.example .env

# 2. Start everything
docker compose up
```

The API is available at **http://localhost:8000**.  
Swagger UI is at **http://localhost:8000/docs**.

---

## Environment variables

Copy `.env.example` to `.env` and fill in your values.

| Variable       | Description                          | Example                                          |
|----------------|--------------------------------------|--------------------------------------------------|
| `DATABASE_URL` | Full Postgres connection string      | `postgresql://postgres:dev@localhost:5432/tasks` |

> **Never commit `.env`** — it is git-ignored. Only `.env.example` is committed.

---

## Endpoints

| Method | Path            | Status codes       | Description                          |
|--------|-----------------|--------------------|--------------------------------------|
| GET    | `/`             | 200                | API info                             |
| GET    | `/health`       | 200 / 503          | Health check (pings DB with SELECT 1)|
| GET    | `/tasks`        | 200                | List all tasks                       |
| GET    | `/tasks/{id}`   | 200 / 404          | Get a single task                    |
| POST   | `/tasks`        | 201 / 400          | Create a task                        |
| PUT    | `/tasks/{id}`   | 200 / 400 / 404    | Update a task                        |
| DELETE | `/tasks/{id}`   | 204 / 404          | Delete a task                        |

---

## Sample curl session

```bash
# List all tasks (seeded automatically on first run)
curl -i http://localhost:8000/tasks

# HTTP/1.1 200 OK
# [{"id":1,"title":"Buy groceries","done":false},
#  {"id":2,"title":"Read a book","done":false},
#  {"id":3,"title":"Go for a walk","done":true}]

# Create a task
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Write docs", "done": false}'
# HTTP/1.1 201 Created  {"id":4,"title":"Write docs","done":false}

# Mark it done
curl -i -X PUT http://localhost:8000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"title": "Write docs", "done": true}'
# HTTP/1.1 200 OK  {"id":4,"title":"Write docs","done":true}

# Delete it
curl -i -X DELETE http://localhost:8000/tasks/4
# HTTP/1.1 204 No Content

# Unknown id → 404
curl -i http://localhost:8000/tasks/999
# HTTP/1.1 404 Not Found  {"error":"Task 999 not found"}
```

---

## Database screenshot

Connect to the running Postgres container to inspect data:

```bash
docker exec -it a3-docker-db-1 psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

```
 id |     title      | done
----+----------------+------
  1 | Buy groceries  | f
  2 | Read a book    | f
  3 | Go for a walk  | t
(3 rows)
```

---

## Persistence proof

```bash
docker compose up          # start
# ... create some tasks via curl ...
docker compose down        # stop + remove containers
docker compose up          # restart — tasks are still there (volume keeps them)
```

---

## How it works

| Layer          | Technology                        |
|----------------|-----------------------------------|
| Web framework  | FastAPI + Uvicorn                 |
| ORM / driver   | SQLModel (wraps psycopg / SQLAlchemy) |
| Database       | PostgreSQL 16 (official Docker image) |
| Orchestration  | Docker Compose                    |
| Secrets        | `.env` file (git-ignored)         |

The `tasks` table is created automatically on first startup.  
Three seed tasks are inserted only when the table is empty — idempotent.

---

## AI vs me

See [`ai-version/`](./ai-version/) for the full bonus stage write-up.

---

## Storage progression

| Assignment | Where tasks live        | What runs it          |
|------------|-------------------------|-----------------------|
| A1         | In-memory list          | Python process        |
| A2         | `tasks.db` SQLite file  | Disk (SQLite)         |
| A3 (this)  | Rows in PostgreSQL      | Docker container      |

Same API all the way down — storage is just an implementation detail.
