import logging
import uuid
from typing import Generator, List, Tuple, Union

import viparse
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ai.embeddings.services.embedding_service import get_embedding_service
from core.ai.llm.services.ai_client import AIClient
from core.ai.vector_store.services.lance_vector_service import LanceVectorService

logger = logging.getLogger('rag_pipeline')

_SYSTEM_PROMPT = (
    "Bạn là một trợ lý ảo hữu ích. Hãy trả lời câu hỏi của người dùng CHỈ bằng cách sử dụng ngữ cảnh được cung cấp. "
    "Nếu câu trả lời không có trong ngữ cảnh, hãy nói rằng bạn không biết. "
    "Hãy trả lời ngắn gọn và chính xác.\n\n"
    "Ngữ cảnh:\n{context}"
)

_NO_CONTEXT_MESSAGE = "Chưa tìm thấy tài liệu phù hợp. Vui lòng yêu cầu giáo viên tải tài liệu lên lớp học trước."


class RAGPipeline:
    DEFAULT_COLLECTION = "lms_document_text_store"
    DEFAULT_TOP_K = 6
    DEFAULT_PER_RESOURCE_CAP = 3
    DEFAULT_MIN_SCORE = 0.30

    def __init__(
        self,
        collection: str = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        top_k: int = None,
        per_resource_cap: int = None,
        min_score: float = None,
    ):
        self.collection = collection or self.DEFAULT_COLLECTION
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.default_top_k = top_k if top_k is not None else self.DEFAULT_TOP_K
        self.default_per_resource_cap = (
            per_resource_cap if per_resource_cap is not None else self.DEFAULT_PER_RESOURCE_CAP
        )
        self.default_min_score = (
            min_score if min_score is not None else self.DEFAULT_MIN_SCORE
        )
        self._embedder = None
        self._store_cache: dict = {}


    def _load_and_chunk(self, file_path: str, metadata: dict = None) -> list:
        """
        Load tài liệu → chunk bằng LangChain RecursiveCharacterTextSplitter.

        PDF / Office: dùng viparse (Vietnamese-first, NFC, chuẩn xuống dòng).
        TXT / MD: dùng LangChain TextLoader (viparse không hỗ trợ).
        """
        ext = file_path.lower().rsplit(".", 1)[-1]
        viparse_exts = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"}

        if ext in viparse_exts:
            docs = self._load_with_viparse(file_path, metadata)
        else:
            docs = self._load_with_textloader(file_path, metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_documents(docs)

    def _load_with_viparse(self, file_path: str, metadata: dict = None) -> List[Document]:
        """Dùng viparse để parse PDF/Office → LangChain Document list.

        `ocr=True` để viparse fallback qua Tesseract khi PDF dùng CID font
        subset không có ToUnicode mapping (trả raw `(cid:131)` thay vì
        ký tự tiếng Việt). Cần tesseract + tesseract-lang (vie) + poppler.
        """
        v_docs = viparse.load(file_path, ocr=True)
        docs = []
        for vd in v_docs:
            content = vd.text
            vmeta = vd.metadata
            meta = {
                "source": getattr(vmeta, "source", ""),
                "page": getattr(vmeta, "page", None),
                "engine": getattr(vmeta, "engine", ""),
                "lang": getattr(vmeta, "lang", ""),
                "content_type": getattr(vmeta, "content_type", ""),
            }
            extra = getattr(vmeta, "extra", None)
            if extra and isinstance(extra, dict):
                meta.update(extra)
            if metadata:
                meta.update(metadata)
            docs.append(Document(page_content=content, metadata=meta))
        return docs

    def _load_with_textloader(self, file_path: str, metadata: dict = None) -> List[Document]:
        """Dùng LangChain TextLoader cho .txt / .md / .csv…"""
        loader = TextLoader(file_path)
        docs = loader.load()
        if metadata:
            for doc in docs:
                doc.metadata.update(metadata)
        return docs

    def _chunk_text(self, text: str, metadata: dict = None) -> list:
        """Split a raw text string into chunks."""
        from langchain_core.documents import Document
        doc = Document(page_content=text, metadata=metadata or {})
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_documents([doc])


    def _get_embedder(self):
        if self._embedder is None:
            self._embedder = get_embedding_service()
        return self._embedder

    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._get_embedder().embed_documents(texts)

    def _embed_query(self, text: str) -> List[float]:
        return self._get_embedder().embed_query(text)



    def _get_store(self, embed_dim: int = None) -> LanceVectorService:
        """
        Trả về LanceVectorService cho collection hiện tại — tạo (và cache) MỘT LẦN
        duy nhất, tránh việc mở lại kết nối/table LanceDB mỗi khi retrieve/ingest
        được gọi (retrieve, ingest_document, ask/ask_stream đều đi qua đây).

        Vì sao cần `embed_dim`:
          Số chiều (dimension) của vector embedding chỉ biết được SAU LẦN GỌI
          MODEL EMBEDDING ĐẦU TIÊN (auto-detect, xem `_get_embedder`/dòng 393).
          Nếu `_get_store()` được gọi trước đó (chưa biết dim) rồi mới gọi lại
          với `embed_dim` xác định, ta backfill giá trị này vào store đã cache
          — thay vì tạo store mới — để không mất kết nối/table đã mở.

        Lưu ý: dù tên biến `_store_cache` gợi ý "cache theo dim", trên thực tế
        chỉ luôn dùng 1 key duy nhất (0) — đây là cache 1-slot (singleton),
        KHÔNG phải cache nhiều store theo từng dim khác nhau.
        """
        if not self._store_cache:
            # Lần gọi đầu tiên: chưa có store nào → tạo mới và cache lại.
            self._store_cache[0] = LanceVectorService(self.collection, embed_dim=embed_dim)
            return self._store_cache[0]

        store = self._store_cache[0]
        if embed_dim and not store._embed_dim:
            # Store đã tồn tại nhưng chưa biết dim (được tạo trước lần embed đầu
            # tiên) → set bổ sung dim vào, không tạo lại store.
            store._embed_dim = embed_dim
        return store


    def retrieve(
        self,
        query: str,
        classroom_id: str = None,
        document_id: str = None,
        top_k: int = None,
        section: str = None,
        per_resource_cap: int = None,
        min_score: float = None,
    ) -> List[dict]:
        """
        Embed query → cosine similarity search trong LanceDB.
        Filter BẮT BUỘC theo classroom_id (per theo spec).
        document_id là optional prefilter phụ.

        min_score: ngưỡng cosine similarity tối thiểu (0–1). Hit nào
        dưới ngưỡng sẽ bị loại bỏ để tránh context nhiễu. Mặc định
        dùng self.default_min_score = 0.30.
        """
        k = top_k or self.default_top_k
        cap = per_resource_cap if per_resource_cap is not None else self.default_per_resource_cap
        threshold = min_score if min_score is not None else self.default_min_score

        where: dict = {}
        if classroom_id:
            where["classroom_id"] = str(classroom_id)
        if document_id:
            where["document_id"] = str(document_id)
        if section:
            where["section"] = section

        logger.info(
            "[RAG:retrieve] query=%r filter=%s top_k=%s min_score=%s per_doc_cap=%s collection=%s",
            query, where, k, threshold, cap, self.collection,
        )

        if not classroom_id:
            raise ValueError("classroom_id is required for retrieval (security: prevent cross-classroom leakage)")

        query_vector = self._embed_query(query)
        store = self._get_store()
        raw_hits = store.query(query_vector, n_results=k, where=where, per_resource_cap=cap)

        hits = [h for h in raw_hits if h.get("score", 0) >= threshold]

        if logger.isEnabledFor(logging.INFO):
            lines = [f"[RAG:retrieve] Raw {len(raw_hits)} → kept {len(hits)} (≥{threshold}):"]
            for i, h in enumerate(hits, 1):
                meta = h.get("metadata", {})
                doc_name = meta.get("doc_name") or meta.get("document_id") or "?"
                page = meta.get("page")
                score = h.get("score", 0)
                preview = h["document"][:120].replace("\n", " ")
                lines.append(f"  [{i}] score={score:.4f} | {doc_name}" + (f" p.{page}" if page else "") + f" | {preview!r}")
            logger.info("\n".join(lines))
        return hits


    def _build_messages(self, question: str, context: str, system_prompt: str = None) -> list:
        system = (system_prompt or _SYSTEM_PROMPT).format(context=context)
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]

    def _deduplicate_sources(self, hits: List[dict]) -> List[dict]:
        """Group multiple chunks from the same document into unique source entries."""
        unique_docs: dict = {}
        for h in hits:
            meta = h.get("metadata") or {}
            doc_id = meta.get("document_id") or meta.get("resource_uid") or meta.get("doc_name") or "unknown"

            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    "doc_name": meta.get("doc_name", "Unknown Document"),
                    "document_id": meta.get("document_id") or meta.get("resource_uid"),
                    "resource_uid": meta.get("resource_uid") or meta.get("document_id"),
                    "doc_url": meta.get("doc_url"),
                    "pages": set(),
                    "score": h.get("score", 0),
                }

            page = meta.get("page")
            if page is not None:
                unique_docs[doc_id]["pages"].add(int(page))

            if h.get("score", 0) > unique_docs[doc_id]["score"]:
                unique_docs[doc_id]["score"] = h["score"]

        results = []
        for doc in unique_docs.values():
            doc["pages"] = sorted(list(doc["pages"]))
            results.append(doc)

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def build_context(self, hits: List[dict]) -> Tuple[str, List[dict]]:
        """Ghép các chunk thành context string + list sources đã dedupe."""
        if not hits:
            return "", []
        context = "\n\n---\n\n".join(h["document"] for h in hits)
        sources = self._deduplicate_sources(hits)
        return context, sources

    # ─────────────────────────────────────────────────────────────────────────
    # ⑥ generate_stream() — LLM streaming
    # ─────────────────────────────────────────────────────────────────────────

    def generate(
        self,
        question: str,
        context: str,
        system_prompt: str = None,
        timeout: int = 120,
    ) -> str:
        """Sync LLM call. Returns full answer string."""
        if not context:
            return _NO_CONTEXT_MESSAGE
        messages = self._build_messages(question, context, system_prompt)
        return AIClient.chat_sync(messages, timeout=timeout)

    def generate_stream(
        self,
        question: str,
        context: str,
        system_prompt: str = None,
        timeout: int = 300,
    ) -> Generator[str, None, None]:
        """
        LLM streaming. CHỈ yield text chunk (str).
        Nếu context rỗng thì yield message no-context rồi dừng.
        """
        if not context:
            yield _NO_CONTEXT_MESSAGE
            return

        messages = self._build_messages(question, context, system_prompt)
        for chunk in AIClient.chat_stream(messages, timeout=timeout):
            if isinstance(chunk, str):
                yield chunk
            elif isinstance(chunk, tuple):
                signal = chunk[0]
                if signal == "__ERROR__":
                    raise RuntimeError(str(chunk[1]))
                # __FULL__ / __TOOL_CALLS__ → bỏ qua, stream đã kết thúc


    def ingest(
        self,
        file_path: str = None,
        text: str = None,
        metadata: dict = None,
    ) -> dict:
        """
        ①②③ — Load → chunk → embed → store trong LanceDB.

        Idempotent theo document_id: nếu metadata có document_id và chunks
        cũ đã tồn tại, sẽ xoá hết trước khi ghi mới.

        Metadata bắt buộc: classroom_id, document_id
        Metadata khuyến nghị: doc_name, doc_url, section
        """
        metadata = metadata or {}
        if not metadata.get("classroom_id"):
            raise ValueError("metadata.classroom_id is required for ingest")
        if not metadata.get("document_id"):
            raise ValueError("metadata.document_id is required for ingest")

        if file_path:
            chunks = self._load_and_chunk(file_path, metadata)
            source = file_path
        elif text:
            chunks = self._chunk_text(text, metadata)
            source = "raw_text"
        else:
            raise ValueError("Provide file_path or text")

        if not chunks:
            return {"chunks": 0, "collection": self.collection, "source": source}

        # ① Gán chunk_index cho từng chunk
        for idx, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["document_id"] = str(metadata["document_id"])
            chunk.metadata["classroom_id"] = str(metadata["classroom_id"])

        # Idempotent: xoá chunks cũ của cùng document_id
        self.delete_document({"document_id": str(metadata["document_id"])})

        texts = [c.page_content for c in chunks]

        # ② Embed all chunks
        vectors = self._embed_documents(texts)
        dim = len(vectors[0])

        # ③ Store in LanceDB
        store = self._get_store(embed_dim=dim)
        rows = [
            {
                "id": str(uuid.uuid4()),
                "vector": vec,
                "document": chunk.page_content,
                "metadata": chunk.metadata,
            }
            for chunk, vec in zip(chunks, vectors)
        ]
        store.add_batch(rows)

        logger.info(
            "[RAG] Ingested %s chunks → '%s' (dim=%s, document_id=%s)",
            len(chunks), self.collection, dim, metadata['document_id'],
        )
        return {"chunks": len(chunks), "collection": self.collection, "source": source, "document_id": str(metadata["document_id"])}

    def ask(
        self,
        question: str,
        classroom_id: str = None,
        document_id: str = None,
        top_k: int = None,
        section: str = None,
        per_resource_cap: int = None,
        system_prompt: str = None,
        timeout: int = 120,
    ) -> dict:
        """
        Sync ④⑤⑥ — retrieve → build_context → generate.
        Returns {"answer": str, "sources": [list of matched chunks]}.
        """
        hits = self.retrieve(
            question,
            classroom_id=classroom_id,
            document_id=document_id,
            top_k=top_k,
            section=section,
            per_resource_cap=per_resource_cap,
        )
        context, sources = self.build_context(hits)

        if not context:
            return {"answer": _NO_CONTEXT_MESSAGE, "sources": []}

        answer = self.generate(question, context, system_prompt, timeout=timeout)
        return {"answer": answer, "sources": sources}

    def ask_stream(
        self,
        question: str,
        classroom_id: str = None,
        document_id: str = None,
        top_k: int = None,
        section: str = None,
        per_resource_cap: int = None,
        system_prompt: str = None,
        timeout: int = 300,
    ) -> Generator[Union[str, tuple], None, None]:
        """
        Streaming ④⑤⑥ — yield text chunks (str).
        Final yield: ('__SOURCES__', [list of matched chunks]).
        On error:    ('__ERROR__', message).
        """
        hits = self.retrieve(
            question,
            classroom_id=classroom_id,
            document_id=document_id,
            top_k=top_k,
            section=section,
            per_resource_cap=per_resource_cap,
        )
        context, sources = self.build_context(hits)

        if not context:
            yield ("__NO_DOC__", _NO_CONTEXT_MESSAGE)
            yield ("__SOURCES__", [])
            return

        try:
            for chunk in self.generate_stream(question, context, system_prompt, timeout=timeout):
                yield chunk
        except Exception as exc:
            yield ("__ERROR__", str(exc))
            return

        yield ("__SOURCES__", sources)

    def search(
        self,
        query: str,
        top_k: int = None,
        filter_meta: dict = None,
        per_resource_cap: int = None,
    ) -> List[dict]:
        """
        Backward-compat shim. Trích classroom_id/document_id từ filter_meta
        rồi gọi retrieve(). Trả về list hits (không gọi LLM).
        """
        return self.retrieve(
            query,
            classroom_id=(filter_meta or {}).get("classroom_id"),
            document_id=(filter_meta or {}).get("document_id"),
            top_k=top_k,
            section=(filter_meta or {}).get("section"),
            per_resource_cap=per_resource_cap,
        )

    def delete_document(self, filter_meta: dict) -> int:
        """Delete all chunks matching filter. Returns count deleted."""
        store = self._get_store()
        return store.delete_where(filter_meta)
