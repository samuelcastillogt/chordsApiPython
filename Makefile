# Common tasks. Run `make help` to list them.
PYTHON ?= .venv/bin/python
VENV_BIN := .venv/bin

.PHONY: help install dev test lint format check docker

help: ## List available tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Create the virtualenv and install dev dependencies
	python3 -m venv .venv
	$(VENV_BIN)/pip install -r requirements-dev.txt
	@test -f .env || cp .env.example .env

dev: ## Run the API with auto-reload on http://localhost:8000
	$(VENV_BIN)/uvicorn app.main:app --reload --port 8000

test: ## Run the test suite with coverage
	$(VENV_BIN)/pytest --cov=app

lint: ## Lint and check formatting
	$(VENV_BIN)/ruff check .
	$(VENV_BIN)/ruff format --check .

format: ## Fix lint issues and format the code
	$(VENV_BIN)/ruff check --fix .
	$(VENV_BIN)/ruff format .

check: lint test ## Everything CI runs

docker: ## Run the API with Docker Compose
	docker compose up --build
