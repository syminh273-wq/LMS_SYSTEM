import os
import django
import sys
import uuid

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

from core.ai.rag.services.rag_pipeline import RAGPipeline
from core.ai.vector_store.services.lance_vector_service import LanceVectorService

def test_classroom_isolation():
    pipeline = RAGPipeline()
    classroom_a = str(uuid.uuid4())
    classroom_b = str(uuid.uuid4())
    
    print(f"--- Testing Classroom Isolation ---")
    print(f"Classroom A: {classroom_a}")
    print(f"Classroom B: {classroom_b}")

    # 1. Ingest into Classroom A
    print("\n[1] Ingesting Document X into Classroom A...")
    pipeline.ingest(text="This is Document X, only for Classroom A.", metadata={"classroom_id": classroom_a, "doc_name": "DocX"})
    
    # 2. Ingest into Classroom B
    print("[2] Ingesting Document Y into Classroom B...")
    pipeline.ingest(text="This is Document Y, only for Classroom B.", metadata={"classroom_id": classroom_b, "doc_name": "DocY"})

    # 3. Query Classroom A -> Expect only Document X
    print(f"\n[3] Querying Classroom A ('Document')...")
    results_a = pipeline.search("Document", filter_meta={"classroom_id": classroom_a})
    found_x = any("Document X" in r["document"] for r in results_a)
    found_y = any("Document Y" in r["document"] for r in results_a)
    print(f" -> Found Document X: {found_x}")
    print(f" -> Found Document Y: {found_y} (Expected: False)")
    assert found_x and not found_y, "Isolation failed: Classroom A found B's docs or missed its own."

    # 4. Query Classroom B -> Expect only Document Y
    print(f"\n[4] Querying Classroom B ('Document')...")
    results_b = pipeline.search("Document", filter_meta={"classroom_id": classroom_b})
    found_x = any("Document X" in r["document"] for r in results_b)
    found_y = any("Document Y" in r["document"] for r in results_b)
    print(f" -> Found Document X: {found_x} (Expected: False)")
    print(f" -> Found Document Y: {found_y}")
    assert found_y and not found_x, "Isolation failed: Classroom B found A's docs or missed its own."
    
    print("\n✅ Classroom Isolation test passed!")

def test_section_filtering():
    pipeline = RAGPipeline()
    classroom_id = str(uuid.uuid4())
    section_1 = "week1"
    section_2 = "week2"
    
    print(f"\n--- Testing Section Filtering in Classroom {classroom_id} ---")

    # 1. Ingest Week 1 doc
    print(f"[1] Ingesting Doc W1 into Section {section_1}...")
    pipeline.ingest(text="Content for Week 1 lesson.", metadata={"classroom_id": classroom_id, "section": section_1, "doc_name": "Week1Doc"})
    
    # 2. Ingest Week 2 doc
    print(f"[2] Ingesting Doc W2 into Section {section_2}...")
    pipeline.ingest(text="Content for Week 2 lesson.", metadata={"classroom_id": classroom_id, "section": section_2, "doc_name": "Week2Doc"})

    # 3. Query Week 1 -> Expect only W1
    print(f"\n[3] Querying Section {section_1} ('lesson')...")
    results_1 = pipeline.search("lesson", filter_meta={"classroom_id": classroom_id, "section": section_1})
    found_w1 = any("Week 1" in r["document"] for r in results_1)
    found_w2 = any("Week 2" in r["document"] for r in results_1)
    print(f" -> Found Week 1: {found_w1}")
    print(f" -> Found Week 2: {found_w2} (Expected: False)")
    assert found_w1 and not found_w2, "Section filtering failed for Week 1."

    # 4. Query Week 2 -> Expect only W2
    print(f"\n[4] Querying Section {section_2} ('lesson')...")
    results_2 = pipeline.search("lesson", filter_meta={"classroom_id": classroom_id, "section": section_2})
    found_w1 = any("Week 1" in r["document"] for r in results_2)
    found_w2 = any("Week 2" in r["document"] for r in results_2)
    print(f" -> Found Week 1: {found_w1} (Expected: False)")
    print(f" -> Found Week 2: {found_w2}")
    assert found_w2 and not found_w1, "Section filtering failed for Week 2."

    # 5. Query Classroom (no section) -> Expect both
    print(f"\n[5] Querying Classroom (no section) ('lesson')...")
    results_all = pipeline.search("lesson", filter_meta={"classroom_id": classroom_id})
    found_w1 = any("Week 1" in r["document"] for r in results_all)
    found_w2 = any("Week 2" in r["document"] for r in results_all)
    print(f" -> Found Week 1: {found_w1}")
    print(f" -> Found Week 2: {found_w2}")
    assert found_w1 and found_w2, "Classroom query failed to find all sections."

    print("\n✅ Section Filtering test passed!")

def verify_schema():
    print(f"\n--- Verifying LanceDB Schema ---")
    store = LanceVectorService(RAGPipeline.DEFAULT_COLLECTION)
    tbl = store._table()
    schema = tbl.schema
    
    print(f"Columns in schema: {schema.names}")
    assert "classroom_id" in schema.names, "classroom_id column missing from schema"
    assert "section" in schema.names, "section column missing from schema"
    
    # Check if indices are created (implicitly by trying to query with where)
    # LanceDB doesn't easily expose index list via Python API without digging into internals
    print("✅ Schema verification passed (columns present)!")

if __name__ == "__main__":
    try:
        test_classroom_isolation()
        test_section_filtering()
        verify_schema()
        print("\n🎉 ALL TESTS PASSED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
