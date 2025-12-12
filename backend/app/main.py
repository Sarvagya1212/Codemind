# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.database import init_db
from app.routers import repositories_router
from app.routers import files
from app.routers import search
# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title="CodeMind AI API",
    description="RAG-based platform for chatting with GitHub repositories + Full Code Search",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(repositories_router)
app.include_router(files.router)
app.include_router(search.router) 

# Application startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize database tables on application startup.
    """
    print("🚀 Initializing database...")
    init_db()
    print("✅ Database initialized successfully!")
    print(f"📡 Server running on http://{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', '8000')}")


# Application shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on application shutdown.
    """
    print("👋 Shutting down CodeMind AI API...")


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {
        "status": "healthy",
        "message": "CodeMind AI API is running",
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": "CodeMind AI API",
        "description": "RAG-based platform for chatting with GitHub repositories",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }
    
@app.get("/debug/repo/{repo_id}/collection")
async def debug_collection(repo_id: int):
    """Debug endpoint to check collection contents."""
    from app.services.embedding_service import get_collection
    
    try:
        collection = get_collection(repo_id)
        if not collection:
            return {"error": "Collection not found"}
        
        count = collection.count()
        
        # Get a sample
        sample = collection.get(limit=3, include=["documents", "metadatas"])
        
        return {
            "collection_name": f"repo_{repo_id}",
            "total_items": count,
            "sample_items": len(sample.get('ids', [])),
            "sample_data": {
                "ids": sample.get('ids', [])[:3],
                "metadatas": sample.get('metadatas', [])[:3],
                "document_lengths": [len(doc) for doc in sample.get('documents', [])[:3]]
            }
        }
    except Exception as e:
        return {"error": str(e)}
