"""
LanceVectorService — local vector store backed by LanceDB.

Data lives in {BASE_DIR}/lancedb/<collection_name>/ as Arrow files.
Pass embed_dim when creating a new table; opening an existing table infers it from schema.
"""

import json
import os

import lancedb
import pyarrow as pa
from decouple import config
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
                    pa.field("metadata_json", pa.string()),
                ])
                self._tbl = self._db.create_table(self._collection_name, schema=schema)
        return self._tbl

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, vector: list, doc_id: str, document: str = "", metadata: dict = None):
        tbl = self._table()
        try:
            tbl.delete(f"id = '{doc_id}'")
        except Exception:
            pass
        tbl.add([{
            "id": doc_id,
            "vector": [float(x) for x in vector],
            "document": document or "",
            "metadata_json": json.dumps(metadata or {}),
        }])

    def add_batch(self, rows: list):
        """rows: list of {id, vector, document, metadata}"""
        tbl = self._table()
        records = []
        for r in rows:
            records.append({
                "id": r["id"],
                "vector": [float(x) for x in r["vector"]],
                "document": r.get("document", ""),
                "metadata_json": json.dumps(r.get("metadata", {})),
            })
        tbl.add(records)

    def query(self, vector: list, n_results: int = 5, where: dict = None) -> list:
        tbl = self._table()
        fetch_limit = n_results * 5 if where else n_results
        rows = (
            tbl.search([float(x) for x in vector])
            .metric("cosine")
            .limit(fetch_limit)
            .to_list()
        )
        results = []
        for r in rows:
            meta = json.loads(r.get("metadata_json", "{}"))
            if where and not all(meta.get(k) == v for k, v in where.items()):
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

    def delete_where(self, where: dict):
        """Delete all rows matching metadata filter (Python-level filter)."""
        tbl = self._table()
        arrow_tbl = tbl.to_arrow()
        ids = arrow_tbl.column("id").to_pylist()
        meta_list = [json.loads(m or "{}") for m in arrow_tbl.column("metadata_json").to_pylist()]
        to_delete = [
            ids[i] for i, meta in enumerate(meta_list)
            if all(meta.get(k) == v for k, v in where.items())
        ]
        for doc_id in to_delete:
            tbl.delete(f"id = '{doc_id}'")
        return len(to_delete)

    def count(self) -> int:
        return self._table().count_rows()
