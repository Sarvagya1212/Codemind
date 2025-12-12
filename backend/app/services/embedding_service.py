# backend/app/services/embedding_service.py
import os
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import OllamaEmbeddings
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

# Configuration
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIR,
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

# Initialize Ollama embeddings
embeddings = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_BASE_URL
)


def initialize_chroma_collection(repo_id: int, reset: bool = False):
    """
    Initialize or get a ChromaDB collection for a repository.
    
    Args:
        repo_id: Repository ID
        reset: Whether to reset the collection if it exists
        
    Returns:
        ChromaDB collection object
    """
    collection_name = f"repo_{repo_id}"
    
    try:
        if reset:
            try:
                chroma_client.delete_collection(name=collection_name)
                print(f"🗑️  Deleted existing collection: {collection_name}")
            except:
                pass
        
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"repo_id": str(repo_id)}
        )
        
        print(f"✅ Initialized ChromaDB collection: {collection_name}")
        return collection
        
    except Exception as e:
        print(f"❌ Error initializing collection: {str(e)}")
        raise


def create_embeddings(
    repo_id: int,
    parsed_files: List[Dict],
    chunk_size: int = 1000,
    overlap: int = 200
) -> Dict:
    """
    Create embeddings for parsed code files and store in ChromaDB.
    
    Args:
        repo_id: Repository ID
        parsed_files: List of parsed file dictionaries
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
        
    Returns:
        Dictionary with embedding statistics
    """
    try:
        # Initialize collection
        collection = initialize_chroma_collection(repo_id, reset=True)
        
        total_chunks = 0
        total_files = len(parsed_files)
        
        print(f"🔄 Creating embeddings for {total_files} files...")
        
        for idx, file_info in enumerate(parsed_files):
            file_path = file_info['file_path']
            content = file_info['content']
            language = file_info['language']
            
            # Chunk the content
            chunks = chunk_code_content(content, chunk_size, overlap)
            
            # Prepare data for ChromaDB
            chunk_ids = []
            chunk_texts = []
            chunk_metadatas = []
            
            for chunk_idx, chunk in enumerate(chunks):
                chunk_id = f"{repo_id}_{idx}_{chunk_idx}"
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk)
                chunk_metadatas.append({
                    "repo_id": repo_id,
                    "file_id": file_info.get('file_id', 0),  # GET FILE ID
                    "file_path": file_path,
                    "language": language,
                    "chunk_index": chunk_idx,
                    "start_line": 1,  # You might want to calculate this
                    "end_line": len(chunk.split('\n')),
                    "file_size": file_info['metadata']['size'],
                    "lines": file_info['metadata']['lines']
                })
            
            # Create embeddings using Ollama
            print(f"📝 Processing ({idx+1}/{total_files}): {file_path} ({len(chunks)} chunks)")
            
            chunk_embeddings = embeddings.embed_documents(chunk_texts)
            
            # Add to ChromaDB
            collection.add(
                ids=chunk_ids,
                embeddings=chunk_embeddings,
                documents=chunk_texts,
                metadatas=chunk_metadatas
            )
            
            total_chunks += len(chunks)
            print(f"✅ [{idx + 1}/{total_files}] Embedded: {file_path}")
        
        print(f"\n🔍 Verifying embeddings in collection...")
        collection = get_collection(repo_id)
        count = collection.count()
        print(f"✅ Collection has {count} items stored")

        if count == 0:
            print(f"❌ WARNING: Collection is empty despite successful embedding!")
        
        stats = {
            "total_files": total_files,
            "total_chunks": total_chunks,
            "collection_name": f"repo_{repo_id}",
            "embedding_model": OLLAMA_EMBED_MODEL
        }
        
        print(f"\n🎉 Embedding complete!")
        print(f"   Files processed: {total_files}")
        print(f"   Total chunks: {total_chunks}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Error creating embeddings: {str(e)}")
        raise


def chunk_code_content(content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split code content into overlapping chunks.
    
    Args:
        content: Code content
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    start = 0
    
    while start < len(content):
        end = start + chunk_size
        chunk = content[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    
    return chunks


def get_collection(repo_id: int):
    """
    Get ChromaDB collection for a repository.
    
    Args:
        repo_id: Repository ID
        
    Returns:
        ChromaDB collection or None if not found
    """
    try:
        collection_name = f"repo_{repo_id}"
        return chroma_client.get_collection(name=collection_name)
    except Exception as e:
        print(f"⚠️  Collection not found for repo {repo_id}: {str(e)}")
        return None