"""
Test script for CodeMind AI services
Run this to verify all services are working correctly
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.abspath('.'))

from app.services.github_service import clone_repository, cleanup_repository, get_repo_metadata
from app.services.code_parser import parse_repository_files
from app.services.embedding_service import create_embeddings
from app.services.rag_service import query_codebase


def test_services():
    """Test all services with a small repository"""
    
    # Test repository (small Python project)
    test_repo_url = "https://github.com/psf/requests"
    repo_id = 1  # Test repo ID
    
    print("=" * 60)
    print("🧪 Testing CodeMind AI Services")
    print("=" * 60)
    
    try:
        # Step 1: Test GitHub Service
        print("\n1️⃣  Testing GitHub Service...")
        repo_metadata = get_repo_metadata(test_repo_url)
        print(f"   Metadata: {repo_metadata}")
        
        repo_path = clone_repository(test_repo_url)
        print(f"   ✅ Repository cloned to: {repo_path}")
        
        # Step 2: Test Code Parser
        print("\n2️⃣  Testing Code Parser...")
        parsed_files = parse_repository_files(repo_path)
        print(f"   ✅ Parsed {len(parsed_files)} files")
        
        if parsed_files:
            print(f"   Sample file: {parsed_files[0]['file_path']}")
        
        # Step 3: Test Embedding Service
        print("\n3️⃣  Testing Embedding Service...")
        # Use only first 5 files for testing
        test_files = parsed_files[:5]
        stats = create_embeddings(repo_id, test_files)
        print(f"   ✅ Created embeddings: {stats}")
        
        # Step 4: Test RAG Service
        print("\n4️⃣  Testing RAG Service...")
        test_query = "How does this codebase handle HTTP requests?"
        result = query_codebase(repo_id, test_query, top_k=3)
        
        print(f"   ✅ Query: {test_query}")
        print(f"   Answer: {result['answer'][:200]}...")
        print(f"   Sources: {len(result['sources'])} files")
        
        # Cleanup
        print("\n5️⃣  Cleaning up...")
        cleanup_repository(repo_path)
        print("   ✅ Cleanup complete")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_services()