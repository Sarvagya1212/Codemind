"""
Database migration script for CodeMind AI
Adds File Viewer feature support:
- local_path column to repositories
- repository_files table
"""

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)

def execute_migration(conn, description, sql_command, step_number):
    """
    Execute a single migration step with proper error handling
    """
    print(f"{step_number} {description}")
    try:
        conn.execute(text(sql_command))
        conn.commit()
        print(f"   ✅ {description} - SUCCESS")
        return True
    except Exception as e:
        error_msg = str(e).lower()
        # Check for "already exists" or "does not exist" errors
        if any(phrase in error_msg for phrase in [
            "already exists", 
            "does not exist", 
            "duplicate column",
            "column already exists"
        ]):
            print(f"   ⏭️  {description} - SKIPPED (already done)")
            conn.rollback()  # Important: rollback to clear error state
            return True
        else:
            print(f"   ❌ {description} - FAILED: {e}")
            conn.rollback()  # Rollback to allow next operations
            return False

def migrate():
    """Migrate database schema"""
    print("🔄 Starting database migration...")
    print("=" * 60)
    
    with engine.connect() as conn:
        success_count = 0
        total_steps = 9
        
        try:
            # ============================================
            # EXISTING MIGRATIONS
            # ============================================
            
            print("\n📋 Part 1: Existing Migrations")
            print("-" * 60)
            
            # Step 1: Rename repositories.metadata
            if execute_migration(
                conn,
                "Migrating repositories.metadata -> repo_metadata",
                "ALTER TABLE repositories RENAME COLUMN metadata TO repo_metadata",
                "1️⃣"
            ):
                success_count += 1
            
            # Step 2: Rename code_files.metadata
            if execute_migration(
                conn,
                "Migrating code_files.metadata -> file_metadata",
                "ALTER TABLE code_files RENAME COLUMN metadata TO file_metadata",
                "2️⃣"
            ):
                success_count += 1
            
            # Step 3: Rename chat_messages.metadata
            if execute_migration(
                conn,
                "Migrating chat_messages.metadata -> message_metadata",
                "ALTER TABLE chat_messages RENAME COLUMN metadata TO message_metadata",
                "3️⃣"
            ):
                success_count += 1
            
            # ============================================
            # NEW MIGRATIONS - File Viewer Feature
            # ============================================
            
            print("\n📂 Part 2: File Viewer Feature")
            print("-" * 60)
            
            # Step 4: Add local_path column
            if execute_migration(
                conn,
                "Adding repositories.local_path column",
                "ALTER TABLE repositories ADD COLUMN local_path VARCHAR(1000)",
                "4️⃣"
            ):
                success_count += 1
            
            # Step 5: Create repository_files table
            if execute_migration(
                conn,
                "Creating repository_files table",
                """
                CREATE TABLE repository_files (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                    file_path VARCHAR(2000) NOT NULL,
                    file_name VARCHAR(500) NOT NULL,
                    file_type VARCHAR(50) NOT NULL,
                    is_directory BOOLEAN DEFAULT FALSE,
                    parent_path VARCHAR(2000),
                    size_bytes INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """,
                "5️⃣"
            ):
                success_count += 1
            
            # Step 6: Create index on repo_id
            if execute_migration(
                conn,
                "Creating index: ix_repository_files_repo_id",
                "CREATE INDEX ix_repository_files_repo_id ON repository_files(repo_id)",
                "6️⃣"
            ):
                success_count += 1
            
            # Step 7: Create index on file_path
            if execute_migration(
                conn,
                "Creating index: ix_repository_files_file_path",
                "CREATE INDEX ix_repository_files_file_path ON repository_files(file_path)",
                "7️⃣"
            ):
                success_count += 1
            
            # Step 8: Create index on repo_id in code_files (if not exists)
            if execute_migration(
                conn,
                "Creating index: ix_code_files_repo_id",
                "CREATE INDEX IF NOT EXISTS ix_code_files_repo_id ON code_files(repo_id)",
                "8️⃣"
            ):
                success_count += 1
            
            # Step 9: Create index on repo_id in chat_messages (if not exists)
            if execute_migration(
                conn,
                "Creating index: ix_chat_messages_repo_id",
                "CREATE INDEX IF NOT EXISTS ix_chat_messages_repo_id ON chat_messages(repo_id)",
                "9️⃣"
            ):
                success_count += 1
            
            # ============================================
            # SUMMARY
            # ============================================
            
            print("\n" + "=" * 60)
            print("✅ Database migration completed!")
            print("=" * 60)
            print(f"\n📊 Migration Summary: {success_count}/{total_steps} steps successful")
            print("\n✓ Changes applied:")
            print("  • Renamed metadata columns to avoid conflicts")
            print("  • Added repositories.local_path for file storage")
            print("  • Created repository_files table for file tree")
            print("  • Created necessary indexes for performance")
            print("\n🚀 Your database is ready for the File Viewer feature!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Unexpected error during migration: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n💥 Migration script failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("  1. Check your DATABASE_URL in .env")
        print("  2. Ensure PostgreSQL is running")
        print("  3. Verify you have database permissions")
        print("  4. Check if columns/tables already exist")
        exit(1)
