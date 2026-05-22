.PHONY: help test test-local clean

help:
	@echo "TextRp X Growth Bot - AI STACK Test Commands"
	@echo ""
	@echo "  make test        Run full test suite via Docker (recommended)"
	@echo "  make test-local  Run pytest locally (requires test deps + mocks)"
	@echo "  make clean       Clean pycache and test artifacts"

test:
	# Starts postgres dep if needed (idempotent) + runs isolated test container
	docker compose run --rm test

test-local:
	python -m pytest tests/ -q --tb=short

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov 2>/dev/null || true
