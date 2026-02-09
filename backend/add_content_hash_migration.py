# backend/add_content_hash_migration.py
"""
Migration script to add content_hash column to code_files table.
Run this once to add the column for incremental indexing support.
"""

from sqlalchemy import text
from app.database import engine

def migrate():
    """Add content_hash column to code_files table."""
    with engine.connect() as conn:
        # Add column if it doesn't exist (PostgreSQL syntax)
        try:
            conn.execute(text("""
                ALTER TABLE code_files 
                ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)
            """))
            conn.commit()
            print("✅ Added 'content_hash' column to code_files table")
        except Exception as e:
            print(f"⚠️  Column may already exist or error: {e}")
        
        # Add index for fast lookups
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_code_files_content_hash 
                ON code_files(content_hash)
            """))
            conn.commit()
            print("✅ Created index on 'content_hash' column")
        except Exception as e:
            print(f"⚠️  Index may already exist or error: {e}")
        
        # Also add updated_at column if missing
        try:
            conn.execute(text("""
                ALTER TABLE code_files 
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE
            """))
            conn.commit()
            print("✅ Added 'updated_at' column to code_files table")
        except Exception as e:
            print(f"⚠️  Column may already exist or error: {e}")

    print("\n🎉 Migration complete!")

if __name__ == "__main__":
    migrate()
