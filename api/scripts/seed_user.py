"""
Seed a user into the database.

Usage:
    DATABASE_URL=sqlite+aiosqlite:///./seed.db python -m scripts.seed_user
    # override defaults:
    DATABASE_URL=... python -m scripts.seed_user --email you@example.com --password BetterPass123

The script honors settings.DATABASE_URL, creates tables if missing, and skips creation if the email already exists.
"""
import argparse
import asyncio
import uuid
import sys
from pathlib import Path

from fastapi_users.password import PasswordHelper
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ensure the project root is on sys.path when run as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.db.base import Base
from app.db.models.user import User

DEFAULT_EMAIL = "admin@example.com"
DEFAULT_PASSWORD = "changeme123!"


async def seed_user(email: str, password: str, superuser: bool, verified: bool) -> None:
    """Create the user if it doesn't exist."""
    engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    password_helper = PasswordHelper()

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing:
            print(f"User already exists: {email} (id={existing.id})")
            await engine.dispose()
            return

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=password_helper.hash(password),
            is_active=True,
            is_superuser=superuser,
            is_verified=verified,
        )
        session.add(user)
        await session.commit()
        print(f"Seeded user: {email} (id={user.id})")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a user into the database.")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Email for the new user")
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Plaintext password to hash and store",
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=None,
        help="Override DATABASE_URL (otherwise uses settings.DATABASE_URL / env)",
    )
    parser.add_argument(
        "--superuser",
        action="store_true",
        help="Flag the user as a superuser (default: False)",
    )
    parser.add_argument(
        "--verified",
        action="store_true",
        help="Mark the user as verified (default: False)",
    )
    args = parser.parse_args()

    if args.database_url:
        settings.DATABASE_URL = args.database_url

    asyncio.run(seed_user(args.email, args.password, args.superuser, args.verified))


if __name__ == "__main__":
    main()
