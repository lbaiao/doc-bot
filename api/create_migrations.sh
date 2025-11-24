#!/bin/bash
set -e

echo "🔧 Creating initial database migration..."
echo ""

# Make sure postgres is running
if ! docker-compose ps postgres | grep -q "Up"; then
    echo "Starting postgres..."
    docker-compose up -d postgres
    echo "Waiting for postgres to be ready..."
    sleep 5
fi

# Generate migration
echo "Generating migration file..."
docker-compose run --rm api alembic revision --autogenerate -m "Initial schema"

# Check if migration was created
MIGRATION_COUNT=$(find app/db/migrations/versions/ -name "*.py" -type f | wc -l)

if [ "$MIGRATION_COUNT" -gt 0 ]; then
    echo ""
    echo "✅ Migration created successfully!"
    echo ""
    echo "Migration files:"
    ls -lh app/db/migrations/versions/*.py
    echo ""
    echo "Now restart the API to apply migrations:"
    echo "  docker-compose restart api"
    echo ""
    echo "Or rebuild and restart everything:"
    echo "  docker-compose up --build -d"
else
    echo ""
    echo "❌ No migration file was created!"
    echo ""
    echo "This could mean:"
    echo "  1. Models are not being discovered by Alembic"
    echo "  2. Database already has all tables"
    echo "  3. There's an import error in the models"
    echo ""
    echo "Check the output above for errors."
    exit 1
fi
