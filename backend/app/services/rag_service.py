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

# Configuration - PHASE 5: LATENCY OPTIMIZATION
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# Faster model for lower latency (3b vs 7b = 2-3x speedup)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
# Hard token limit (production-grade: 8k-12k)
MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "12000"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.1"))
# MMR configuration
USE_MMR = os.getenv("USE_MMR", "true").lower() == "true"
MMR_TOP_K = int(os.getenv("MMR_TOP_K", "6"))  # Compress to 6 chunks max

# PHASE 6: GROUNDING PROTECTION
# Confidence gate - prevents hallucinations on low-quality retrievals
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.15"))  # Lowered for small repos
USE_CONFIDENCE_GATE = os.getenv("USE_CONFIDENCE_GATE", "true").lower() == "true"

# PHASE 7: QUERY EXPANSION
# Expand queries with related terms for better recall
USE_QUERY_EXPANSION = os.getenv("USE_QUERY_EXPANSION", "true").lower() == "true"

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
    """Get or create LLM instance with FAST generation config."""
    global _llm_instance
    if _llm_instance is None or streaming:
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2,
            keep_alive="5m",
            num_predict=1024,  # REDUCED from 2048 for faster generation
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
    rerank: bool = True,
    use_reranker: bool = True  # NEW: Enable cross-encoder reranking
) -> List[Dict]:
    """
    Search for similar code chunks with two-stage retrieval.
    
    Stage 1: Bi-encoder retrieves top candidates (fast, approximate)
    Stage 2: Cross-encoder reranks for precision (slower, more accurate)
    
    Args:
        repo_id: Repository ID
        query: Search query
        top_k: Final number of results to return
        score_threshold: Minimum similarity score
        rerank: Apply keyword-based boosting (legacy)
        use_reranker: Apply cross-encoder reranking (recommended)
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
        
        # STAGE 1: Bi-encoder retrieval - fetch MORE candidates for reranking
        # If using reranker, get 4x candidates; otherwise just top_k
        if use_reranker:
            fetch_k = min(top_k * 4, collection_count, 30)  # Max 30 for perf
        else:
            fetch_k = min(top_k * 3 if rerank else top_k, collection_count)
            
        print(f"🔎 Stage 1: Bi-encoder retrieval (n={fetch_k})")
        
        # Query with explicit parameters
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"]
        )

        print(f"📦 Retrieved {len(results.get('ids', [[]])[0])} candidates")

        similar_chunks = []
        if results and results.get('ids') and len(results['ids'][0]) > 0:
            
            for i in range(len(results['ids'][0])):
                distance = results['distances'][0][i]
                similarity = calculate_similarity_score(distance)
                
                # Apply threshold filter
                if similarity < score_threshold:
                    continue
                
                metadata = results['metadatas'][0][i]
                content = results['documents'][0][i]
                
                # Legacy keyword-based boosting
                boost = 1.0
                if rerank and not use_reranker:
                    file_path = metadata.get('file_path', '')
                    if any(ext in file_path for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.html', '.css']):
                        boost *= 1.1
                    
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
            
            print(f"📋 {len(similar_chunks)} chunks passed threshold filter")
            
            # STAGE 2: Cross-encoder reranking (if enabled)
            if use_reranker and len(similar_chunks) > 0:
                from app.services.reranker_service import rerank_chunks
                
                print(f"🎯 Stage 2: Cross-encoder reranking...")
                similar_chunks = rerank_chunks(
                    query=query_str,
                    chunks=similar_chunks,
                    top_k=top_k,
                    return_scores=True
                )
            else:
                # Fallback: sort by similarity and take top_k
                similar_chunks.sort(key=lambda x: x['similarity'], reverse=True)
                similar_chunks = similar_chunks[:top_k]
            
            print(f"🎯 Returning {len(similar_chunks)} final results")
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

def summarize_file_chunks(chunks: List[Dict], language: str) -> str:
    """
    Extract semantic summary from code chunks (imports, classes, functions).
    This reduces cognitive load on the LLM by providing structured info instead of raw code.
    """
    import re
    
    combined_code = "\n".join([c['content'] for c in chunks])
    summary_items = []
    
    # Extract imports (Python, JS, TS, Java, etc.)
    if language in ['python', 'py']:
        imports = re.findall(r'^(?:from\s+[\w.]+\s+)?import\s+([\w,\s.]+)', combined_code, re.MULTILINE)
        if imports:
            summary_items.append(f"Imports: {', '.join([i.strip() for i in imports[:5]])}")
        
        # Extract class definitions
        classes = re.findall(r'^class\s+(\w+)', combined_code, re.MULTILINE)
        if classes:
            summary_items.append(f"Classes: {', '.join(classes[:5])}")
        
        #Extract function definitions
        functions = re.findall(r'^(?:async\s+)?def\s+(\w+)', combined_code, re.MULTILINE)
        if functions:
            summary_items.append(f"Functions: {', '.join(functions[:8])}")
    
    elif language in ['javascript', 'typescript', 'js', 'ts', 'jsx', 'tsx']:
        # Extract imports
        imports = re.findall(r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]', combined_code)
        if imports:
            summary_items.append(f"Imports: {', '.join(imports[:5])}")
        
        # Extract classes
        classes = re.findall(r'class\s+(\w+)', combined_code)
        if classes:
            summary_items.append(f"Classes: {', '.join(classes[:5])}")
        
        # Extract functions (including arrow functions)
        functions = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\()', combined_code)
        func_names = [f[0] or f[1] for f in functions if f[0] or f[1]]
        if func_names:
            summary_items.append(f"Functions: {', '.join(func_names[:8])}")
    
    elif language in ['java', 'cpp', 'c++', 'c', 'go']:
        # Extract classes/structs
        classes = re.findall(r'(?:class|struct)\s+(\w+)', combined_code)
        if classes:
            summary_items.append(f"Classes/Structs: {', '.join(classes[:5])}")
        
        # Extract function signatures
        functions = re.findall(r'(?:public|private|protected|static)?\s*\w+\s+(\w+)\s*\(', combined_code)
        if functions:
            summary_items.append(f"Functions: {', '.join(functions[:8])}")
    
    # If no structural info found, provide a generic summary
    if not summary_items:
        lines = combined_code.split('\n')
        non_empty = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]
        if non_empty:
            summary_items.append(f"Contains {len(non_empty)} lines of {language} code")
    
    return "\n".join([f"- {item}" for item in summary_items])

def format_context(chunks: List[Dict], include_similarity: bool = False, use_summaries: bool = False) -> str:
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
        
        
        if use_summaries:
            # Use semantic summary instead of raw code
            file_summary = summarize_file_chunks(sorted_chunks, data['language'])
            formatted_parts.append(
                f"### File: {file_path}{similarity_label}\n"
                f"{file_summary}"
            )
        else:
            # Original behavior: show raw code
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
        "senior_dev": """You are a repository analysis assistant.

