
# Deployment

```mermaid
flowchart LR
	Dev["Local Dev"]
	Compose["Docker Compose (Postgres + Redis)"]
	Image["Docker Image"]
	Prod["Production (k8s / VM)"]
	Gunicorn["Gunicorn + Uvicorn workers"]
	Dev --> Compose
	Compose --> Image
	Image --> Prod
	Prod --> Gunicorn
```

Docker Compose (recommended for local and staging)

```bash
docker compose up --build -d
```

Build and push image

```bash
docker build -t myorg/fastapi-boilerplate:latest .
docker push myorg/fastapi-boilerplate:latest
```

Production server

- Use `gunicorn` with Uvicorn workers (the Makefile `serve` target does this):

```bash
make serve
```

Environment variables

- Configure via `.env` in CI/CD or environment variables directly. See `app/core/config.py` for names and defaults.

Database migrations

```bash
alembic upgrade head
```
