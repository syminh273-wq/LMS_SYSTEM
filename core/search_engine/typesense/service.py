from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from django.conf import settings

from core.search_engine.typesense.client import TypesenseClient
from core.search_engine.typesense.schemas import TypesenseSchema


@dataclass
class SearchResult:
    id: str
    collection: str
    entity_id: str
    title: str
    snippet: str
    score: float
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'collection': self.collection,
            'entity_id': self.entity_id,
            'title': self.title,
            'snippet': self.snippet,
            'score': self.score,
            **self.extra,
        }


@dataclass
class SearchResponse:
    total_hits: int
    results: List[SearchResult]
    facets: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        return {
            'total_hits': self.total_hits,
            'results': [r.to_dict() for r in self.results],
            'facets': self.facets,
        }


class TypesenseService:
    """High-level Typesense operations for LMS."""

    # Collections already verified/patched this process lifetime — skip repeat API calls
    _ensured: set = set()

    def __init__(self):
        self.client = TypesenseClient()

    # ── Collection bootstrap ──────────────────────────────────────────────────

    def initialize_collections(self) -> None:
        """Create missing collections and patch schemas of existing ones."""
        for name in TypesenseSchema.names():
            try:
                self.ensure_collection(name)
            except Exception:
                pass  # never block startup

    def ensure_collection(self, name: str) -> None:
        """Create collection if absent; add any missing fields if it exists."""
        if name in TypesenseService._ensured:
            return

        schema = TypesenseSchema.get(name)
        if not schema:
            raise ValueError(f"No schema registered for '{name}'")

        try:
            existing = self.client.get_collection(name)
            # Patch schema: add fields present in schema but missing in Typesense
            existing_names = {f['name'] for f in existing.get('fields', [])}
            new_fields = [f for f in schema['fields'] if f['name'] not in existing_names]
            if new_fields:
                self.client.update_collection(name, new_fields)
        except Exception:
            # Collection doesn't exist yet — create it
            try:
                self.client.create_collection(schema)
            except Exception:
                pass

        TypesenseService._ensured.add(name)

    # ── Indexing ──────────────────────────────────────────────────────────────

    def upsert(self, collection: str, document: dict) -> None:
        if not getattr(settings, 'TYPESENSE_ENABLED', True):
            return
        try:
            self.ensure_collection(collection)
            self.client.upsert_document(collection, document)
        except Exception:
            pass  # never crash the main request

    def remove(self, collection: str, doc_id: str) -> None:
        if not getattr(settings, 'TYPESENSE_ENABLED', True):
            return
        try:
            self.client.delete_document(collection, doc_id)
        except Exception:
            pass

    def bulk_upsert(
        self,
        collection: str,
        instances: list,
        transformer: Callable,
        batch_size: int = 500,
    ) -> Dict[str, int]:
        self.ensure_collection(collection)
        total = ok = failed = 0
        for i in range(0, len(instances), batch_size):
            batch = instances[i:i + batch_size]
            docs = []
            for inst in batch:
                try:
                    docs.append(transformer(inst))
                except Exception:
                    failed += 1
            if docs:
                raw = self.client.bulk_upsert(collection, docs)
                for line in raw.splitlines():
                    try:
                        r = json.loads(line)
                        if r.get('success'):
                            ok += 1
                        else:
                            failed += 1
                    except Exception:
                        pass
            total += len(batch)
        return {'total': total, 'ok': ok, 'failed': failed}

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        collection: str,
        query: str,
        query_by: List[str],
        filter_by: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: Optional[str] = None,
        facet_by: Optional[str] = None,
    ) -> SearchResponse:
        params: Dict[str, Any] = {
            'q':         query,
            'query_by':  ','.join(query_by),
            'per_page':  limit,
            'page':      max(1, offset // limit + 1) if limit else 1,
            'num_typos': 2,
            'typo_tokens_threshold': 1,
            'prefix':    True,
            # fallback to infix (substring) when prefix returns no hits
            # requires fields to be indexed with infix:true in schema
            'infix':     'fallback',
        }
        if filter_by:
            params['filter_by'] = filter_by
        if sort_by:
            params['sort_by'] = sort_by
        if facet_by:
            params['facet_by'] = facet_by

        raw = self.client.search(collection, params)
        hits = raw.get('hits', [])
        total = raw.get('found', 0)

        results = []
        for hit in hits:
            doc = hit.get('document', {})
            highlights = hit.get('highlights', [])
            snippet = highlights[0].get('snippet', '') if highlights else doc.get('description', '')
            results.append(SearchResult(
                id=doc.get('id', ''),
                collection=collection,
                entity_id=doc.get('uid') or doc.get('consumer_uid') or doc.get('id', ''),
                title=doc.get('name') or doc.get('title') or doc.get('full_name') or doc.get('consumer_name') or '',
                snippet=snippet,
                score=hit.get('text_match', 0),
                extra={k: v for k, v in doc.items() if k not in ('id', 'uid')},
            ))

        facets = None
        if facet_by and raw.get('facet_counts'):
            facets = {fc['field_name']: fc['counts'] for fc in raw['facet_counts']}

        return SearchResponse(total_hits=total, results=results, facets=facets)

    # ── Utility ───────────────────────────────────────────────────────────────

    def health(self) -> bool:
        return self.client.health()

    def stats(self, collection: str) -> dict:
        return self.client.get_stats(collection)
