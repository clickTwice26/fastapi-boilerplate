# FastAPI Boilerplate

Production-minded FastAPI starter with PostgreSQL, Redis, SQLAlchemy, Alembic migrations, response caching, request rate limiting, Docker Compose, and sample endpoints.

## Features

- FastAPI application factory with lifespan-managed resources
- PostgreSQL with SQLAlchemy 2.x async ORM
- Alembic migrations
- Redis client setup
- Redis-backed cache service
- Redis-backed rate limiter middleware
- Pydantic settings loaded from `.env`
- Docker Compose for API, PostgreSQL, and Redis
- Health, cache demo, and user CRUD sample endpoints
- Structured JSON logging and request IDs

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

The API will be available at:

- OpenAPI docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Useful Commands

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
pytest
ruff check .
ruff format .
```

## Project Layout

```text
app/
  api/v1/          API routers
  core/            settings, logging, middleware, security helpers
  db/              database session and base metadata
  models/          SQLAlchemy models
  repositories/    data access layer
  schemas/         Pydantic request/response schemas
  services/        Redis, cache, and domain services
alembic/           database migrations
tests/             test suite
```
