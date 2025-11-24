#!/usr/bin/env bash
set -euo pipefail

# Development helper script

case "${1:-}" in
  start)
    echo "Starting development server..."
    uvicorn app.main:app --reload --port 8000
    ;;
  
  migrate)
    echo "Running database migrations..."
    alembic upgrade head
    ;;
  
  migration)
    if [ -z "${2:-}" ]; then
      echo "Usage: $0 migration <message>"
      exit 1
    fi
    echo "Creating migration: $2"
    alembic revision --autogenerate -m "$2"
    ;;
  
  test)
    echo "Running tests..."
    pytest tests/ -v
    ;;
  
  worker)
    echo "Starting Celery worker..."
    celery -A app.workers.celery_app worker --loglevel=info
    ;;
  
  generate-client)
    echo "Generating TypeScript client..."
    ./scripts/generate_ts_client.sh "${2:-http://localhost:8000/openapi.json}"
    ;;
  
  docker-up)
    echo "Starting Docker services..."
    docker-compose up -d
    ;;
  
  docker-down)
    echo "Stopping Docker services..."
    docker-compose down
    ;;
  
  *)
    echo "Usage: $0 {start|migrate|migration|test|worker|generate-client|docker-up|docker-down}"
    echo ""
    echo "Commands:"
    echo "  start            - Start development server"
    echo "  migrate          - Run database migrations"
    echo "  migration <msg>  - Create new migration"
    echo "  test             - Run tests"
    echo "  worker           - Start Celery worker"
    echo "  generate-client  - Generate TypeScript client"
    echo "  docker-up        - Start Docker services"
    echo "  docker-down      - Stop Docker services"
    exit 1
    ;;
esac
