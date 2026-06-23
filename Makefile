.PHONY: install dev backend workers ui test lint migrate seed docker-up docker-down

install:
	pip install -r requirements-dev.txt
	cd ui && npm install

dev:
	docker-compose up postgres redis -d
	@echo "Waiting for postgres..."
	@sleep 3
	cd backend && alembic upgrade head

backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

workers:
	cd workers && dramatiq app.tasks -p 2 --watch .

ui:
	cd ui && npm run dev

test:
	pytest tests/ --cov=backend --cov=workers --cov=browser --cov=agents --cov=integrations --cov-report=term-missing --cov-fail-under=80

test-e2e:
	cd tests/e2e && npx playwright test

lint:
	ruff check backend/ workers/ browser/ agents/ integrations/
	black --check backend/ workers/ browser/ agents/ integrations/
	cd ui && npm run lint

migrate:
	cd backend && alembic revision --autogenerate -m "$(m)"
	cd backend && alembic upgrade head

seed:
	python backend/app/seed.py

docker-up:
	docker-compose up -d --build

docker-down:
	docker-compose down -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
