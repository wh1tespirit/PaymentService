.PHONY: up down logs infra test lint

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

logs:
	docker compose logs -f

infra:
	docker compose up -d --wait postgres rabbitmq

test: infra
	uv run pytest

lint:
	uv run ruff check .
