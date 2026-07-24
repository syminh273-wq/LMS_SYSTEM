"""
LanceVectorService — local vector store backed by LanceDB.

Data lives in {BASE_DIR}/lancedb/<collection_name>/ as Arrow files.
Schema has a top-level `classroom_id` column for native SQL pre-filtering
via LanceDB's .where(..., prefilter=True).
"""

import json
import os

import lancedb
import pyarrow as pa
from django.conf import settings


class LanceVectorService:
    def __init__(self, collection_name: str = "lms_store", embed_dim: int = None):
        db_path = os.path.join(settings.BASE_DIR, "lancedb")
        os.makedirs(db_path, exist_ok=True)
        self._db = lancedb.connect(db_path)
        self._collection_name = collection_name
        self._embed_dim = embed_dim
        self._tbl = None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _table(self):
        """
        Always re-open the table handle on every call. LanceDB's table handle
        is a cheap metadata read; the actual data is loaded lazily per-query.
        Re-opening is required because data ingested by a different
        LanceVectorService instance in the same process is otherwise invisible
        to this cached handle (the same on-disk table can be opened multiple
        times in one process, and writes via one handle don't propagate to
        the cached handle of another instance).
        """
        try:
            tbl = self._db.open_table(self._collection_name)
            actual_dim = tbl.schema.field("vector").type.list_size
            if self._embed_dim and self._embed_dim != actual_dim:
                print(
                    f"[LanceDB] WARN: table '{self._collection_name}' has dim={actual_dim} "
                    f"but embed_dim={self._embed_dim} was passed — using table dim"
                )
            return tbl
        except Exception:
            dim = self._embed_dim
            if not dim:
                raise ValueError(
                    f"Table '{self._collection_name}' does not exist. "
                    "Pass embed_dim= to create it."
                )
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
                pa.field("document", pa.string()),
                pa.field("classroom_id", pa.string()),
                pa.field("document_id", pa.string()),
                pa.field("chunk_index", pa.int32()),
                pa.field("section", pa.string()),
                pa.field("metadata_json", pa.string()),
            ])
            tbl = self._db.create_table(self._collection_name, schema=schema)
            tbl.create_scalar_index("classroom_id")
            tbl.create_scalar_index("document_id")
            tbl.create_scalar_index("section")
            return tbl

    def _actual_dim(self) -> int:
        return self._table().schema.field("vector").type.list_size

    def _has_table(self) -> bool:
        try:
            self._db.open_table(self._collection_name)
            return True
        except Exception:
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, vector: list, doc_id: str, document: str = "", metadata: dict = None):
        tbl = self._table()
        meta = metadata or {}
        try:
            tbl.delete(f"id = '{doc_id}'")
        except Exception:
            pass
        tbl.add([{
            "id": doc_id,
            "vector": [float(x) for x in vector],
            "document": document or "",
            "classroom_id": meta.get("classroom_id", ""),
            "document_id": meta.get("document_id", "") or meta.get("resource_uid", ""),
            "chunk_index": int(meta.get("chunk_index", 0) or 0),
            "section": meta.get("section", ""),
            "metadata_json": json.dumps(meta),
        }])

    def add_batch(self, rows: list):
        """rows: list of {id, vector, document, metadata}"""
        tbl = self._table()
        records = []
        for r in rows:
            meta = r.get("metadata") or {}
            records.append({
                "id": r["id"],
                "vector": [float(x) for x in r["vector"]],
                "document": r.get("document", ""),
                "classroom_id": meta.get("classroom_id", ""),
                "document_id": meta.get("document_id", "") or meta.get("resource_uid", ""),
                "chunk_index": int(meta.get("chunk_index", 0) or 0),
                "section": meta.get("section", ""),
                "metadata_json": json.dumps(meta),
            })
        tbl.add(records)

    def query(
        self,
        vector: list,
        n_results: int = 5,
        where: dict = None,
        per_resource_cap: int = 0,
    ) -> list:
        """
        Cosine similarity search with optional metadata filter and
        per-resource diversity cap.

        When `per_resource_cap > 0`, results are picked round-robin across
        distinct `document_id` values so a single chunky file can't dominate
        the top-K.
        """
        tbl = self._table()
        where = where or {}
        classroom_id = where.get("classroom_id")
        document_id = where.get("document_id")
        section = where.get("section")

        top_level = ["classroom_id", "document_id", "section"]
        remaining = {k: v for k, v in where.items() if k not in top_level}

        q = tbl.search([float(x) for x in vector]).metric("cosine")

        filter_parts = []
        if classroom_id:
            escaped_cid = str(classroom_id).replace("'", "''")
            filter_parts.append(f"classroom_id = '{escaped_cid}'")
        if document_id:
            escaped_did = str(document_id).replace("'", "''")
            filter_parts.append(f"document_id = '{escaped_did}'")
        if section:
            escaped_sec = str(section).replace("'", "''")
            filter_parts.append(f"section = '{escaped_sec}'")

        if filter_parts:
            filter_str = " AND ".join(filter_parts)
            q = q.where(filter_str, prefilter=True)
            print(f"[LanceDB] SQL prefilter: {filter_str}")
        else:
            print(f"[LanceDB] No prefilter applied (searching full collection: '{self._collection_name}')")

        over_fetch = n_results * (per_resource_cap if per_resource_cap > 0 else 3)
        if remaining:
            over_fetch = max(over_fetch, n_results * 3)
        rows = q.limit(over_fetch).to_list()

        # Build candidate list (already ordered by score ASC distance)
        candidates = []
        for r in rows:
            meta = json.loads(r.get("metadata_json", "{}"))
            if remaining and not all(meta.get(k) == v for k, v in remaining.items()):
                continue
            candidates.append({
                "id": r["id"],
                "document": r["document"],
                "metadata": meta,
                "distance": r.get("_distance", 0.0),
                "score": round(1 - r.get("_distance", 0.0), 4),
            })

        if per_resource_cap <= 0 or len(candidates) <= n_results:
            return candidates[:n_results]

        # Group by resource_uid, keep score order within each group
        groups: dict = {}
        for c in candidates:
            key = (c.get("metadata") or {}).get("resource_uid") or (c.get("metadata") or {}).get("doc_name") or "unknown"
            groups.setdefault(key, []).append(c)

        # Round-robin pick best chunks from each resource
        results = []
        while len(results) < n_results and any(groups.values()):
            progressed = False
            for key in list(groups.keys()):
                bucket = groups[key]
                if not bucket:
                    continue
                pick = bucket.pop(0)
                if len(results) < n_results:
                    results.append(pick)
                    progressed = True
                    if len(results) >= n_results:
                        break
                if len(bucket) >= per_resource_cap:
                    break
            if not progressed:
                break
        return results[:n_results]

    def get_by_id(self, doc_id: str):
        if not self._has_table():
            return None
        tbl = self._table()
        arrow_tbl = tbl.to_arrow()
        ids = arrow_tbl.column("id").to_pylist()
        idx = next((i for i, v in enumerate(ids) if v == doc_id), None)
        if idx is None:
            return None
        return {
            "id": ids[idx],
            "document": arrow_tbl.column("document").to_pylist()[idx],
            "metadata": json.loads(arrow_tbl.column("metadata_json").to_pylist()[idx] or "{}"),
            "embedding": arrow_tbl.column("vector").to_pylist()[idx],
        }

    def delete(self, doc_id: str):
        if not self._has_table():
            return
        self._table().delete(f"id = '{doc_id}'")

    def delete_where(self, where: dict) -> int:
        """Delete all rows matching filter. Returns count deleted."""
        if not self._has_table():
            return 0
        tbl = self._table()
        classroom_id = where.get("classroom_id")
        document_id = where.get("document_id")
        section = where.get("section")

        top_level = {"classroom_id", "document_id", "section"}
        remaining = {k: v for k, v in where.items() if k not in top_level}

        filter_parts = []
        if classroom_id:
            escaped_cid = str(classroom_id).replace("'", "''")
            filter_parts.append(f"classroom_id = '{escaped_cid}'")
        if document_id:
            escaped_did = str(document_id).replace("'", "''")
            filter_parts.append(f"document_id = '{escaped_did}'")
        if section:
            escaped_sec = str(section).replace("'", "''")
            filter_parts.append(f"section = '{escaped_sec}'")

        if filter_parts and not remaining:
            # Fast path: only top-level columns, use SQL directly
            filter_str = " AND ".join(filter_parts)
            count = tbl.count_rows(filter_str)
            tbl.delete(filter_str)
            return count

        # Mixed or metadata-only: pre-filter by top-level then scan metadata_json
        arrow_tbl = tbl.to_arrow()
        ids      = arrow_tbl.column("id").to_pylist()
        cid_col  = arrow_tbl.column("classroom_id").to_pylist()
        did_col  = arrow_tbl.column("document_id").to_pylist()
        sec_col  = arrow_tbl.column("section").to_pylist()
        meta_list = [json.loads(m or "{}") for m in arrow_tbl.column("metadata_json").to_pylist()]

        to_delete = []
        for i, (rid, cid, did, sec, meta) in enumerate(zip(ids, cid_col, did_col, sec_col, meta_list)):
            if classroom_id and cid != str(classroom_id):
                continue
            if document_id and did != str(document_id):
                continue
            if section and sec != str(section):
                continue
            if remaining and not all(meta.get(k) == v for k, v in remaining.items()):
                continue
            to_delete.append(rid)

        for doc_id in to_delete:
            tbl.delete(f"id = '{doc_id}'")
        return len(to_delete)

    def get_by_document_id(self, document_id: str) -> list:
        """Return all chunks for a document, sorted by chunk_index ASC."""
        if not self._has_table():
            return []
        tbl = self._table()
        escaped = str(document_id).replace("'", "''")
        try:
            rows = tbl.search().where(f"document_id = '{escaped}'", prefilter=True).to_list()
        except Exception:
            return []
        results = []
        for r in rows:
            meta = json.loads(r.get("metadata_json", "{}") or "{}")
            results.append({
                "id": r["id"],
                "document": r.get("document", ""),
                "metadata": meta,
                "chunk_index": int(r.get("chunk_index", 0) or 0),
            })
        results.sort(key=lambda x: x["chunk_index"])
        return results

    def count(self) -> int:
        if not self._has_table():
            return 0
        return self._table().count_rows()
