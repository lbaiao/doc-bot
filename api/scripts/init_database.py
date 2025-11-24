#!/usr/bin/env python
"""
Standalone script to initialize the database.
Can be run manually or imported.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.init_db import init_db


if __name__ == "__main__":
    print("🔧 Initializing database tables...")
    asyncio.run(init_db())
    print("✅ Done!")
