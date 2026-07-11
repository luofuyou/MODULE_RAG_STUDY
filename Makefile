.PHONY: install install-dev test test-unit test-integration test-e2e lint format typecheck clean run-mcp run-dashboard

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v -m "not requires_llm"

test-cov:
	pytest tests/ -v --cov=knowledge_hub --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf src/knowledge_hub.egg-info build/ dist/
	rm -rf htmlcov/ .coverage coverage.xml

run-mcp:
	python -m knowledge_hub.main

run-dashboard:
	streamlit run src/knowledge_hub/dashboard/app.py

all: format lint typecheck test
