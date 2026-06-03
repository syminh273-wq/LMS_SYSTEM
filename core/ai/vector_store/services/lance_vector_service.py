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
        if self._tbl is None:
            try:
                self._tbl = self._db.open_table(self._collection_name)
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
                    pa.field("section", pa.string()),
                    pa.field("metadata_json", pa.string()),
                ])
                self._tbl = self._db.create_table(self._collection_name, schema=schema)
                self._tbl.create_scalar_index("classroom_id")
                self._tbl.create_scalar_index("section")
        return self._tbl

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
                "section": meta.get("section", ""),
                "metadata_json": json.dumps(meta),
            })
        tbl.add(records)

    def query(self, vector: list, n_results: int = 5, where: dict = None) -> list:
        tbl = self._table()
        where = where or {}
        classroom_id = where.get("classroom_id")
        section = where.get("section")
        
        # filters that are now top-level columns
        top_level = ["classroom_id", "section"]
        remaining = {k: v for k, v in where.items() if k not in top_level}

        q = tbl.search([float(x) for x in vector]).metric("cosine")
        
        filter_parts = []
        if classroom_id:
            escaped_cid = str(classroom_id).replace("'", "''")
            filter_parts.append(f"classroom_id = '{escaped_cid}'")
        if section:
            escaped_sec = str(section).replace("'", "''")
            filter_parts.append(f"section = '{escaped_sec}'")
            
        if filter_parts:
            filter_str = " AND ".join(filter_parts)
            q = q.where(filter_str, prefilter=True)
            print(f"[LanceDB] SQL prefilter: {filter_str}")
        else:
            print(f"[LanceDB] No prefilter applied (searching full collection: '{self._collection_name}')")

        rows = q.limit(n_results * 3 if remaining else n_results).to_list()

        results = []
        for r in rows:
            meta = json.loads(r.get("metadata_json", "{}"))
            if remaining and not all(meta.get(k) == v for k, v in remaining.items()):
                continue
            results.append({
                "id": r["id"],
                "document": r["document"],
                "metadata": meta,
                "distance": r.get("_distance", 0.0),
                "score": round(1 - r.get("_distance", 0.0), 4),
            })
            if len(results) >= n_results:
                break
        return results

    def get_by_id(self, doc_id: str):
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
        self._table().delete(f"id = '{doc_id}'")

    def delete_where(self, where: dict) -> int:
        """Delete all rows matching filter. Returns count deleted."""
        tbl = self._table()
        classroom_id = where.get("classroom_id")
        section = where.get("section")

        top_level = {"classroom_id", "section"}
        remaining = {k: v for k, v in where.items() if k not in top_level}

        filter_parts = []
        if classroom_id:
            escaped_cid = str(classroom_id).replace("'", "''")
            filter_parts.append(f"classroom_id = '{escaped_cid}'")
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
        sec_col  = arrow_tbl.column("section").to_pylist()
        meta_list = [json.loads(m or "{}") for m in arrow_tbl.column("metadata_json").to_pylist()]

        to_delete = []
        for i, (rid, cid, sec, meta) in enumerate(zip(ids, cid_col, sec_col, meta_list)):
            if classroom_id and cid != str(classroom_id):
                continue
            if section and sec != str(section):
                continue
            if remaining and not all(meta.get(k) == v for k, v in remaining.items()):
                continue
            to_delete.append(rid)

        for doc_id in to_delete:
            tbl.delete(f"id = '{doc_id}'")
        return len(to_delete)

    def count(self) -> int:
        return self._table().count_rows()
