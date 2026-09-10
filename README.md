<p align="center">
  <img src="assets/flyrank%20logo.png" alt="FlyRank AI" width="100%" />
</p>

# FlyRank AI Backend Internship

**A practical backend engineering portfolio by [Noman Rafique](https://github.com/NomanRafique01).**

This repository contains the work completed during the FlyRank AI Backend Engineering Internship. It follows the progression from a small REST API to persistent storage, containerized services, responsible web data extraction, automated PDF reporting, and a production-minded AI usage metering and billing engine.

The projects are intentionally kept in their own assignment folders. Each folder has its own README with the commands, architecture decisions, test evidence, and implementation details for that assignment.

## What is covered

| Stage | Project | Main concepts | Technologies |
| --- | --- | --- | --- |
| Week 2 | [Todo CRUD API](Week2/) | REST design, validation, HTTP status codes | Python, FastAPI, Uvicorn |
| Week 3 | [SQLite persistence](Week3/A2-database/) | ORM-backed storage, durable data | Python, FastAPI, SQLModel, SQLite |
| Week 3 | [Dockerized API](Week3/A3-docker/) | Service composition, environment configuration, PostgreSQL | FastAPI, SQLModel, PostgreSQL, Docker Compose |
| Week 5 | [Polite scraper](Week5/A9-scraper/) | Caching, retries, validation, failure reporting | Requests, BeautifulSoup, Pydantic |
| Week 7 | [PDF report generator](Week7/A8-report-generator/) | SQL aggregation, HTML-to-PDF generation, idempotency | FastAPI, SQLite, Playwright, Chromium |
| Capstone | [Usage metering and billing engine](flyrank-capstone-metering-billing/) | AI token accounting, quotas, replay protection, billing webhooks | FastAPI, SQLite, Stripe, OpenRouter |

## Capstone highlight

The capstone is the most complete service in the repository. It provides a billable AI generation endpoint with:

- Idempotency-key support for safe request retries.
- Atomic usage-event recording and replay responses.
- Separate input, cached-input, output, and reasoning token pricing.
- Plan-based call and token quotas.
- Payment-state enforcement with appropriate HTTP responses.
- Stripe webhook signature verification and event deduplication.
- Deterministic local simulation when an OpenRouter key is not configured.
- Automated acceptance probes in `test_engine.py`.

See the [capstone README](flyrank-capstone-metering-billing/README.md) for the full API contract, pricing rules, setup steps, and limitations.

## Repository layout

```text
.
├── assets/                         # Static repository artwork
├── Week2/                          # First FastAPI CRUD service
├── Week3/
│   ├── A2-database/                # CRUD API with SQLite
│   └── A3-docker/                  # FastAPI + PostgreSQL + Docker Compose
├── Week5/A9-scraper/               # Cached and validated scraping pipeline
├── Week7/A8-report-generator/      # SQL-backed PDF reporting service
├── flyrank-capstone-metering-billing/ # AI metering and billing engine
├── flyrank-assignment-solver.md    # Assignment workflow and conventions
└── README.md
```

## Getting started

Clone the repository, then open the README inside the assignment you want to run:

```bash
git clone https://github.com/NomanRafique01/FlyRank-Internship-AI-Backend-.git
cd FlyRank-Internship-AI-Backend-
```

Each project is independently runnable. The usual Python workflow is:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Some assignments have additional requirements. The Docker assignment needs Docker Desktop, and the report generator needs Playwright's Chromium browser. Follow the project-specific README before starting its server.

## Engineering practices

- Build assignments incrementally and preserve the behavior of earlier stages.
- Keep configuration and secrets out of source control with `.env` files and committed examples where needed.
- Validate inputs at the API boundary and use explicit HTTP status codes.
- Prefer idempotent seeders, repeatable commands, and observable run reports.
- Document the reasoning behind storage, scraping, reporting, pricing, and deployment choices.
- Test the important behavior instead of treating a successful server startup as proof of correctness.

## Author

**Noman Rafique**  
BS Artificial Intelligence, NFC IET Multan, Pakistan  
[GitHub](https://github.com/NomanRafique01)