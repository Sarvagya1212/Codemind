# backend/app/config/chroma.py

import chromadb
from chromadb.config import Settings
import warnings
import os

os.environ['ANONYMIZED_TELEMETRY'] = 'False'
warnings.filterwarnings('ignore', message='.*telemetry.*')
warnings.filterwarnings('ignore', message='.*capture.*')

_chroma_client = None

def get_chroma_client():
    """
    Get or create ChromaDB client singleton.
    """
    global _chroma_client
    
    if _chroma_client is None:
        try:
            # Use persistent client with local storage
            _chroma_client = chromadb.PersistentClient(
                path="./chroma_data",
                settings=Settings(
                    anonymized_telemetry=False,  # Disable telemetry
                    allow_reset=True
                )
            )
            print("✅ ChromaDB client initialized (persistent)")
        except Exception as e:
            print(f"⚠️  ChromaDB initialization failed: {e}")
            # Fallback to ephemeral client
            try:
                _chroma_client = chromadb.Client(
                    Settings(
                        anonymized_telemetry=False,
                        is_persistent=False
                    )
                )
                print("⚠️  Using ephemeral ChromaDB client (data won't persist)")
            except:
                _chroma_client = None
    
    return _chroma_client