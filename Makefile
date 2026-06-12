.PHONY: install test lint run clean

install:
	pip install --no-cache-dir -e ".[dev]"

test:
	pytest tests/unit/ -v --tb=short \
	  --cov=hvp_mod15_notification_service \
	  --cov-report=term-missing \
	  --cov-fail-under=88

lint:
	ruff check src/ tests/

run:
	uvicorn hvp_mod15_notification_service.main:app \
	  --host 0.0.0.0 --port 8015 --app-dir src --reload

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov coverage.xml .coverage
