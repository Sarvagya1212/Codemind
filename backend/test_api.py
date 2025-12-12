"""
Test script for CodeMind AI API endpoints
Run this to test all API endpoints
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health check endpoint"""
    print("\n1️⃣  Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200


def test_ingest_repository():
    """Test repository ingestion"""
    print("\n2️⃣  Testing Repository Ingestion...")
    
    payload = {
        "github_url": "https://github.com/psf/requests"
    }
    
    response = requests.post(f"{BASE_URL}/repos/ingest", json=payload)
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Response: {json.dumps(data, indent=2)}")
    
    assert response.status_code == 202
    return data["id"]


def test_get_repository_status(repo_id):
    """Test getting repository status"""
    print(f"\n3️⃣  Testing Get Repository Status (ID: {repo_id})...")
    
    max_attempts = 60  # Wait up to 5 minutes
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(f"{BASE_URL}/repos/{repo_id}")
        data = response.json()
        status = data["status"]
        
        print(f"   Attempt {attempt + 1}: Status = {status}")
        
        if status == "completed":
            print(f"   ✅ Repository ready!")
            print(f"   Response: {json.dumps(data, indent=2)}")
            return True
        elif status == "failed":
            print(f"   ❌ Repository ingestion failed!")
            print(f"   Error: {data.get('repo_metadata', {}).get('error', 'Unknown error')}")
            return False
        
        time.sleep(5)  # Wait 5 seconds before checking again
        attempt += 1
    
    print(f"   ⚠️  Timeout waiting for repository to complete")
    return False


def test_chat_with_repository(repo_id):
    """Test chatting with repository"""
    print(f"\n4️⃣  Testing Chat with Repository (ID: {repo_id})...")
    
    payload = {
        "question": "What is this repository about? Give me a brief overview."
    }
    
    response = requests.post(f"{BASE_URL}/repos/{repo_id}/chat", json=payload)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Question: {data['question']}")
        print(f"   Answer: {data['answer'][:200]}...")
        print(f"   Sources: {len(data['sources'])} files")
        for src in data['sources'][:3]:
            print(f"      - {src['file_path']} ({src['language']})")
        return data["id"]
    else:
        print(f"   Error: {response.json()}")
        return None


def test_chat_history(repo_id):
    """Test getting chat history"""
    print(f"\n5️⃣  Testing Chat History (ID: {repo_id})...")
    
    response = requests.get(f"{BASE_URL}/repos/{repo_id}/history")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Total messages: {len(data)}")
        if data:
            print(f"   Latest message:")
            print(f"      Q: {data[0]['question']}")
            print(f"      A: {data[0]['answer'][:100]}...")


def test_list_repositories():
    """Test listing all repositories"""
    print("\n6️⃣  Testing List Repositories...")
    
    response = requests.get(f"{BASE_URL}/repos/")
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   Total repositories: {len(data)}")
        for repo in data:
            print(f"      - ID: {repo['id']}, URL: {repo['github_url']}, Status: {repo['status']}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Testing CodeMind AI API Endpoints")
    print("=" * 60)
    
    try:
        # Test 1: Health check
        test_health()
        
        # Test 2: Ingest repository
        repo_id = test_ingest_repository()
        
        # Test 3: Check repository status (wait for completion)
        if not test_get_repository_status(repo_id):
            print("\n❌ Repository ingestion failed or timed out. Stopping tests.")
            return
        
        # Test 4: Chat with repository
        chat_id = test_chat_with_repository(repo_id)
        
        # Test 5: Get chat history
        if chat_id:
            test_chat_history(repo_id)
        
        # Test 6: List all repositories
        test_list_repositories()
        
        print("\n" + "=" * 60)
        print("✅ All API tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()