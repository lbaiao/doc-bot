# 🚀 Quick Start - Automatic Migrations

## ✨ How It Works

Migrations run **automatically** when the API starts! Just run:

```bash
docker-compose up -d
```

That's it! ✅

---

## 🎯 First Time Setup (One-Time Only)

Before first run, generate the initial migration:

```bash
cd /home/lucas/dev/doc-bot/api

# Start postgres
docker-compose up -d postgres
sleep 5

# Generate initial migration
docker-compose run --rm api alembic revision --autogenerate -m "Initial schema"

# Stop
docker-compose down
```

Now you're ready!

---

## 🏃 Normal Usage

```bash
# Start everything (migrations run automatically)
docker-compose up -d

# Check logs
docker-compose logs -f api
```

**You should see:**
```
⏳ Waiting for Postgres...
✅ Postgres is ready!
🔧 Running database migrations...
✅ Migrations complete!
🎯 Starting API server...
```

---

## 🔧 Adding New Models

1. Edit model in `app/db/models/`
2. Generate migration: `docker-compose exec api alembic revision --autogenerate -m "Add feature"`
3. Restart: `docker-compose restart api` (applies automatically)

---

## 📚 Quick Commands

```bash
# Generate migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Apply manually (usually automatic)
docker-compose exec api alembic upgrade head

# Rollback
docker-compose exec api alembic downgrade -1

# Check status
docker-compose exec api alembic current

# Reset database
docker-compose down -v && docker-compose up -d
```

---

## 🐛 Troubleshooting

**"relation does not exist"?**
```bash
docker-compose logs api | grep migration
docker-compose restart api
```

**Database locked?**
```bash
docker-compose restart postgres
```

---

## ✅ Verify It Works

```bash
# Start
docker-compose up -d
sleep 10

# Test
curl http://localhost:8000/health

# Check tables
docker-compose exec postgres psql -U docbot -d docbot -c "\dt"
```

Done! 🎉
