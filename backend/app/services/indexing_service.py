# backend/app/services/indexing_service.py
import asyncio
import hashlib
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import Repository, CodeFile, CodeChunk, Symbol, IndexJob
from app.services.github_service import clone_repository, cleanup_repository
from app.services.code_parser import parse_repository_files
from app.services.ast_chunker import ast_chunker
from app.services.symbol_extractor import symbol_extractor
from app.services.embedding_service import embeddings, chroma_client
from app.config.search_config import search_config

# ============================================
# TESTING FLAGS
# ============================================
TESTING_MODE = False
#MAX_FILES_FOR_TESTING = 10
SKIP_EMBEDDINGS = False

# ============================================
# TIMEOUT HELPER
# ============================================
class TimeoutException(Exception):
    pass

def run_with_timeout(func, args=(), kwargs=None, timeout_duration=10):
    """Run function with timeout using threading (Windows compatible)"""
    if kwargs is None:
        kwargs = {}
    
    result = [None]
    exception = [None]
    
    def wrapper():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout_duration)
    
    if thread.is_alive():
        raise TimeoutException(f"Operation timed out after {timeout_duration}s")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


class IndexingService:
    """
    Manages code indexing pipeline.
    Clean implementation with timeout detection for debugging.
    """
    
    def __init__(self):
        self.active_jobs = {}
    
    async def start_indexing(
        self,
        repo_id: int,
        branch: str,
        force: bool,
        incremental: bool,
        db: Session
    ) -> int:
        """Start an indexing job and return job ID"""
        job = IndexJob(
            repo_id=repo_id,
            branch=branch,
            job_type="incremental" if incremental else "full",
            status="pending"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Start background task
        asyncio.create_task(
            self._process_indexing(job.id, repo_id, branch, force, incremental, db)
        )
        
        return job.id
    
    async def _process_indexing(
        self,
        job_id: int,
        repo_id: int,
        branch: str,
        force: bool,
        incremental: bool,
        db: Session
    ):
        """Background indexing task"""
        job = db.query(IndexJob).get(job_id)
        repo = db.query(Repository).get(repo_id)
        repo_path = None
        
        try:
            print(f"\n{'='*60}")
            print(f"🚀 STARTING INDEXING JOB {job_id}")
            print(f"{'='*60}")
            
            if TESTING_MODE:
                print(f"⚙️  TESTING MODE:")
                print(f"   - Max files: {MAX_FILES_FOR_TESTING}")
                print(f"   - Skip embeddings: {SKIP_EMBEDDINGS}")
                print(f"{'='*60}\n")
            
            job.status = "running"
            job.started_at = datetime.now()
            db.commit()
            
            overall_start = time.time()
            
            # STEP 1: Clone Repository (0% -> 10%)
            print(f"📥 [STEP 1/7] Cloning repository...")
            step_start = time.time()
            
            repo_path = clone_repository(repo.github_url)
            commit_hash = self._get_commit_hash(repo_path)
            
            job.commit_hash = commit_hash
            job.progress = 0.1
            db.commit()
            
            print(f"✅ Clone completed in {time.time() - step_start:.2f}s\n")
            
            # STEP 2: Parse Files (10% -> 20%)
            print(f"📂 [STEP 2/7] Parsing repository files...")
            step_start = time.time()
            
            parsed_files = parse_repository_files(repo_path)
            
            if not parsed_files:
                raise Exception("No files found in repository")
            
            print(f"✅ Parsed {len(parsed_files)} files in {time.time() - step_start:.2f}s")
            
            # Limit files in testing mode
            if TESTING_MODE and len(parsed_files) > MAX_FILES_FOR_TESTING:
                print(f"⚠️  TESTING MODE: Limiting to first {MAX_FILES_FOR_TESTING} files")
                parsed_files = parsed_files[:MAX_FILES_FOR_TESTING]
            
            job.files_processed = len(parsed_files)
            job.progress = 0.2
            db.commit()
            
            print(f"📊 Progress: 20%\n")
            
            # STEP 3: Check for Changes (20% -> 25%)
            print(f"🔍 [STEP 3/7] Checking for changes...")
            step_start = time.time()
            
            files_to_index = parsed_files
            
            if incremental and not force:
                files_to_index = self._filter_changed_files(parsed_files, repo_id, db)
                print(f"✅ {len(files_to_index)}/{len(parsed_files)} files changed")
            else:
                print(f"✅ Processing all {len(files_to_index)} files (force={force})")
            
            print(f"⏱️  Change detection in {time.time() - step_start:.2f}s")
            
            job.progress = 0.25
            db.commit()
            
            # STEP 4: Process Files (25% -> 60%)
            print(f"⚙️  [STEP 4/7] Processing files (chunking + symbols)...")
            step_start = time.time()
            
            all_chunks, all_symbols = self._process_files(
                files_to_index, repo_id, db, job
            )
            
            job.chunks_created = len(all_chunks)
            job.symbols_extracted = len(all_symbols)
            job.progress = 0.6
            db.commit()
            
            print(f"✅ Processing completed in {time.time() - step_start:.2f}s")
            print(f"   - {len(all_chunks)} chunks created")
            print(f"   - {len(all_symbols)} symbols extracted")
            print(f"📊 Progress: 60%\n")
            
            # STEP 5: Store Chunks (60% -> 70%)
            print(f"💾 [STEP 5/7] Storing chunks in database...")
            step_start = time.time()
            
            self._store_chunks(all_chunks, repo_id, db)
            
            job.progress = 0.7
            db.commit()
            
            print(f"✅ Stored {len(all_chunks)} chunks in {time.time() - step_start:.2f}s")
            print(f"📊 Progress: 70%\n")
            
            # STEP 6: Store Symbols (70% -> 80%)
            print(f"💾 [STEP 6/7] Storing symbols in database...")
            step_start = time.time()
            
            self._store_symbols(all_symbols, repo_id, db)
            
            job.progress = 0.8
            db.commit()
            
            print(f"✅ Stored {len(all_symbols)} symbols in {time.time() - step_start:.2f}s")
            print(f"📊 Progress: 80%\n")
            
            # STEP 7: Generate Embeddings (80% -> 95%)
            if SKIP_EMBEDDINGS:
                print(f"⏭️  [STEP 7/7] Skipping embeddings (TESTING MODE)")
                job.progress = 0.95
                db.commit()
            else:
                print(f"🧠 [STEP 7/7] Generating embeddings...")
                print(f"   This is the slowest step (~0.2s per chunk)")
                step_start = time.time()
                
                self._generate_embeddings(all_chunks, repo_id, db, job)
                
                job.progress = 0.95
                db.commit()
                
                print(f"✅ Generated embeddings in {time.time() - step_start:.2f}s")
                print(f"📊 Progress: 95%\n")
            
            # COMPLETE
            job.status = "completed"
            job.progress = 1.0
            job.completed_at = datetime.now()
            db.commit()
            
            total_time = time.time() - overall_start
            
            print(f"\n{'='*60}")
            print(f"✅ INDEXING COMPLETED")
            print(f"{'='*60}")
            print(f"⏱️  Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
            print(f"📁 Files processed: {job.files_processed}")
            print(f"📦 Chunks created: {job.chunks_created}")
            print(f"🔤 Symbols extracted: {job.symbols_extracted}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ INDEXING FAILED")
            print(f"{'='*60}")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")
            
            import traceback
            traceback.print_exc()
            
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now()
            db.commit()
            
        finally:
            if repo_path:
                print(f"🧹 Cleaning up temporary directory...")
                cleanup_repository(repo_path)
    
    def _process_files(
        self,
        files_to_index: List[Dict],
        repo_id: int,
        db: Session,
        job: IndexJob
    ) -> tuple[List[Dict], List[Dict]]:
        """Process files sequentially with timeout detection"""
        all_chunks = []
        all_symbols = []
        
        total_files = len(files_to_index)
        progress_start = 0.25
        progress_end = 0.6
        progress_range = progress_end - progress_start
        
        print(f"   Processing {total_files} files sequentially...\n")
        
        # NUCLEAR OPTION: Skip first file if it's markdown (known to hang sometimes)
        if files_to_index and files_to_index[0].get('language') in ['markdown', 'md']:
            first_file = files_to_index[0]
            print(f"   ⚠️  First file is markdown: {first_file['file_path']}")
            print(f"   🔍 Attempting to process with 10s timeout...\n")
        
        for idx, file_info in enumerate(files_to_index):
            file_path = file_info.get('file_path', 'unknown')
            file_size = len(file_info['content'])
            
            # Check file size
            if file_size > 1_000_000:  # 1MB limit
                print(f"   [{idx+1}/{total_files}] ⏭️  Skipping: {file_path} (too large: {file_size/1024:.1f}KB)\n")
                continue
            
            try:
                print(f"   [{idx+1}/{total_files}] 📄 Processing: {file_path} ({file_size/1024:.1f}KB)")
                start_time = time.time()
                
                # STEP 1: Save file to database with timeout
                print(f"      → [1/3] Saving to DB...", end='', flush=True)
                save_start = time.time()
                
                try:
                    code_file = run_with_timeout(
                        self._save_file,
                        args=(file_info, repo_id, db),
                        timeout_duration=10
                    )
                    print(f" ✓ ({time.time() - save_start:.2f}s)")
                except TimeoutException:
                    print(f" ⏰ TIMEOUT after 10s!")
                    print(f"      ❌ Database operation is hanging. Skipping file.\n")
                    continue
                except Exception as e:
                    print(f" ❌ FAILED: {str(e)}\n")
                    continue
                
                # Create chunks for the file (use ast_chunker if available, otherwise fall back to one chunk)
                chunks = []
                try:
                    # Try a few common call patterns for ast_chunker if it exposes helpers
                    if callable(getattr(ast_chunker, "chunk", None)):
                        chunks = ast_chunker.chunk(file_info['content'], language=file_info.get('language'), file_path=file_info.get('file_path'))
                    elif callable(getattr(ast_chunker, "chunk_file", None)):
                        chunks = ast_chunker.chunk_file(file_info['content'], file_info.get('language'), file_info.get('file_path'))
                    elif callable(ast_chunker):
                        chunks = ast_chunker(file_info['content'], file_info.get('language'), file_info.get('file_path'))
                except Exception as e:
                    print(f"      ⚠️  Chunking failed: {e} - falling back to single-chunk")
                    chunks = []
                
                # Fallback: single chunk representing the whole file
                if not chunks:
                    lines = file_info['content'].splitlines()
                    total_lines = len(lines) if lines else 1
                    content_hash = hashlib.sha256(file_info['content'].encode()).hexdigest()
                    chunks = [{
                        'content': file_info['content'],
                        'chunk_index': 0,
                        'start_line': 1,
                        'end_line': total_lines,
                        'language': file_info.get('language'),
                        'chunk_type': 'block',
                        'keywords': [],
                        'content_hash': content_hash,
                        'file_path': file_info['file_path']
                    }]
                
                # Add metadata to chunks
                for chunk in chunks:
                    chunk['file_id'] = code_file.id
                    chunk['repo_id'] = repo_id
                
                all_chunks.extend(chunks)
                
                # STEP 3: Extract symbols with timeout
                symbols = []
                if search_config.EXTRACT_SYMBOLS:
                    print(f"      → [3/3] Extracting symbols...", end='', flush=True)
                    symbol_start = time.time()
                    
                    try:
                        symbols = run_with_timeout(
                            symbol_extractor.extract_symbols,
                            kwargs={
                                'content': file_info['content'],
                                'language': file_info['language'],
                                'file_path': file_info['file_path']
                            },
                            timeout_duration=10
                        )
                        print(f" ✓ {len(symbols)} symbols ({time.time() - symbol_start:.2f}s)")
                    except TimeoutException:
                        print(f" ⏰ TIMEOUT after 10s!")
                        print(f"      ⚠️  Symbol extraction hanging. Skipping symbols.")
                        symbols = []
                    except Exception as e:
                        print(f" ❌ FAILED: {str(e)}")
                        symbols = []
                    
                    # Add metadata to symbols
                    for symbol in symbols:
                        symbol['file_id'] = code_file.id
                        symbol['repo_id'] = repo_id
                    
                    all_symbols.extend(symbols)
                
                elapsed = time.time() - start_time
                print(f"   ✅ Complete: {len(chunks)} chunks, {len(symbols)} symbols ({elapsed:.2f}s)\n")
                
                # Update progress
                current_progress = progress_start + (progress_range * (idx + 1) / total_files)
                job.progress = current_progress
                db.commit()
                
            except Exception as e:
                print(f"   ❌ Unexpected error: {str(e)}")
                import traceback
                traceback.print_exc()
                print()
                continue
        
        return all_chunks, all_symbols
    
    def _save_file(self, file_info: Dict, repo_id: int, db: Session) -> CodeFile:
        """Save file to database"""
        try:
            existing_file = db.query(CodeFile).filter(
                CodeFile.repo_id == repo_id,
                CodeFile.file_path == file_info['file_path']
            ).first()
            
            if existing_file:
                code_file = existing_file
                code_file.content = file_info['content']
                code_file.file_metadata = file_info['metadata']
            else:
                code_file = CodeFile(
                    repo_id=repo_id,
                    file_path=file_info['file_path'],
                    content=file_info['content'],
                    language=file_info['language'],
                    file_metadata=file_info['metadata']
                )
                db.add(code_file)
            
            db.commit()
            db.refresh(code_file)
            
            # Expire session to avoid caching issues
            db.expire_all()
            
            return code_file
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Database error: {str(e)}")
    
    def _get_commit_hash(self, repo_path: str) -> str:
        """Get current commit hash"""
        try:
            from git import Repo
            git_repo = Repo(repo_path)
            return git_repo.head.commit.hexsha
        except:
            return None
    
    def _filter_changed_files(
        self,
        parsed_files: List[Dict],
        repo_id: int,
        db: Session
    ) -> List[Dict]:
        """Filter files that have changed"""
        changed_files = []
        
        for file_info in parsed_files:
            file_hash = hashlib.sha256(file_info['content'].encode()).hexdigest()
            
            existing_file = db.query(CodeFile).filter(
                CodeFile.repo_id == repo_id,
                CodeFile.file_path == file_info['file_path']
            ).first()
            
            if not existing_file:
                changed_files.append(file_info)
            else:
                existing_hash = hashlib.sha256(existing_file.content.encode()).hexdigest()
                if existing_hash != file_hash:
                    changed_files.append(file_info)
        
        return changed_files
    
    def _store_chunks(self, chunks: List[Dict], repo_id: int, db: Session):
        """Store chunks in database"""
        if not chunks:
            return
        
        # Delete existing chunks
        file_ids = list(set(chunk['file_id'] for chunk in chunks))
        db.query(CodeChunk).filter(
            CodeChunk.repo_id == repo_id,
            CodeChunk.file_id.in_(file_ids)
        ).delete(synchronize_session=False)
        db.commit()
        
        # Insert new chunks
        for chunk in chunks:
            db_chunk = CodeChunk(
                repo_id=chunk['repo_id'],
                file_id=chunk['file_id'],
                content=chunk['content'],
                chunk_index=chunk['chunk_index'],
                start_line=chunk['start_line'],
                end_line=chunk['end_line'],
                language=chunk['language'],
                chunk_type=chunk.get('chunk_type', 'block'),
                keywords=chunk.get('keywords', []),
                content_hash=chunk['content_hash']
            )
            db.add(db_chunk)
        
        db.commit()
    
    def _store_symbols(self, symbols: List[Dict], repo_id: int, db: Session):
        """Store symbols in database"""
        if not symbols:
            return
        
        # Delete existing symbols
        file_ids = list(set(symbol['file_id'] for symbol in symbols))
        db.query(Symbol).filter(
            Symbol.repo_id == repo_id,
            Symbol.file_id.in_(file_ids)
        ).delete(synchronize_session=False)
        db.commit()
        
        # Insert new symbols
        for symbol in symbols:
            db_symbol = Symbol(
                repo_id=symbol['repo_id'],
                file_id=symbol['file_id'],
                name=symbol['name'],
                qualified_name=symbol.get('qualified_name'),
                symbol_type=symbol['symbol_type'],
                signature=symbol.get('signature'),
                start_line=symbol['start_line'],
                end_line=symbol['end_line'],
                start_column=symbol.get('start_column'),
                end_column=symbol.get('end_column'),
                docstring=symbol.get('docstring'),
                comment=symbol.get('comment'),
                language=symbol['language'],
                scope=symbol.get('scope', 'public')
            )
            db.add(db_symbol)
        
        db.commit()
    
    def _generate_embeddings(
        self,
        chunks: List[Dict],
        repo_id: int,
        db: Session,
        job: IndexJob
    ):
        """Generate embeddings and store in ChromaDB"""
        if not chunks:
            return
        
        collection_name = f"repo_{repo_id}_chunks"
        
        # Delete existing collection
        try:
            chroma_client.delete_collection(name=collection_name)
        except:
            pass
        
        # Create new collection
        collection = chroma_client.create_collection(
            name=collection_name,
            metadata={"repo_id": str(repo_id)}
        )
        
        # Process in batches
        batch_size = 50
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        progress_start = 0.8
        progress_end = 0.95
        progress_range = progress_end - progress_start
        
        print(f"   Processing {len(chunks)} chunks in {total_batches} batches...\n")
        
        for batch_idx in range(0, len(chunks), batch_size):
            batch = chunks[batch_idx:batch_idx + batch_size]
            current_batch = (batch_idx // batch_size) + 1
            
            try:
                # Generate embeddings
                texts = [chunk['content'] for chunk in batch]
                batch_start = time.time()
                chunk_embeddings = embeddings.embed_documents(texts)
                batch_time = time.time() - batch_start
                
                # Prepare data
                ids = [f"chunk_{c['repo_id']}_{c['file_id']}_{c['chunk_index']}" for c in batch]
                metadatas = [{
                    'repo_id': c['repo_id'],
                    'file_id': c['file_id'],
                    'file_path': c['file_path'],
                    'language': c['language'],
                    'chunk_type': c.get('chunk_type', 'block'),
                    'start_line': c['start_line'],
                    'end_line': c['end_line'],
                    'chunk_index': c['chunk_index']
                } for c in batch]
                
                # Add to ChromaDB
                collection.add(
                    ids=ids,
                    embeddings=chunk_embeddings,
                    documents=texts,
                    metadatas=metadatas
                )
                
                # Update vector_id in database
                for idx, chunk in enumerate(batch):
                    db.query(CodeChunk).filter(
                        CodeChunk.repo_id == chunk['repo_id'],
                        CodeChunk.file_id == chunk['file_id'],
                        CodeChunk.chunk_index == chunk['chunk_index']
                    ).update({'vector_id': ids[idx]})
                
                db.commit()
                
                # Update progress
                current_progress = progress_start + (progress_range * current_batch / total_batches)
                job.progress = current_progress
                db.commit()
                
                print(f"   ✓ Batch {current_batch}/{total_batches}: {batch_time:.2f}s ({batch_time/len(texts):.3f}s/chunk) [{current_progress*100:.0f}%]")
                
            except Exception as e:
                print(f"   ❌ Batch {current_batch} failed: {str(e)}")
                continue
    
    def get_job_status(self, job_id: int, db: Session) -> Optional[IndexJob]:
        """Get indexing job status"""
        return db.query(IndexJob).get(job_id)


# Singleton instance
indexing_service = IndexingService()