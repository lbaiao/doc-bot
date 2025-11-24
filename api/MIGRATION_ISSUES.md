# Migration Issues & Solutions

This document explains the database migration challenges we encountered and how we solved them.

---

## The Problem: Alembic Migration Challenges

### Issue #1: Docker Permission Errors

**Error:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Cause:** Running `docker-compose run` or `docker exec` requires Docker daemon access, which often needs sudo or specific user permissions.

**Impact:** Couldn't generate migration files without sudo, making automation difficult.

### Issue #2: Manual Migration Generation Required

**Error:**
```
relation "users" does not exist
```

**Cause:** 
1. No migration files existed in `app/db/migrations/versions/`
2. Startup script ran `alembic upgrade head` but had nothing to upgrade
3. Tables were never created

**Why migrations weren't generated:**
- Models existed but weren't discovered by Alembic
- `Base.metadata` didn't have model information
- Required manual `alembic revision --autogenerate` step before first run

### Issue #3: Model Discovery Problem

**Cause:** Models weren't imported in `app/db/base.py`

**Original code:**
```python
# app/db/base.py
class Base(DeclarativeBase):
    pass

# No model imports!
```

**Result:** Alembic couldn't find any models to generate migrations from.

### Issue #4: Complex First-Time Setup

**Required steps (with Alembic):**
1. Start Postgres
2. Generate migration: `docker-compose run --rm api alembic revision --autogenerate`
3. Commit migration file to git
4. Build and restart containers
5. Migration runs automatically on startup

**Problem:** Step 2 required Docker permissions and was easy to forget.

---

## Our Solution: Programmatic Initialization

### What We Did

Replace Alembic with SQLAlchemy's built-in `Base.metadata.create_all()`:

**1. Created `app/db/init_db.py`:**
```python
async def init_db():
    """Create all database tables programmatically."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # This creates all tables from Base.metadata
        await conn.run_sync(Base.metadata.create_all)
```

**2. Updated `app/db/base.py`:**
```python
class Base(DeclarativeBase):
    pass

# Import all models so Base.metadata discovers them
from app.db.models.user import User
from app.db.models.document import Document, Page, Chunk, Figure, Table
from app.db.models.embedding import TextEmbedding, ImageEmbedding, TableEmbedding
from app.db.models.chat import Chat, Message, ToolRun
```

**3. Updated `scripts/startup.sh`:**
```bash
# Wait for Postgres
while ! pg_isready -h postgres -U docbot; do sleep 2; done

# Initialize database (instead of alembic upgrade head)
python -m app.db.init_db

# Start server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Why This Works

**Benefits:**
- ✅ **Zero setup**: No migration files to generate
- ✅ **No Docker permissions needed**: Pure Python, no docker commands
- ✅ **Automatic**: Runs on every container start
- ✅ **Idempotent**: Safe to run multiple times (won't fail if tables exist)
- ✅ **Simple**: Just `docker-compose up -d`

**Trade-offs:**
- ❌ **No rollback**: Can't downgrade schema
- ❌ **No history**: No record of schema changes
- ❌ **Manual production migrations**: Need SQL for complex changes

---

## Timeline of Issues

### Attempt 1: Standard Alembic Setup

**What we tried:**
```bash
alembic init app/db/migrations
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

**Result:** ❌ Docker permission errors, complex setup

### Attempt 2: Auto-migrations on Startup

**What we tried:**
- Updated `startup.sh` to run `alembic upgrade head`
- Assumed migration files existed

**Result:** ❌ No migration files → nothing to upgrade → tables not created

### Attempt 3: Generate Migrations in Container

**What we tried:**
```bash
docker-compose run --rm api alembic revision --autogenerate -m "Initial"
```

**Result:** ❌ Docker permission denied errors

### Attempt 4: Fix Model Discovery

**What we tried:**
- Added explicit model imports to `app/db/base.py`
- Attempted to generate migrations again

**Result:** ⚠️ Would work but still requires manual step before first run

### Solution: Programmatic Initialization ✅

**What we did:**
- Created `app/db/init_db.py`
- Use `Base.metadata.create_all()`
- Run on container startup
- No migration files needed

**Result:** ✅ Works perfectly, zero setup required

---

## Technical Deep Dive

### How SQLAlchemy Creates Tables

```python
# When you call Base.metadata.create_all()
# SQLAlchemy does:

1. Inspect Base.metadata for all registered tables
2. For each table:
   - Check if it exists in database
   - If not, generate CREATE TABLE SQL
   - Execute the SQL
3. Create indexes, foreign keys, constraints

# It's idempotent:
# - If table exists: skip
# - If table missing: create
# - Safe to run anytime
```

### How Alembic Migrations Work

