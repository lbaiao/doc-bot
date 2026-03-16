# Database Migration Guide

This guide explains how to manage database schema changes using Alembic and Docker in the Doc-Bot project.

## Prerequisites

Ensure that your Docker environment is running:

```bash
docker-compose up -d postgres
```

## Creating a Migration

When you modify SQLAlchemy models (e.g., adding a column to `app/db/models/`), you need to generate a migration script.

### 1. Make Model Changes
Modify your Python model files in `api/app/db/models/`.

### 2. Generate Migration Script
Run the following command to auto-generate a migration based on your changes:

```bash
# syntax: docker-compose run --rm api alembic revision --autogenerate -m "Message"
docker-compose run --rm api alembic revision --autogenerate -m "Add document_id to chats"
```

This will create a new python file in `api/app/db/migrations/versions/`.

### 3. Review the Migration
Always verify the generated file to ensure it captures exactly what you intended and nothing else.

## Applying Migrations

To apply the pending migrations to the database:

### Option 1: Restart API Container
The API container is configured to automatically apply migrations on startup.

```bash
docker-compose restart api
```

### Option 2: Manual Apply
You can apply migrations without restarting the container:

```bash
docker-compose run --rm api alembic upgrade head
```

## Rolling Back

To undo the last migration:

```bash
docker-compose run --rm api alembic downgrade -1
```

## Troubleshooting

### Migration not detecting changes?
- Ensure your model is imported in `app/db/base.py` or `app/db/models/__init__.py` so Alembic can "see" it.
- Check that `api/app/db/base.py` imports all your models.

### "Target database is not up to date"
This means there are pending migrations. Run `alembic upgrade head`.
