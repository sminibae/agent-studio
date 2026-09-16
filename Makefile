UV_RUN := uv run --project backend

.PHONY: install db-up db-down migrate dev dev-api dev-web fmt lint typecheck test \
	test-integration test-e2e generate-api check-generated build check

install:
	uv sync --project backend --frozen
	CI=true pnpm --dir frontend install --frozen-lockfile

db-up:
	docker compose up -d --wait postgres

db-down:
	docker compose down

migrate:
	$(UV_RUN) alembic -c backend/alembic.ini upgrade head

dev: db-up migrate
	$(MAKE) -j2 dev-api dev-web

dev-api:
	$(UV_RUN) uvicorn agent_studio.bootstrap.api:app --reload --port 8000

dev-web:
	pnpm --dir frontend dev

fmt:
	$(UV_RUN) ruff format backend
	$(UV_RUN) ruff check --fix backend
	pnpm --dir frontend format

lint:
	$(UV_RUN) ruff format --check backend
	$(UV_RUN) ruff check backend
	pnpm --dir frontend format:check
	pnpm --dir frontend lint

typecheck:
	$(UV_RUN) mypy backend/src backend/tests
	pnpm --dir frontend typecheck

test:
	$(UV_RUN) pytest backend/tests --ignore=backend/tests/integration
	pnpm --dir frontend test

test-integration: db-up migrate
	$(UV_RUN) pytest backend/tests/integration

test-e2e: db-up migrate
	./e2e/smoke.sh

generate-api:
	$(UV_RUN) python backend/scripts/export_openapi.py frontend/openapi.json
	pnpm --dir frontend generate:api

check-generated:
	./scripts/check_openapi.sh

build:
	pnpm --dir frontend build

check: lint typecheck test check-generated build
