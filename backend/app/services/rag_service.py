# backend/app/services/rag_service.py
import os
import json
from typing import Dict, List, Optional, Generator, Tuple
from functools import lru_cache
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
from app.services.embedding_service import get_collection

load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "4000"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.1"))

# Cache embeddings model (singleton pattern)
_embeddings_instance = None
_llm_instance = None

def get_embeddings():
    """Get or create embeddings instance (singleton)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = OllamaEmbeddings(
            model=OLLAMA_EMBED_MODEL,
            base_url=OLLAMA_BASE_URL
        )
    return _embeddings_instance

def get_llm(streaming: bool = False):
    """Get or create LLM instance with optional streaming."""
    global _llm_instance
    if _llm_instance is None or streaming:
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
            keep_alive="5m",
            num_predict=2048,  # Max tokens to generate
            streaming=streaming
        )
    return _llm_instance
def calculate_similarity_score(distance: float, metric: str = "l2") -> float:
    """
    Convert distance to similarity score.
    
    ChromaDB uses SQUARED L2 distance by default.
    Typical ranges:
    - 0-100: Very similar
    - 100-400: Moderately similar  
    - 400+: Not very similar
    
    Args:
        distance: Distance value from ChromaDB (squared L2)
        metric: Distance metric (default: "l2")
    
    Returns:
        Similarity score between 0 and 1
    """
    import math
    
    if distance < 0:
        return 1.0
    
    # For squared L2 distance, we need to normalize differently
    # First, take the square root to get actual L2 distance
    actual_distance = math.sqrt(distance)
    
    # Normalize using inverse exponential with a scaling factor
    # Scale factor of 10 works well for typical embedding distances
    # This maps: 0 → 1.0, 10 → 0.37, 20 → 0.14, 30 → 0.05
    scale_factor = 10.0
    similarity = math.exp(-actual_distance / scale_factor)
    
    return max(0.0, min(1.0, similarity))
    
    # For L2 distance, use exponential decay
    # This maps: distance=0 → 1.0, distance=1 → 0.37, distance=2 → 0.14
    similarity = math.exp(-distance)
    
    return max(0.0, min(1.0, similarity))


def search_similar_code(
    repo_id: int,
    query: str,
    top_k: int = 5,
    score_threshold: float = MIN_RELEVANCE_SCORE,
    rerank: bool = True
) -> List[Dict]:
    """
    Search for similar code chunks with improved error handling.
    """
    try:
        collection = get_collection(repo_id)
        if not collection:
            print(f"❌ No collection found for repository {repo_id}")
            raise Exception(f"No collection found for repository {repo_id}")

        # Check collection size
        collection_count = collection.count()
        print(f"📊 Collection 'repo_{repo_id}' has {collection_count} items")
        
        if collection_count == 0:
            print(f"⚠️ Collection is empty - no embeddings found")
            return []

        embeddings = get_embeddings()
        
        # Ensure query is a string
        query_str = str(query).strip()
        if not query_str:
            print(f"❌ Empty query provided")
            return []
            
        print(f"🔍 Creating embedding for query: '{query_str[:50]}...'")
        query_embedding = embeddings.embed_query(query_str)
        print(f"✅ Query embedding created (dim: {len(query_embedding)})")
        
        # Fetch more results for re-ranking
        fetch_k = min(top_k * 3 if rerank else top_k, collection_count)
        print(f"🔎 Querying collection with n_results={fetch_k}")
        
        # Query with explicit parameters
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"]
        )

        print(f"📦 Query returned {len(results.get('ids', [[]])[0])} results")

        similar_chunks = []
        if results and results.get('ids') and len(results['ids'][0]) > 0:
            print(f"✅ Processing {len(results['ids'][0])} results...")
            
            for i in range(len(results['ids'][0])):
                distance = results['distances'][0][i]
                similarity = calculate_similarity_score(distance)
                
                print(f"  [{i+1}] Distance: {distance:.4f}, Similarity: {similarity:.4f}")
                
                # Apply threshold filter
                if similarity < score_threshold:
                    print(f"  ⏭️ Skipping (below threshold {score_threshold})")
                    continue
                
                metadata = results['metadatas'][0][i]
                content = results['documents'][0][i]
                
                # Re-ranking boost based on file type and query keywords
                boost = 1.0
                if rerank:
                    # Boost if file extension matches common code patterns
                    file_path = metadata.get('file_path', '')
                    if any(ext in file_path for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.html', '.css']):
                        boost *= 1.1
                    
                    # Boost if chunk contains query keywords
                    content_lower = content.lower()
                    query_lower = query_str.lower()
                    keyword_matches = sum(1 for word in query_lower.split() if len(word) > 2 and word in content_lower)
                    boost *= (1 + keyword_matches * 0.05)
                
                boosted_similarity = similarity * boost
                
                similar_chunks.append({
                    "id": results['ids'][0][i],
                    "content": content,
                    "metadata": metadata,
                    "distance": distance,
                    "similarity": boosted_similarity,
                    "original_similarity": similarity
                })
                
                print(f"  ✅ Added chunk (boosted similarity: {boosted_similarity:.4f})")
            
            # Sort by boosted similarity and take top_k
            similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
            similar_chunks = similar_chunks[:top_k]
            
            print(f"🎯 Returning {len(similar_chunks)} chunks after filtering and ranking")
        else:
            print(f"⚠️ No results returned from ChromaDB query")

        return similar_chunks

    except Exception as e:
        print(f"❌ Error searching similar code: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def truncate_context(context: str, max_length: int = MAX_CONTEXT_LENGTH) -> Tuple[str, bool]:
    """
    Truncate context to fit within token limits while preserving code structure.
    
    Returns:
        Tuple of (truncated_context, was_truncated)
    """
    if len(context) <= max_length:
        return context, False
    
    # Try to truncate at a natural boundary (end of code block)
    truncation_point = context.rfind("```", 0, max_length)
    if truncation_point > max_length * 0.7:  # Only if we keep at least 70%
        return context[:truncation_point] + "\n```\n\n...[Context truncated for length]...", True
    
    # Fallback: hard truncate with warning
    return context[:max_length] + "\n\n...[Context truncated for length]...", True

def format_context(chunks: List[Dict], include_similarity: bool = False) -> str:
    """
    Format chunks with improved structure and optional similarity scores.
    """
    files_context = {}
    
    for chunk in chunks:
        meta = chunk['metadata']
        file_path = meta.get('file_path', 'unknown')
        language = meta.get('language', 'text')
        
        if file_path not in files_context:
            files_context[file_path] = {
                "language": language,
                "chunks": [],
                "max_similarity": 0
            }
        
        files_context[file_path]["chunks"].append({
            "content": chunk['content'],
            "similarity": chunk.get('similarity', 0)
        })
        files_context[file_path]["max_similarity"] = max(
            files_context[file_path]["max_similarity"],
            chunk.get('similarity', 0)
        )
    
    # Sort files by relevance
    sorted_files = sorted(
        files_context.items(),
        key=lambda x: x[1]["max_similarity"],
        reverse=True
    )
    
    formatted_parts = []
    for file_path, data in sorted_files:
        # Sort chunks within file by similarity
        sorted_chunks = sorted(data['chunks'], key=lambda x: x['similarity'], reverse=True)
        
        similarity_label = ""
        if include_similarity and data["max_similarity"] > 0:
            similarity_label = f" (Relevance: {data['max_similarity']:.2f})"
        
        file_content = "\n...[skipped code]...\n".join([c['content'] for c in sorted_chunks])
        
        formatted_parts.append(
            f"### File: {file_path}{similarity_label}\n"
            f"```{data['language']}\n"
            f"{file_content}\n"
            f"```"
        )
    
    context = "\n\n".join(formatted_parts)
    truncated_context, was_truncated = truncate_context(context)
    
    return truncated_context

@lru_cache(maxsize=5)
def get_prompt_template(style: str = "senior_dev") -> ChatPromptTemplate:
    """
    Get prompt template with caching support for different styles.
    
    Args:
        style: Prompt style ("senior_dev", "concise", "educational")
    """
    templates = {
        "senior_dev": """You are CodeMind AI, an expert Senior Software Engineer and Mentor with deep expertise in code analysis and documentation.

