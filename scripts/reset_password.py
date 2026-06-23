#!/usr/bin/env python3
"""Reset user password - reads password from stdin to avoid shell escaping issues."""
import sys
import asyncio
from sqlalchemy import select

# Add app to path
sys.path.insert(0, '/app')

from backend.app.database import async_session
from backend.app.models import User
from backend.app.security import hash_password

async def reset_password(username: str, password: str):
    """Reset password for given username."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"ERROR: User '{username}' not found")
            return False
        
        user.hashed_password = hash_password(password)
        await session.commit()
        print(f"SUCCESS: Password updated for user '{username}'")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: reset_password.py <username>")
        print("Password is read from stdin")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.stdin.read().strip()
    
    if not password:
        print("ERROR: No password provided via stdin")
        sys.exit(1)
    
    success = asyncio.run(reset_password(username, password))
    sys.exit(0 if success else 1)