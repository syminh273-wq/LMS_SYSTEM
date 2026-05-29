import typesense
from django.conf import settings


class TypesenseClient:
    """Singleton Typesense client — one connection per process."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.client = typesense.Client({
            'nodes': [{
                'host':     settings.TYPESENSE_HOST,
                'port':     settings.TYPESENSE_PORT,
                'protocol': settings.TYPESENSE_PROTOCOL,
            }],
            'api_key':                  settings.TYPESENSE_API_KEY,
            'connection_timeout_seconds': 2,
        })
        self._initialized = True

    # ── Collections ───────────────────────────────────────────────────────────

    def create_collection(self, schema: dict):
        return self.client.collections.create(schema)

    def get_collection(self, name: str):
        return self.client.collections[name].retrieve()

    def delete_collection(self, name: str):
        return self.client.collections[name].delete()

    # ── Documents ─────────────────────────────────────────────────────────────

    def upsert_document(self, collection: str, document: dict):
        return self.client.collections[collection].documents.upsert(document)

    def delete_document(self, collection: str, doc_id: str):
        return self.client.collections[collection].documents[doc_id].delete()

    def bulk_upsert(self, collection: str, documents: list[dict]) -> str:
        import json
        jsonl = '\n'.join(json.dumps(d) for d in documents)
        return self.client.collections[collection].documents.import_(
            jsonl, {'action': 'upsert'}
        )

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, collection: str, params: dict):
        return self.client.collections[collection].documents.search(params)

    # ── Utility ───────────────────────────────────────────────────────────────

    def health(self) -> bool:
        try:
            return self.client.operations.is_healthy()
        except Exception:
            return False

    def get_stats(self, collection: str) -> dict:
        try:
            return self.client.collections[collection].retrieve()
        except Exception:
            return {}