CONTEXT FROM REPOSITORY:
{context}

CHAT HISTORY:
{chat_history}

USER QUESTION: {question}

INSTRUCTIONS:
1. **Analyze the Big Picture**: Start with a high-level explanation of what the relevant code does and its purpose within the system.

2. **Detailed Technical Breakdown**:
   - Explain the logic, architecture, or patterns used
   - Reference specific functions, classes, or variables using `code blocks`
   - Use **bold** for key concepts
   - Provide code examples when helpful

3. **Evidence & Sources**: Always reference specific file names and line contexts from the provided code.

4. **Best Practices**: If relevant, mention design patterns, potential improvements, or common pitfalls.

5. **Formatting**: Use clear Markdown structure with headers, lists, and code blocks.

If the context doesn't contain information to answer the question, clearly state this and suggest what additional context might be needed.""",

        "concise": """You are CodeMind AI, an expert code analyst providing concise, accurate answers.

CONTEXT: {context}

HISTORY: {chat_history}

QUESTION: {question}

Provide a clear, direct answer using the code context. Be concise but complete. Use code blocks and bold for emphasis. Cite specific files when referencing code.""",

        "educational": """You are CodeMind AI, a patient coding mentor helping developers learn.

CONTEXT: {context}

HISTORY: {chat_history}

QUESTION: {question}

Explain the code in an educational way:
1. **What**: Describe what the code does
2. **Why**: Explain the reasoning behind the approach
3. **How**: Break down the implementation step-by-step
4. **Learn More**: Suggest related concepts to explore

Use simple language, examples, and encourage questions. Always cite the specific files you're referencing."""
    }
    
    template = templates.get(style, templates["senior_dev"])
    return ChatPromptTemplate.from_template(template)

