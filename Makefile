# EVAL_URL: adres API (domyślnie compose na :8000)
EVAL_URL ?= http://localhost:8000

.PHONY: eval test lint

eval:
	cd api && uv run python -m app.eval --url $(EVAL_URL)

test:
	cd api && uv run pytest -q

lint:
	cd api && uv run ruff check . && uv run ruff format --check .
