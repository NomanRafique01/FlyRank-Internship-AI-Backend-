# AI vs Me — Stage 6

## My prompt

> I'm building a Python task CRUD API (FastAPI, Python lane) and I need you to containerize it
> with PostgreSQL running in Docker. Requirements:
>
> - Use the raw `psycopg` driver (psycopg3, `%s` placeholders for parameterized queries — never
>   glue user input into SQL strings).
> - The `tasks` table must be created automatically on startup: columns `id SERIAL PRIMARY KEY`,
>   `title TEXT NOT NULL`, `done BOOLEAN NOT NULL DEFAULT FALSE`.
> - Seed exactly three tasks on the very first run — only when the table is empty (idempotent).
> - Five endpoints with identical behaviour to the hand-built version:
>   `GET /tasks`, `GET /tasks/{id}`, `POST /tasks` (201), `PUT /tasks/{id}`, `DELETE /tasks/{id}` (204).
> - Unknown id → 404 `{"error": "..."}`. Missing/empty title → 400 `{"error": "..."}`.
> - The DB password must come from a `.env` file via `DATABASE_URL` — never hardcoded.
> - Use Docker Compose with two services: `api` and `db` (official postgres image).
> - Mount a named volume so data persists across `docker compose down && docker compose up`.
> - Inside the compose network the app must reach the DB by service name `db`, not `localhost`.
> - Include a `GET /health` endpoint that runs `SELECT 1` and returns `{"status":"ok","db":"ok"}`.

---

## Did it work first try?

`docker compose up` — **yes**, app started and connected to the DB.  
Create tasks → `down` → `up` → tasks still there ✅ (volume was included).

---

## Three concrete differences

| # | What I compared | My hand-built version | AI-generated version |
|---|----------------|-----------------------|----------------------|
| 1 | **ORM vs raw SQL** | Uses SQLModel (ORM) — less boilerplate, automatic schema from the Python class | Uses raw `psycopg` with explicit `CREATE TABLE` and `%s` placeholders — closer to what the assignment teaches |
| 2 | **Dockerfile structure** | Single `RUN pip install` with all packages inline | Copies `requirements.txt` first then installs — better Docker layer caching (only reinstalls when deps change) |
| 3 | **DB readiness retry** | Retries up to 15 times with `SELECT 1` before calling `create_all` | Same retry logic, but extracted into a named `wait_for_db()` helper — cleaner separation |

### What the AI did better
- Copied `requirements.txt` before the app code → better build-cache reuse.
- Used explicit raw SQL for the table definition — directly matches what psycopg docs show.

### What the AI got right that I almost missed
- Named the volume `taskdata_ai` in its compose to avoid clashing with the parent folder's volume.

### What my prompt forgot to specify
- I didn't say which port to expose on the host — the AI defaulted to `8001` to avoid clashing with my version. I should have been explicit.
- I didn't mention `depends_on` health condition (`service_healthy`) — neither version uses it, but a production stack would.

---

## One rematch — improved prompt

Added: "Expose port **8000** on the host. Use `depends_on` with a `healthcheck` on the `db`
service so the API waits for Postgres to be *healthy* before starting, instead of using a manual retry loop."

After regenerating, the AI produced a proper `healthcheck` block in the compose file and removed the manual
retry loop from the Python code — cleaner and more idiomatic. The manual retry is a workaround; a proper
`depends_on: condition: service_healthy` is the right solution.

---

## The lesson

> An AI's output is exactly as good as your specification — and you could only judge it because
> you built the thing yourself first.

Both halves of that sentence are true here. I could immediately spot the missing port, the missing
healthcheck condition, and the ORM/raw-SQL trade-off — because I had already made each of those
decisions myself.
