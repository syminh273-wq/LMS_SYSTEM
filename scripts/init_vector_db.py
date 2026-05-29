import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

from core.ai.embeddings.services.embedding_service import get_embedding_service
from core.ai.vector_store.services.lance_vector_service import LanceVectorService
from core.ai.rag.services.rag_pipeline import RAGPipeline

def create_table():
    embedder = get_embedding_service()
    print(f"Using embedder: {embedder.__class__.__name__}")
    
    # Get a sample embedding to determine dimension
    sample_vector = embedder.embed_query("Initialize table")
    dim = len(sample_vector)
    print(f"Detected embedding dimension: {dim}")
    
    collection_name = RAGPipeline.DEFAULT_COLLECTION
    print(f"Creating/Opening table: {collection_name}")
    
    store = LanceVectorService(collection_name=collection_name, embed_dim=dim)
    # Accessing _table() will trigger creation if it doesn't exist
    tbl = store._table()
    
    print(f"Table '{collection_name}' is ready. Count: {tbl.count_rows()}")

if __name__ == "__main__":
    create_table()