CONTEXT:
{context}

CHAT HISTORY:
{chat_history}

USER QUESTION: {question}

Follow this process strictly:

1. **Identify Relevant Files**: List the file paths from the context that are relevant to the question.
2. **Extract Evidence**: Quote the exact lines of code that support your answer.
3. **Architectural Interpretation**: Infer the architecture or logic ONLY from the evidence.
4. **Confidence Level**: State your confidence (High/Medium/Low) based on the available context.
5. **Final Answer**: Provide the direct answer to the user's question based on the above steps.

If the evidence is weak, say "architecture not fully inferable" or "context insufficient".
**Never guess.** Ground every statement in the provided code.

Return structured output.""",
    }
    
    # NOTE: Multi-step chain (use_multistep=True) is now the default.
    # This template is only used as a fallback if use_multistep=False.
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
    top_k: int = 8,
    include_sources: bool = True,
    rerank: bool = True,
    chat_history: List[Dict] = None,
    prompt_style: str = "senior_dev",
    include_metadata: bool = True,
    use_hybrid: bool = True,  # Enable hybrid search
    use_summaries: bool = True,  # Use semantic summaries (Priority 2)
    use_multistep: bool = True  # NEW: 3-step chain (Priorities 3-8)
) -> Dict:
    """
    Query the codebase with hybrid search support.
    
    Args:
        use_hybrid: If True, uses BM25 + Dense + RRF fusion (recommended)
                   If False, uses only dense embedding search
    """
    try:
        print(f"🔍 Searching codebase for: '{query}'")
        
        # PHASE 7: QUERY EXPANSION - Boost recall with related terms
        search_query = query
        if USE_QUERY_EXPANSION:
            from app.services.query_expansion_service import expand_and_merge_query
            search_query = expand_and_merge_query(query, max_terms=3)
            if search_query != query:
                print(f"🔎 Expanded query: '{query}' → '{search_query}'")
        
        # Choose search strategy
        if use_hybrid:
            from app.services.hybrid_search_service import hybrid_search
            print(f"   🔀 Using HYBRID search (BM25 + Dense + RRF)")
            similar_chunks = hybrid_search(
                repo_id=repo_id,
                query=search_query,  # Use expanded query
                top_k=top_k,
                use_rerank=rerank
            )
        else:
            print(f"   📘 Using DENSE-only search")
            similar_chunks = search_similar_code(repo_id, search_query, top_k, rerank=rerank)
        
        if not similar_chunks:
            return {
                "answer": "I couldn't find any relevant code in the repository to answer your question. Try rephrasing your query or asking about different aspects of the codebase.",
                "sources": [],
                "metadata": {"chunks_found": 0, "avg_similarity": 0}
            }

        # PHASE 5: MMR COMPRESSION - Remove redundant chunks
        if USE_MMR:
            from app.services.mmr_service import compress_context
            original_count = len(similar_chunks)
            similar_chunks, compression_meta = compress_context(
                chunks=similar_chunks,
                max_tokens=MAX_CONTEXT_LENGTH,
                mmr_top_k=MMR_TOP_K,
                use_mmr=True
            )
            print(f"✂️  Compression: {original_count} → {len(similar_chunks)} chunks ({compression_meta['tokens_used']} tokens)")

        # PHASE 6: CONFIDENCE GATE - Prevent hallucinations
        top_score = max([c.get('similarity', 0) for c in similar_chunks]) if similar_chunks else 0
        
        if USE_CONFIDENCE_GATE and top_score < CONFIDENCE_THRESHOLD:
            print(f"🚫 Confidence gate: top_score={top_score:.3f} < threshold={CONFIDENCE_THRESHOLD}")
            return {
                "answer": f"⚠️ **Insufficient repository context to answer this question.**\n\nThe retrieval confidence score ({top_score:.2f}) is below the threshold ({CONFIDENCE_THRESHOLD}). This means I couldn't find sufficiently relevant code to provide a reliable answer.\n\n**Suggestions:**\n- Rephrase your question with more specific terms\n- Ask about a different aspect of the codebase\n- Ensure the repository has been fully indexed",
                "sources": [],
                "metadata": {
                    "chunks_found": len(similar_chunks),
                    "top_confidence": top_score,
                    "confidence_threshold": CONFIDENCE_THRESHOLD,
                    "blocked_by_confidence_gate": True
                }
            }
        
        print(f"✅ Confidence check passed: top_score={top_score:.3f} >= threshold={CONFIDENCE_THRESHOLD}")

        context_str = format_context(similar_chunks, include_similarity=False, use_summaries=use_summaries)
        history_str = format_chat_history(chat_history or [])

        print(f"🤖 Generating answer using {OLLAMA_MODEL}...")
        
        if use_multistep:
            # NEW: Multi-Step Generation (Priorities 3-8)
            print("   🔗 Using 3-step chain (Evidence -> Reasoning -> Answer)")
            from app.services.multistep_rag import create_multistep_chain
            
            llm = get_llm(streaming=False)
            evidence_chain, reasoning_chain, final_chain = create_multistep_chain(llm)
            
            # Step 1: Extract Evidence
            print("   📋 Step 1: Extracting evidence...")
            evidence = evidence_chain.invoke({
                "context": context_str,
                "question": query
            })
            
            # Step 2: Architectural Reasoning
            print("   🧠 Step 2: Reasoning about architecture...")
            reasoning = reasoning_chain.invoke({
                "evidence": evidence,
                "question": query
            })
            
            # Step 3: Final Structured Answer
            print("   ✍️  Step 3: Formatting final answer...")
            answer = final_chain.invoke({
                "question": query,
                "evidence": evidence,
                "reasoning": reasoning
            })
        else:
            # Original single-shot generation
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
    prompt_style: str = "senior_dev",
    use_summaries: bool = True  # NEW: Use semantic summaries instead of raw code
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

        # 2. Format context (with optional summarization)
        context_str = format_context(similar_chunks, include_similarity=False, use_summaries=use_summaries)
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