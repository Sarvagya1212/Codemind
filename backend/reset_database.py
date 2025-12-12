"""
Reset database script - drops all tables and recreates them
WARNING: This will delete ALL data!
"""
import sys
from app.database import engine, Base
from app.models import Repository, CodeFile, ChatMessage

def reset_database():
    """Drop all tables and recreate them"""
    
    print("⚠️  WARNING: This will delete ALL data in the database!")
    confirm = input("Are you sure you want to continue? (yes/no): ")
    
    if confirm.lower() != "yes":
        print("❌ Operation cancelled")
        return
    
    try:
        print("\n🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped")
        
        print("\n🔨 Creating tables with new schema...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        
        print("\n✅ Database reset complete!")
        print("   Tables created:")
        print("   - repositories (with repo_metadata)")
        print("   - code_files (with file_metadata)")
        print("   - chat_messages (with message_metadata)")
        
    except Exception as e:
        print(f"\n❌ Error resetting database: {str(e)}")
        raise

if __name__ == "__main__":
    reset_database()