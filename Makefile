.PHONY: help install dev build test lint clean

help:
	@echo "Available commands:"
	@echo "  install    Install all dependencies"
	@echo "  dev        Start development servers"
	@echo "  build      Build for production"
	@echo "  test       Run tests"
	@echo "  lint       Run linters"
	@echo "  clean      Clean build artifacts"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	docker-compose up

dev-backend:
	cd backend && uvicorn app.main:app --reload

dev-frontend:
	cd frontend && npm start

build:
	cd frontend && npm run build
	docker-compose build

test:
	cd backend && pytest
	cd frontend && npm test

lint:
	cd backend && ruff check . && black --check .
	cd frontend && npm run lint

format:
	cd backend && black .
	cd frontend && npm run format

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf frontend/build
	rm -rf .pytest_cache