```python
# Alembic workflow:

1. Developer runs: alembic revision --autogenerate
   - Compares current DB state to models
   - Generates Python migration file with upgrade/downgrade

2. Migration file committed to git
   - Contains version history
   - upgrade() function: apply changes
   - downgrade() function: revert changes

3. Deployment runs: alembic upgrade head
   - Checks current DB version (alembic_version table)
   - Runs migration files to get to latest
   - Updates version table

# Problems in our case:
# - Step 1 required Docker permissions
# - Step 2 added git noise
# - Step 3 had nothing to run (no migrations generated)
```

### Why Our Solution is Better for This Use Case

**Our needs:**
- Fast iteration in development
- Simple deployment
- Docker-based workflow
- Small team

**Alembic is better for:**
- Large teams
- Complex production environments
- Need for rollbacks
- Strict schema versioning

**Our solution fits our needs perfectly.**

---

## Comparison Table

| Aspect | Alembic | Programmatic |
|--------|---------|--------------|
| **Setup time** | 5-10 minutes | 0 seconds |
| **Manual steps** | Generate migrations | None |
| **Docker permissions** | Required | Not needed |
| **First run** | Need migration files | Works immediately |
| **Schema history** | ✅ Versioned | ❌ No history |
| **Rollback** | ✅ Yes | ❌ No |
| **Production** | ✅ Safe | ⚠️ Manual SQL |
| **Development** | ⚠️ Complex | ✅ Simple |
| **Git noise** | Migration files | Clean |

---

## When to Use Each Approach

### Use Programmatic (Our Choice)

✅ **Perfect for:**
- Development environments
- Prototypes & MVPs
- Docker-based deployments
- Small teams
- Projects with simple schemas
- Frequent schema changes

### Use Alembic

✅ **Better for:**
- Production with multiple environments
- Large teams
- Complex schema migrations (data transformations)
- Need for rollback capability
- Regulatory/compliance requirements
- Schema versioning is critical

---

## Hybrid Approach (Future Option)

You can use both:

```bash
# scripts/startup.sh
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Production: Using Alembic migrations"
    alembic upgrade head
else
    echo "Development: Using programmatic init"
    python -m app.db.init_db
fi
```

**Benefits:**
- Dev/test: Fast, automatic
- Production: Safe, versioned

---

## Lessons Learned

### 1. Simplicity Wins

Sometimes the "right way" (Alembic) is overkill. For our use case, programmatic init is simpler and more reliable.

### 2. Docker Permissions are Annoying

Requiring `sudo` or special permissions breaks automation and CI/CD. Avoid if possible.

### 3. Model Discovery Matters

Whether using Alembic or programmatic, explicitly import models in `app/db/base.py`:

```python
from app.db.models.user import User
from app.db.models.document import Document
# etc...
```

### 4. Idempotency is Key

Any database initialization should be safe to run multiple times:
- Check if tables exist before creating
- Use `IF NOT EXISTS` in SQL
- Handle conflicts gracefully

### 5. Document the "Why"

This document exists because we want future developers to understand our decision, not just see the code.

---

## Migration Path (If Needed Later)

If you need to add Alembic in the future:

### Step 1: Initial Migration from Current Schema

```bash
# Create migrations directory (already exists)
# Generate initial migration from current DB state
docker-compose exec api alembic revision --autogenerate -m "Initial from existing schema"
```

### Step 2: Update Startup Script

```bash
# scripts/startup.sh
if [ "$USE_ALEMBIC" = "true" ]; then
    alembic upgrade head
else
    python -m app.db.init_db
fi
```

### Step 3: Test Both Paths

```bash
# Test programmatic (development)
USE_ALEMBIC=false docker-compose up -d

# Test Alembic (production)
USE_ALEMBIC=true docker-compose up -d
```

---

## Troubleshooting Programmatic Init

### Tables Not Created

**Check:**
```bash
docker-compose logs api | grep "Initializing database"
```

**Should see:**
```
INFO  [app.db.init_db] Initializing database...
INFO  [app.db.init_db] Creating tables: users, documents, ...
✅ Database initialization complete!
```

**If missing:**
```bash
# Manually run
docker-compose exec api python -m app.db.init_db

# Or restart
docker-compose restart api
```

### Models Not Discovered

**Check:** Are models imported in `app/db/base.py`?

```python
# app/db/base.py
from app.db.models.user import User  # Add this
from app.db.models.document import Document  # And this
```

### SQL Errors

**Check logs for specific SQL errors:**
```bash
docker-compose logs api | grep -i "error"
```

Common issues:
- Foreign key violations
- Type mismatches
- Duplicate table names

---

## Conclusion

**Problem:** Alembic migrations were complex and had Docker permission issues.

**Solution:** Programmatic table creation using SQLAlchemy's `create_all()`.

**Result:** Zero-config setup that just works! ✨

**Future:** Can add Alembic later if needed for production environments.

---

## References

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- Our implementation: `app/db/init_db.py`, `scripts/startup.sh`
