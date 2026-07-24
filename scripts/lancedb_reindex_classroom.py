"""
Wipe and re-index all chunks for one classroom.

Steps:
  1. Look up all active Resource rows for the classroom (from Cassandra).
  2. Wipe all LanceDB chunks whose metadata.classroom_id == <uid>.
  3. For each Resource, download from R2 into a tmp file, then re-ingest.

Usage:
    python scripts/lancedb_reindex_classroom.py <classroom_uid>
"""

import os
import sys
import tempfile
import uuid as _uuid

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

import requests
from core.ai.rag.services.rag_pipeline import RAGPipeline
from features.resource.repositories.resource_repository import ResourceRepository


def download_to_tmp(url: str, suffix: str) -> str:
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if chunk:
                f.write(chunk)
    return path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/lancedb_reindex_classroom.py <classroom_uid>")
        sys.exit(1)

    classroom_uid = sys.argv[1]
    print(f"== Reindex classroom {classroom_uid} ==")

    pipeline = RAGPipeline()

    wiped = pipeline.delete_document({"classroom_id": classroom_uid})
    print(f"[1/3] Wiped {wiped} existing chunk(s)")

    owner_id = _uuid.UUID(classroom_uid)
    resources = ResourceRepository().filter(
        owner_id=owner_id,
        owner_type="classroom",
        is_deleted=False,
    )
    print(f"[2/3] Found {len(resources)} active resource(s)")

    total_chunks = 0
    failed = []
    for res in resources:
        ext = os.path.splitext(res.name or "")[1].lower() or ".bin"
        url = res.url
        if not url:
            print(f"  - skip {res.name}: no url")
            continue
        tmp_path = None
        try:
            tmp_path = download_to_tmp(url, ext)
            metadata = {
                "classroom_id": classroom_uid,
                "resource_uid": str(res.uid),
                "doc_name": res.name,
                "doc_url": res.url,
            }
            md = res.metadata or {}
            if isinstance(md, dict):
                if md.get("section"):
                    metadata["section"] = md["section"]
                if md.get("folder_id"):
                    metadata["folder_id"] = str(md["folder_id"])
                if md.get("exam_period"):
                    metadata["exam_period"] = md["exam_period"]

            result = pipeline.ingest(file_path=tmp_path, metadata=metadata)
            print(f"  + {res.name}: {result['chunks']} chunk(s)")
            total_chunks += result["chunks"]
        except Exception as exc:
            print(f"  ! {res.name}: FAILED — {exc}")
            failed.append((res.name, str(exc)))
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    print(f"[3/3] Done. Re-ingested {total_chunks} chunk(s) across {len(resources)} file(s).")
    if failed:
        print(f"  {len(failed)} file(s) failed:")
        for n, e in failed:
            print(f"    - {n}: {e}")


if __name__ == "__main__":
    main()
