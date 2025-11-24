#!/bin/bash
set -e

echo "🔧 Generating migration..."

# Check if this is the first migration
VERSIONS_DIR="app/db/migrations/versions"
if [ ! "$(ls -A $VERSIONS_DIR)" ]; then
    echo "Creating initial migration..."
    alembic revision --autogenerate -m "Initial schema"
else
    echo "Creating migration for schema changes..."
    alembic revision --autogenerate -m "Schema update"
fi

echo "✅ Migration generated!"
echo ""
echo "Files created in $VERSIONS_DIR/"
ls -lt $VERSIONS_DIR/ | head -5
