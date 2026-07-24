"""
Inspect current LanceDB state.

Usage:
    python scripts/lancedb_inspect.py                 # whole collection
    python scripts/lancedb_inspect.py --classroom X  # filter by classroom
"""

import argparse
import json
import os
import sys

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "LMS_SYSTEM.settings")
django.setup()

import lancedb
from django.conf import settings

from core.ai.rag.services.rag_pipeline import RAGPipeline


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--classroom", default=None, help="filter by classroom_id")
    args = p.parse_args()

    db_path = os.path.join(settings.BASE_DIR, "lancedb")
    db = lancedb.connect(db_path)
    try:
        tbl = db.open_table(RAGPipeline.DEFAULT_COLLECTION)
    except Exception:
        print(f"Collection '{RAGPipeline.DEFAULT_COLLECTION}' not found in {db_path}")
        return

    print(f"Collection: {RAGPipeline.DEFAULT_COLLECTION}")
    print(f"Path:       {db_path}")
    print(f"Total rows: {tbl.count_rows()}")
    print(f"Vector dim: {tbl.schema.field('vector').type.list_size}")
    print(f"Columns:    {tbl.schema.names}")
    print()

    arrow = tbl.to_arrow()
    ids = arrow.column("id").to_pylist()
    cids = arrow.column("classroom_id").to_pylist()
    secs = arrow.column("section").to_pylist()
    docs = arrow.column("document").to_pylist()
    mjs = arrow.column("metadata_json").to_pylist()

    if args.classroom:
        idx = [i for i, c in enumerate(cids) if c == args.classroom]
        print(f"Filter: classroom_id = {args.classroom}  → {len(idx)} row(s)")
    else:
        idx = list(range(len(ids)))

    print()
    summary = {}
    for i in idx:
        m = json.loads(mjs[i] or "{}")
        key = (cids[i], m.get("doc_name", "?"), m.get("resource_uid", "?"))
        summary.setdefault(key, 0)
        summary[key] += 1

    print(f"Distinct (classroom, doc, resource): {len(summary)}")
    for (cid, dn, ru), n in sorted(summary.items(), key=str):
        print(f"  • {n:3d} chunk(s) | classroom={cid} | doc={dn} | resource={ru}")
    print()

    if args.classroom and idx:
        print("--- Chunk previews ---")
        for i in idx[:5]:
            m = json.loads(mjs[i] or "{}")
            print(f"  [{ids[i][:8]}] page={m.get('page')} score_preview: {docs[i][:90].replace(chr(10),' ')!r}")
        if len(idx) > 5:
            print(f"  ... ({len(idx) - 5} more)")


if __name__ == "__main__":
    sys.exit(main() or 0)