def format_chat_history(chat_history: List[Dict], max_messages: int = 3) -> str:
    """Format chat history with better context management."""
    if not chat_history:
        return "None"
    
    recent_history = chat_history[-max_messages:]
    formatted = []
    
    for msg in recent_history:
        question = msg.get('question', '')
        answer = msg.get('answer', '')
        
        # Truncate long answers
        if len(answer) > 500:
            answer = answer[:497] + "..."
        
        formatted.append(f"User: {question}\nAssistant: {answer}")
    
    return "\n\n".join(formatted)

def query_codebase(
    repo_id: int,
    query: str,
    top_k: int = 5,
    include_sources: bool = True,
    chat_history: List[Dict] = None,
    prompt_style: str = "senior_dev",
    include_metadata: bool = True
) -> Dict:
    """Query the codebase with enhanced features."""
    try:
        print(f"🔍 Searching codebase for: '{query}'")
        
        similar_chunks = search_similar_code(repo_id, query, top_k, rerank=True)
        
        if not similar_chunks:
            return {
                "answer": "I couldn't find any relevant code in the repository to answer your question. Try rephrasing your query or asking about different aspects of the codebase.",
                "sources": [],
                "metadata": {"chunks_found": 0, "avg_similarity": 0}
            }

        context_str = format_context(similar_chunks, include_similarity=False)
        history_str = format_chat_history(chat_history or [])

        print(f"🤖 Generating answer using {OLLAMA_MODEL}...")
        
        prompt_template = get_prompt_template(prompt_style)
        llm = get_llm(streaming=False)
        chain = prompt_template | llm | StrOutputParser()
        
        answer = chain.invoke({
            "context": context_str,
            "chat_history": history_str,
            "question": query
        })

        # Extract sources with proper type conversion
        sources = []
        if include_sources:
            seen_files = set()
            for chunk in similar_chunks:
                file_path = chunk['metadata'].get('file_path')
                if file_path and file_path not in seen_files:
                    # Get lines and ensure it's a string
                    lines_value = chunk['metadata'].get('lines')
                    if lines_value is not None:
                        # Convert to string format
                        if isinstance(lines_value, int):
                            lines_str = str(lines_value)
                        elif isinstance(lines_value, (list, tuple)) and len(lines_value) == 2:
                            lines_str = f"{lines_value[0]}-{lines_value[1]}"
                        else:
                            lines_str = str(lines_value)
                    else:
                        lines_str = None
                    
                    sources.append({
                        "file_path": file_path,
                        "language": chunk['metadata'].get('language', 'unknown'),
                        "relevance_score": round(chunk['similarity'], 3),
                        "lines": lines_str  # Now guaranteed to be string or None
                    })
                    seen_files.add(file_path)
            
            sources.sort(key=lambda x: x['relevance_score'], reverse=True)

        response = {
            "answer": answer,
            "sources": sources
        }
        
        if include_metadata:
            avg_similarity = sum(c['similarity'] for c in similar_chunks) / len(similar_chunks)
            response["metadata"] = {
                "chunks_found": len(similar_chunks),
                "avg_similarity": round(avg_similarity, 3),
                "model": OLLAMA_MODEL,
                "prompt_style": prompt_style
            }
        
        return response

    except Exception as e:
        print(f"❌ Error querying codebase: {str(e)}")
        raise

def query_codebase_stream(
    repo_id: int,
    query: str,
    top_k: int = 5,
    chat_history: List[Dict] = None,
    prompt_style: str = "senior_dev"
) -> Generator[str, None, None]:
    """
    Streaming version with enhanced source formatting.
    """
    try:
        # 1. Retrieve chunks
        similar_chunks = search_similar_code(repo_id, query, top_k, rerank=True)
        
        if not similar_chunks:
            yield "I couldn't find any relevant code in the repository to answer your question."
            return

        # 2. Format context
        context_str = format_context(similar_chunks, include_similarity=False)
        history_str = format_chat_history(chat_history or [])

        # 3. Stream answer
        prompt_template = get_prompt_template(prompt_style)
        llm = get_llm(streaming=True)
        chain = prompt_template | llm | StrOutputParser()

        for chunk in chain.stream({
            "context": context_str,
            "chat_history": history_str,
            "question": query
        }):
            yield chunk

        # 4. Yield sources as JSON for frontend parsing
        sources = []
        seen_files = set()
        for chunk in similar_chunks:
            file_path = chunk['metadata'].get('file_path')
            if file_path and file_path not in seen_files:
                sources.append({
                    "file_path": file_path,
                    "language": chunk['metadata'].get('language'),
                    "relevance_score": round(chunk['similarity'], 3)
                })
                seen_files.add(file_path)
        
        # Signal sources with special marker
        yield f"\n\n[SOURCES]{json.dumps(sources)}[/SOURCES]"

    except Exception as e:
        yield f"\n\n❌ Error: {str(e)}"

# Health check function
def check_service_health() -> Dict:
    """Check if RAG service components are accessible."""
    try:
        embeddings = get_embeddings()
        llm = get_llm()
        
        # Test embedding
        test_embedding = embeddings.embed_query("test")
        
        return {
            "status": "healthy",
            "ollama_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
            "embed_model": OLLAMA_EMBED_MODEL,
            "embedding_dim": len(test_embedding)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }