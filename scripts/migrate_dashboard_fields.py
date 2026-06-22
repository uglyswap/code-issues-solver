"""
Migration script for dashboard fields.
Adds new columns to tickets table and creates sessions table.
"""
import asyncio
import sys
sys.path.insert(0, '/app/backend')

from sqlalchemy import text
from app.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Add new columns to tickets table
        print("Adding dashboard fields to tickets table...")
        
        columns_to_add = [
            ("resolution_summary", "JSON"),
            ("attempts_log", "JSON DEFAULT '[]'::json"),
            ("resolution_time_seconds", "FLOAT"),
            ("files_changed", "JSON DEFAULT '[]'::json"),
            ("test_results_before", "JSON"),
            ("test_results_after", "JSON"),
            ("screenshots_before", "JSON DEFAULT '[]'::json"),
            ("screenshots_after", "JSON DEFAULT '[]'::json"),
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                await conn.execute(text(f"""
                    ALTER TABLE tickets 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """))
                print(f"  ✓ Added column: {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  - Column {col_name} already exists")
                else:
                    print(f"  ✗ Error adding {col_name}: {e}")
        
        # Create sessions table
        print("\nCreating sessions table...")
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    trigger_type VARCHAR(50) NOT NULL DEFAULT 'manual',
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    total_tickets_found INTEGER DEFAULT 0,
                    total_tickets_resolved INTEGER DEFAULT 0,
                    total_tickets_failed INTEGER DEFAULT 0,
                    current_ticket_id INTEGER,
                    logs JSON DEFAULT '[]'::json,
                    auto_close_github_issues BOOLEAN DEFAULT TRUE,
                    max_concurrent_tickets INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """))
            print("  ✓ Created sessions table")
            
            # Create indexes
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)
            """))
            print("  ✓ Created indexes")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  - Sessions table already exists")
            else:
                print(f"  ✗ Error creating sessions table: {e}")
        
        print("\n✅ Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
