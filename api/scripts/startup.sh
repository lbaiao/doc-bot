#!/bin/bash
set -e

echo "🚀 Starting application..."

# Wait for postgres to be ready
echo "⏳ Waiting for Postgres..."
while ! pg_isready -h postgres -U docbot > /dev/null 2>&1; do
    echo "Postgres not ready yet, waiting..."
    sleep 2
done
echo "✅ Postgres is ready!"

# Initialize database (create tables programmatically)
echo "🔧 Initializing database..."
python -m app.db.init_db
echo "✅ Database initialization complete!"

# Start the application
echo "🎯 Starting API server..."
exec "$@"
