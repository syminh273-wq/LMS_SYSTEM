import lancedb
import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

from core.ai.rag.services.rag_pipeline import RAGPipeline

def test_rag_retrieval(classroom_id=None, query="Bác Hồ", ingest_sample=True):
    # Always use the global collection
    pipeline = RAGPipeline()

    print(f"--- Testing RAG Retrieval on GLOBAL collection: {pipeline.collection} ---")

    if ingest_sample:
        # 2. Ingest Sample Data
        sample_texts = [
            {"text": "Học máy (Machine Learning) là một lĩnh vực của trí tuệ nhân tạo.", "meta": {"subject": "AI", "classroom_id": "test_class"}},
            {"text": "Mạng nơ-ron nhân tạo được lấy cảm hứng từ cấu trúc não bộ.", "meta": {"subject": "AI", "classroom_id": "test_class"}},
            {"text": "Lập trình Python rất phổ biến trong phân tích dữ liệu.", "meta": {"subject": "Programming", "classroom_id": "test_class"}},
            {"text": "Django là một framework web mạnh mẽ của Python.", "meta": {"subject": "Programming", "classroom_id": "test_class"}},
        ]

        print("\n[Ingesting sample data into GLOBAL collection...]")
        for item in sample_texts:
            pipeline.ingest(text=item["text"], metadata=item["meta"])

    # 3. Test Search
    filter_meta = {"classroom_id": classroom_id} if classroom_id else None
    
    print(f"\n[Search query: '{query}']")
    if filter_meta:
        print(f"[Filter: {filter_meta}]")
    else:
        print("[No filter - searching entire collection]")
        
    results = pipeline.search(query, top_k=3, filter_meta=filter_meta)
    
    if not results:
        print(" -> No results found in search.")
    else:
        for r in results:
            print(f" - [{r['score']}] {r['document'][:100]}... (Meta: {r['metadata']})")

    # 4. Test Ask (Full RAG)
    print(f"\n[Asking AI: '{query}']")
    ask_result = pipeline.ask(query, top_k=3, filter_meta=filter_meta)
    print(f"\nAI ANSWER:\n{ask_result['answer']}")
    
    if ask_result.get('sources'):
        print("\nSOURCES USED (deduplicated by API):")
        for s in ask_result['sources']:
            name = s.get('doc_name', 'Unknown')
            pages = s.get('pages', [])
            page_info = f" (Pages: {', '.join(map(str, pages))})" if pages else ""
            print(f" - {name}{page_info}")

if __name__ == "__main__":
    # Usage: 
    #   poetry run python scripts/test_rag_filtering.py [classroom_id] [query]
    class_id = sys.argv[1] if len(sys.argv) > 1 else None
    search_query = sys.argv[2] if len(sys.argv) > 2 else "Bác Hồ"
    
    # If a classroom_id is provided, we assume we want to search existing data
    should_ingest = class_id is None
    
    try:
        test_rag_retrieval(classroom_id=class_id, query=search_query, ingest_sample=should_ingest)
    except Exception as e:
        import traceback
        traceback.print_exc()
