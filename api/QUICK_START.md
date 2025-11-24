# 🚀 Quick Start - Zero-Config Database Setup

## The Solution: Programmatic Initialization

**No migrations to generate. No files to manage. Just works!** ✨

```bash
docker-compose up -d
```

Done! Tables are created automatically on startup.

---

## Why Not Alembic?

We tried Alembic but hit issues:
- ❌ Docker permission errors running `alembic revision`
- ❌ Manual step to generate migrations before first run
- ❌ Migration files need git management
- ❌ Complex for simple use cases

**Our solution:** Use SQLAlchemy `Base.metadata.create_all()`
- ✅ Zero manual steps
- ✅ Works on first run
- ✅ No permission issues
- ✅ Idempotent (safe to run multiple times)

---

## How It Works

**On container startup:**
1. Wait for Postgres ✓
2. Run `python -m app.db.init_db` ✓
3. Create all tables from models ✓
4. Start API server ✓

**See:** `scripts/startup.sh` + `app/db/init_db.py`

---

## Usage

### Start Everything
```bash
cd /home/lucas/dev/doc-bot/api
docker-compose up -d
```

### Watch Logs
```bash
docker-compose logs -f api
```

**Expected output:**
```
🚀 Starting application...
⏳ Waiting for Postgres...
✅ Postgres is ready!
🔧 Initializing database...
INFO  [app.db.init_db] Creating tables: users, documents, pages...
✅ Database initialization complete!
🎯 Starting API server...
INFO:     Application startup complete.
```

### Verify
```bash
# Check tables
docker-compose exec postgres psql -U docbot -d docbot -c "\dt"

# Test API
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

---

## Reset Database

```bash
# Full reset (deletes data)
docker-compose down -v
docker-compose up -d

# Or just restart (recreates tables if needed)
docker-compose restart api
```

---

## Troubleshooting

### "relation does not exist"
```bash
# Restart the API
docker-compose restart api

# Or manually initialize
docker-compose exec api python -m app.db.init_db
```

### Tables not created
```bash
# Check logs
docker-compose logs api | grep "Initializing database"

# Verify startup script ran
docker-compose logs api | grep "startup.sh"
```

---

## Schema Changes (Future)

When you modify models:

**Development:**
```bash
docker-compose restart api  # Recreates tables
```

**Production:**
```bash
# Write manual SQL migrations
docker-compose exec postgres psql -U docbot -d docbot -c "
ALTER TABLE documents ADD COLUMN new_field VARCHAR(255);
"
```

**Or add Alembic later** if you need versioned migrations.

---

## Why This Works

### `app/db/init_db.py`
```python
async def init_db():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # Creates all tables from Base.metadata
        await conn.run_sync(Base.metadata.create_all)
```

### `app/db/base.py`
```python
class Base(DeclarativeBase):
    pass

# Import models so Base.metadata discovers them
from app.db.models.user import User
from app.db.models.document import Document, Page, Chunk
# ...etc
```

---

## Comparison

| Feature | Programmatic (Us) | Alembic |
|---------|------------------|---------|
| First run | ✅ Works | ❌ Need to generate migration |
| Setup time | 0 seconds | 5 minutes |
| Docker issues | ✅ None | ❌ Permission errors |
| Git noise | ✅ None | ⚠️ Migration files |
| Rollback | ❌ No | ✅ Yes |
| History | ❌ No | ✅ Yes |

**Perfect for:** Development, prototypes, simple apps
**Use Alembic for:** Complex production deployments

---

## Summary

**Alembic problems:**
- Required manual migration generation
- Docker permission issues
- Complex first-time setup

**Our solution:**
- Automatic table creation on startup
- No manual steps
- Just works!

**Run this:**
```bash
docker-compose up -d
```

Tables are created automatically. No migrations needed! 🎉
