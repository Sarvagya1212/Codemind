# backend/debug_search.py
# Run this script to debug what's in your database and ChromaDB

from app.database import SessionLocal
from app.models import CodeFile, Repository
from app.config.chroma import get_chroma_client

def debug_search_data(repo_id: int):
    """Debug search data for a repository"""
    db = SessionLocal()
    chroma_client = get_chroma_client()
    
    print(f"\n{'='*60}")
    print(f"DEBUG: Repository {repo_id}")
    print(f"{'='*60}\n")
    
    # Check repository exists
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        print(f"❌ Repository {repo_id} not found!")
        return
    
    print(f"✅ Repository found: {repo.github_url}")
    print(f"   Status: {repo.status}\n")
    
    # Check CodeFiles in database
    files = db.query(CodeFile).filter(CodeFile.repo_id == repo_id).all()
    print(f"📁 CodeFiles in database: {len(files)}")
    
    if files:
        print(f"   Sample files:")
        for file in files[:5]:
            print(f"   - ID: {file.id}, Path: {file.file_path}, Language: {file.language}")
    else:
        print(f"   ⚠️  No files found in database!")
    print()
    
    # Check ChromaDB collection
    collection_name = f"repo_{repo_id}_chunks"
    try:
        collection = chroma_client.get_collection(name=collection_name)
        count = collection.count()
        print(f"🧠 ChromaDB collection: {collection_name}")
        print(f"   Chunks: {count}")
        
        if count > 0:
            # Get a sample chunk to inspect metadata
            sample = collection.get(limit=1, include=["metadatas", "documents"])
            if sample and sample['ids']:
                print(f"\n   Sample chunk:")
                print(f"   - ID: {sample['ids'][0]}")
                print(f"   - Metadata: {sample['metadatas'][0]}")
                print(f"   - Content preview: {sample['documents'][0][:100]}...")
                
                # Check if file_id exists in metadata
                metadata = sample['metadatas'][0]
                file_id = metadata.get('file_id')
                print(f"\n   🔍 file_id in metadata: {file_id} (type: {type(file_id)})")
                
                if file_id:
                    # Check if this file_id exists in database
                    file = db.query(CodeFile).filter(CodeFile.id == file_id).first()
                    if file:
                        print(f"   ✅ File exists in DB: {file.file_path}")
                    else:
                        print(f"   ❌ File ID {file_id} NOT FOUND in database!")
                else:
                    print(f"   ❌ file_id is missing from metadata!")
                    
                    # Try to find file by path
                    file_path = metadata.get('file_path')
                    if file_path:
                        print(f"   🔍 Trying to find by path: {file_path}")
                        file = db.query(CodeFile).filter(
                            CodeFile.repo_id == repo_id,
                            CodeFile.file_path == file_path
                        ).first()
                        if file:
                            print(f"   ✅ Found file in DB: ID={file.id}")
                        else:
                            print(f"   ❌ File path not found in database!")
        
    except Exception as e:
        print(f"❌ ChromaDB collection not found: {e}")
    
    print(f"\n{'='*60}")
    print(f"DIAGNOSIS:")
    print(f"{'='*60}")
    
    if not files:
        print("❌ PROBLEM: No files in database")
        print("   SOLUTION: Re-run ingestion for this repository")
    elif count == 0:
        print("❌ PROBLEM: No chunks in ChromaDB")
        print("   SOLUTION: Run indexing for this repository")
    else:
        print("✅ Data exists in both database and ChromaDB")
        print("   Next: Check if file_id is properly set in metadata")
    
    print(f"{'='*60}\n")
    
    db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python debug_search.py <repo_id>")
        sys.exit(1)
    
    repo_id = int(sys.argv[1])
    debug_search_data(repo_id)