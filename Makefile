.PHONY: install run test lint demo clean

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn urlshortener.main:app --reload

test:
	pytest --cov=urlshortener --cov-report=term-missing

lint:
	ruff check src tests scripts

demo:
	python scripts/run_scenarios.py

clean:
	rm -f data/urlshortener.db data/workflows.json
	rm -f artifacts/demos/*.json
