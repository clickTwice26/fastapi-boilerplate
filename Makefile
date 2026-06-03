# Makefile — FastAPI Boilerplate
# Professionally organised targets for development, testing, CI and Docker

.DEFAULT_GOAL := help

# --- Configurable variables (override via environment or command line) ---
PROJECT_NAME ?= fastapi-boilerplate
APP_MODULE ?= app.main:app
HOST ?= 0.0.0.0
PORT ?= 8000
WORKERS ?= 1

PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
ALEMBIC := $(VENV)/bin/alembic
GUNICORN := $(VENV)/bin/gunicorn

REQUIREMENTS := requirements.txt
DOCKER_IMAGE ?= $(PROJECT_NAME)
COMPOSE_FILE ?= docker-compose.yml

# Detect whether poetry is available and what to prefer
POETRY := $(shell command -v poetry 2>/dev/null || true)

# --- Helper targets and documentation ---
.PHONY: help
help: ## Show this help text
	@echo "Usage: make <target> [VARIABLE=value]"
	@echo ""
	@echo "Common targets:"
	@grep -E '^[a-zA-Z0-9._-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## ";} {printf "  %-20s %s\n", $$1, $$2}'

.PHONY: env
env: ## Print key environment variables used by this Makefile
	@echo "PYTHON: $(PYTHON)"
	@echo "VENV: $(VENV)"
	@echo "APP_MODULE: $(APP_MODULE)"
	@echo "HOST: $(HOST)"
	@echo "PORT: $(PORT)"
	@echo "DOCKER_IMAGE: $(DOCKER_IMAGE)"

# --- Virtual environment and installation ---
.PHONY: venv
venv: ## Create virtualenv at $(VENV) and upgrade pip/setuptools
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip setuptools wheel

.PHONY: install
install: venv ## Install runtime dependencies. Prefers Poetry if present, fallback to pip on failure.
	@if [ "$(USE_POETRY)" = "1" ] && [ -n "$(POETRY)" ] && [ -f pyproject.toml ]; then \
		$(POETRY) install || { echo "Poetry install failed — falling back to pip install"; $(PIP) install -r $(REQUIREMENTS); }; \
	else \
		$(PIP) install -r $(REQUIREMENTS); \
	fi

.PHONY: install-dev
install-dev: venv ## Install developer dependencies (Poetry or fallback)
	@if [ "$(USE_POETRY)" = "1" ] && [ -n "$(POETRY)" ] && [ -f pyproject.toml ]; then \
		$(POETRY) install --with dev || { echo "Poetry dev install failed — falling back to pip install"; $(PIP) install -r $(REQUIREMENTS); $(PIP) install pytest black isort flake8 mypy pre-commit ruff || true; }; \
	elif [ -f requirements-dev.txt ]; then \
		$(PIP) install -r requirements-dev.txt; \
	else \
		$(PIP) install pytest black isort flake8 mypy pre-commit ruff; \
	fi

# --- Run / serve ---
.PHONY: run
run: venv ## Launch development server with Uvicorn (auto-reload)
	$(UVICORN) $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

.PHONY: serve
serve: venv ## Launch production-style server using Gunicorn + Uvicorn workers
	$(GUNICORN) -k uvicorn.workers.UvicornWorker -w $(WORKERS) -b $(HOST):$(PORT) $(APP_MODULE)

# --- Docker & compose ---
.PHONY: docker-build
docker-build: ## Build Docker image (tags as $(DOCKER_IMAGE):latest)
	docker build -t $(DOCKER_IMAGE):latest .

.PHONY: compose-up
compose-up: ## Start docker-compose services (detached)
	docker-compose -f $(COMPOSE_FILE) up --build -d

.PHONY: compose-down
compose-down: ## Stop and remove docker-compose services and volumes
	docker-compose -f $(COMPOSE_FILE) down --volumes --remove-orphans

.PHONY: compose-logs
compose-logs: ## Tail docker-compose logs
	docker-compose -f $(COMPOSE_FILE) logs -f

# --- Formatting, linting, type-checking ---
.PHONY: fmt
fmt: venv ## Format project source using isort and black
	$(PIP) install isort black || true
	$(VENV)/bin/isort .
	$(VENV)/bin/black .

.PHONY: check-format
check-format: venv ## Check formatting (isort/black)
	$(PIP) install isort black || true
	$(VENV)/bin/isort --check-only .
	$(VENV)/bin/black --check .

.PHONY: lint
lint: venv ## Run linters (flake8 + ruff if installed)
	$(PIP) install flake8 ruff || true
	$(VENV)/bin/ruff || true
	$(VENV)/bin/flake8 || true

.PHONY: mypy
mypy: venv ## Run mypy static type checks
	$(PIP) install mypy || true
	$(VENV)/bin/mypy app tests || true

# --- Tests & coverage ---
.PHONY: test
test: install ## Run tests with pytest (ensure project deps are installed)
	PYTHONPATH=$(shell pwd) $(VENV)/bin/pytest -q

.PHONY: coverage
coverage: install ## Run tests and show coverage report (ensure deps installed)
	PYTHONPATH=$(shell pwd) $(VENV)/bin/pytest --cov=app --cov-report=term-missing

# --- Database migrations (Alembic) ---
.PHONY: migrate
migrate: venv ## Apply database migrations (alembic upgrade head)
	$(PIP) install alembic || true
	$(ALEMBIC) upgrade head

.PHONY: revision
revision: venv ## Create an Alembic revision. Usage: make revision MSG="message"
	@test -n "$(MSG)" || (echo "Usage: make revision MSG=\"describe change\""; exit 1)
	$(PIP) install alembic || true
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

.PHONY: downgrade
downgrade: venv ## Downgrade Alembic to REV. Usage: make downgrade REV=<revision>
	@test -n "$(REV)" || (echo "Usage: make downgrade REV=<revision>"; exit 1)
	$(PIP) install alembic || true
	$(ALEMBIC) downgrade $(REV)

# --- Packaging / build ---
.PHONY: build
build: venv ## Build source and wheel distributions
	$(PIP) install build || true
	$(PY) -m build

# --- CI convenience target ---
.PHONY: ci
ci: venv check-format lint mypy test ## Run a set of checks useful for CI
	@echo "CI checks finished"

# --- Utility tasks ---
.PHONY: precommit-install
precommit-install: venv ## Install pre-commit hooks
	$(PIP) install pre-commit || true
	$(VENV)/bin/pre-commit install || true

.PHONY: outdated
outdated: venv ## List outdated pip packages (local venv)
	$(PIP) list --outdated

.PHONY: clean
clean: ## Remove common Python build artifacts and caches
	@echo "Cleaning build artifacts and caches..."
	@find . -type d -name "__pycache__" -print -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -print -exec rm -rf {} +
	@rm -rf .mypy_cache .coverage build dist *.egg-info

## End of Makefile
