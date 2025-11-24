#!/bin/bash

echo "🔍 Verifying Doc-Bot API Setup..."
echo ""

# Check 1: Migration files exist
echo "1. Checking migration files..."
MIGRATION_COUNT=$(find app/db/migrations/versions/ -name "*.py" -type f 2>/dev/null | wc -l)
if [ "$MIGRATION_COUNT" -gt 0 ]; then
    echo "   ✅ $MIGRATION_COUNT migration file(s) found"
    ls -1 app/db/migrations/versions/*.py 2>/dev/null | head -3
else
    echo "   ❌ No migration files found!"
    echo "      Run: sudo ./create_migrations.sh"
    exit 1
fi

echo ""

# Check 2: Services running
echo "2. Checking services..."
if docker-compose ps | grep -q "Up"; then
    echo "   ✅ Services are running"
    docker-compose ps | grep "Up" | awk '{print "      -", $1, $2}'
else
    echo "   ❌ Services not running!"
    echo "      Run: docker-compose up -d"
    exit 1
fi

echo ""

# Check 3: Database tables
echo "3. Checking database tables..."
TABLES=$(docker-compose exec -T postgres psql -U docbot -d docbot -t -c "\dt" 2>/dev/null | grep -v "^$" | wc -l)
if [ "$TABLES" -gt 5 ]; then
    echo "   ✅ $TABLES tables found in database"
    docker-compose exec -T postgres psql -U docbot -d docbot -t -c "\dt" 2>/dev/null | grep -E "users|documents|chats" | sed 's/^/      /'
else
    echo "   ❌ Not enough tables in database!"
    echo "      Expected: users, documents, pages, chunks, figures, tables, chats, messages, tool_runs"
    echo "      Run: docker-compose restart api"
    exit 1
fi

echo ""

# Check 4: API health
echo "4. Checking API health..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "   ✅ API is responding"
    curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
else
    echo "   ❌ API not responding!"
    echo "      Check logs: docker-compose logs api"
    exit 1
fi

echo ""

# Check 5: Qdrant
echo "5. Checking Qdrant..."
if curl -sf http://localhost:6333/collections > /dev/null 2>&1; then
    echo "   ✅ Qdrant is responding"
    COLLECTIONS=$(curl -s http://localhost:6333/collections | jq -r '.result.collections[].name' 2>/dev/null | wc -l)
    echo "      Collections: $COLLECTIONS"
else
    echo "   ⚠️  Qdrant not responding (will auto-create collections)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Setup verification complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "You can now test the API:"
echo "  curl -X POST http://localhost:8000/v1/auth/register \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\":\"test@test.com\",\"password\":\"test123\"}'"
echo ""
