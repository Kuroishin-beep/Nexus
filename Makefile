.PHONY: install dev lint test test-unit test-integration eval docker-up docker-down mcp clean

# ── Setup ─────────────────────────────────────────────────────
install:
	pip install -e ".[dev]"
	pre-commit install

# ── Development ───────────────────────────────────────────────
dev:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

mcp:
	python -m src.mcp.server

# ── Quality ───────────────────────────────────────────────────
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# ── Tests ─────────────────────────────────────────────────────
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v --cov=src --cov-report=term-missing

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

# ── Evals ─────────────────────────────────────────────────────
eval:
	python scripts/run_evals.py --suite all --output eval_results.json --fail-threshold 0.80

eval-agents:
	python scripts/run_evals.py --suite agents

eval-tools:
	python scripts/run_evals.py --suite tools

# ── Docker ────────────────────────────────────────────────────
docker-up:
	docker compose -f infra/docker/docker-compose.yml up -d

docker-down:
	docker compose -f infra/docker/docker-compose.yml down

docker-build:
	docker compose -f infra/docker/docker-compose.yml build

docker-logs:
	docker compose -f infra/docker/docker-compose.yml logs -f api

# ── DB / Vector ───────────────────────────────────────────────
seed:
	python scripts/seed_db.py

# ── Clean ─────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf .coverage coverage.xml .mypy_cache .ruff_cache dist build
