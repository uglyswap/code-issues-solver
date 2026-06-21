#!/usr/bin/env python3
"""
Database migration script to add bug_patterns and successful_patches tables.

Run this script once to create the new tables.

Usage:
    python scripts/migrate_knowledge_base.py
"""
import asyncio
import sys

sys.path.insert(0, '/app')

from backend.app.database import engine, Base
from backend.app.models import BugPattern, SuccessfulPatch


async def migrate():
    """Create the new tables."""
    print("Creating bug_patterns table...")
    async with engine.begin() as conn:
        await conn.run_sync(BugPattern.__table__.create)
    
    print("Creating successful_patches table...")
    async with engine.begin() as conn:
        await conn.run_sync(SuccessfulPatch.__table__.create)
    
    print("✅ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
