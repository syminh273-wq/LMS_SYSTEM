"""
Re-index all classroom documents from R2 into LanceDB.

Walks every Resource with owner_type='classroom', downloads the file,
and ingests it into the RAG pipeline with the correct metadata.

Run: python scripts/lancedb_reindex.py
"""
import os
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")

import django
django.setup()

import requests
from features.resource.models.resource import Resource
from core.ai.rag.services.rag_pipeline import RAGPipeline

_INDEXABLE = {'.pdf', '.txt', '.md', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.json', '.xml'}

pipeline = RAGPipeline()

resources = list(Resource.objects.filter(bucket=0, owner_type='classroom').all())
indexable = [r for r in resources if not r.is_deleted and f".{r.file_type.lower()}" in _INDEXABLE]

print(f"Total classroom resources : {len(resources)}")
print(f"Indexable (non-deleted)   : {len(indexable)}")

if not indexable:
    print("Nothing to index.")
    sys.exit(0)

ok = 0
fail = 0

for r in indexable:
    print(f"\n[{ok + fail + 1}/{len(indexable)}] {r.name} ({r.file_type}) — classroom {r.owner_id}")
    suffix = f".{r.file_type.lower()}"
    tmp_path = None
    try:
        resp = requests.get(r.url, timeout=60)
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        from features.course.classroom.repositories import Repository as ClassroomRepo
        try:
            classroom = ClassroomRepo().find(str(r.owner_id))
            teacher_id = str(classroom.teacher_id) if classroom else ''
        except Exception:
            teacher_id = ''

        result = pipeline.ingest(
            file_path=tmp_path,
            metadata={
                'classroom_id': str(r.owner_id),
                'teacher_id':   teacher_id,
                'resource_uid': str(r.uid),
                'doc_name':     r.name,
                'doc_url':      r.url,
                'section':      r.metadata.get('section', '') if r.metadata else '',
                'file_type':    r.file_type.lower(),
            },
        )
        print(f"  OK — {result['chunks']} chunks ingested")
        ok += 1
    except Exception as exc:
        print(f"  FAILED — {exc}")
        fail += 1
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

print(f"\n{'='*40}")
print(f"Done. Success: {ok}  Failed: {fail}")
