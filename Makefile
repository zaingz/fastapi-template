.PHONY: install dev test test-cov lint format typecheck check precommit docker-build docker-run sync lock clean

install:
	uv sync --all-groups
	uv run pre-commit install

dev:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy app/

check: lint typecheck test

precommit:
	uv run pre-commit run --all-files

docker-build:
	docker build -t fastapi-template:dev .

docker-run:
	docker run -p 8000:8000 --env-file .env fastapi-template:dev

sync:
	uv sync

lock:
	uv lock

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info
