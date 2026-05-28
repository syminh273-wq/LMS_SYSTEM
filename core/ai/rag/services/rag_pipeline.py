"""
RAGPipeline — full Retrieval-Augmented Generation pipeline.

Flow
────
  Document / Text
      │
  ① LangChain Loader + RecursiveCharacterTextSplitter   (chunking)
      │
  ② Embedding Model  (OmniRoute or Ollama, via AI_MODE)
      │  auto-detects vector dimension from first call
      │
  ③ LanceDB                                              (vector store)
      │
  ④ Cosine Similarity Search                             (retrieval)
      │
  ⑤ LLM  (OmniRoute or Ollama, via AI_MODE)             (generation)
      │
  Answer + Sources

Usage
─────
    pipeline = RAGPipeline(collection="my_course")

    # Ingest a document
    result = pipeline.ingest("lecture.pdf", metadata={"classroom_id": "abc"})
    # → {"chunks": 24, "file": "lecture.pdf", "collection": "my_course"}

    # Ask a question
    result = pipeline.ask("What is gradient descent?", filter_meta={"classroom_id": "abc"})
    # → {"answer": "...", "sources": [...]}

    # Streaming answer
    for chunk in pipeline.ask_stream("Explain backpropagation"):
        print(chunk, end="", flush=True)

    # Just search (no LLM call)
    hits = pipeline.search("neural network layers", top_k=5)
    # → [{"id": ..., "document": ..., "metadata": ..., "score": ...}, ...]
"""

import uuid
from typing import Generator, List, Union

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.ai.embeddings.services.embedding_service import get_embedding_service
from core.ai.llm.services.ai_client import AIClient
from core.ai.vector_store.services.lance_vector_service import LanceVectorService

_SYSTEM_PROMPT = (
    "Bạn là một trợ lý ảo hữu ích. Hãy trả lời câu hỏi của người dùng CHỈ bằng cách sử dụng ngữ cảnh được cung cấp. "
    "Nếu câu trả lời không có trong ngữ cảnh, hãy nói rằng bạn không biết. "
    "Hãy trả lời ngắn gọn và chính xác.\n\n"
    "Ngữ cảnh:\n{context}"
)


class RAGPipeline:
    DEFAULT_COLLECTION = "lms_document_text_store"

    def __init__(
        self,
        collection: str = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        top_k: int = 3,
    ):
        self.collection = collection or self.DEFAULT_COLLECTION
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.default_top_k = top_k
        self._embedder = None
        self._store_cache: dict = {}  # dim → LanceVectorService

    # ─────────────────────────────────────────────────────────────────────────
    # ① LangChain — load & chunk
    # ─────────────────────────────────────────────────────────────────────────

    def _load_and_chunk(self, file_path: str, metadata: dict = None) -> list:
        """Load a PDF or TXT file and split into chunks using LangChain."""
        loader = PyPDFLoader(file_path) if file_path.lower().endswith(".pdf") else TextLoader(file_path)
        docs = loader.load()

        if metadata:
            for doc in docs:
                doc.metadata.update(metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_documents(docs)

    def _chunk_text(self, text: str, metadata: dict = None) -> list:
        """Split a raw text string into chunks."""
        from langchain_core.documents import Document
        doc = Document(page_content=text, metadata=metadata or {})
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_documents([doc])

    # ─────────────────────────────────────────────────────────────────────────
    # ② Embedding model
    # ─────────────────────────────────────────────────────────────────────────

    def _get_embedder(self):
        if self._embedder is None:
            self._embedder = get_embedding_service()
        return self._embedder

    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._get_embedder().embed_documents(texts)

    def _embed_query(self, text: str) -> List[float]:
        return self._get_embedder().embed_query(text)

    # ─────────────────────────────────────────────────────────────────────────
    # ③ LanceDB — vector store
    # ─────────────────────────────────────────────────────────────────────────

    def _get_store(self, embed_dim: int = None) -> LanceVectorService:
        key = embed_dim or 0
        if key not in self._store_cache:
            self._store_cache[key] = LanceVectorService(self.collection, embed_dim=embed_dim)
        return self._store_cache[key]

    # ─────────────────────────────────────────────────────────────────────────
    # ④ Similarity search
    # ─────────────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = None,
        filter_meta: dict = None,
    ) -> List[dict]:
        """
        Embed query → cosine similarity search in LanceDB.
        Returns list of {id, document, metadata, score}.
        """
        k = top_k or self.default_top_k
        query_vector = self._embed_query(query)
        store = self._get_store()
        return store.query(query_vector, n_results=k, where=filter_meta)

    # ─────────────────────────────────────────────────────────────────────────
    # ⑤ LLM — generate answer from retrieved context
    # ─────────────────────────────────────────────────────────────────────────

    def _build_messages(self, question: str, context: str, system_prompt: str = None) -> list:
        system = (system_prompt or _SYSTEM_PROMPT).format(context=context)
        return [
            {"role": "system", "content": system},
            {"role": "user",   "content": question},
        ]

    def _deduplicate_sources(self, hits: List[dict]) -> List[dict]:
        """Group multiple chunks from the same resource into unique source entries."""
        unique_docs = {}
        for h in hits:
            meta = h.get("metadata") or {}
            # Use resource_uid or doc_name as unique key
            doc_id = meta.get("resource_uid") or meta.get("doc_name") or "unknown"
            
            if doc_id not in unique_docs:
                unique_docs[doc_id] = {
                    "doc_name": meta.get("doc_name", "Unknown Document"),
                    "resource_uid": meta.get("resource_uid"),
                    "doc_url": meta.get("doc_url"),
                    "pages": set(),
                    "score": h.get("score", 0),
                }
            
            page = meta.get("page")
            if page is not None:
                unique_docs[doc_id]["pages"].add(int(page))
            
            # Keep the highest score
            if h.get("score", 0) > unique_docs[doc_id]["score"]:
                unique_docs[doc_id]["score"] = h["score"]

        # Convert sets to sorted lists for JSON serializability
        results = []
        for doc in unique_docs.values():
            doc["pages"] = sorted(list(doc["pages"]))
            results.append(doc)
        
        return sorted(results, key=lambda x: x["score"], reverse=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def ingest(self, file_path: str = None, text: str = None, metadata: dict = None) -> dict:
        """
        Step ①②③ — Load → chunk → embed → store in LanceDB.

        Pass file_path for PDF/TXT files, or text for raw string input.
        Returns {"chunks": n, "collection": ..., "source": ...}.
        """
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

        texts = [c.page_content for c in chunks]

        # ② Embed all chunks — auto-detect dimension from result
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

        print(f"[RAG] Ingested {len(chunks)} chunks → '{self.collection}' (dim={dim})")
        return {"chunks": len(chunks), "collection": self.collection, "source": source}

    def ask(
        self,
        question: str,
        top_k: int = None,
        filter_meta: dict = None,
        system_prompt: str = None,
        timeout: int = 120,
    ) -> dict:
        """
        Step ④⑤ — Search → retrieve context → generate answer with LLM.

        Returns {"answer": str, "sources": [list of matched chunks]}.
        """
        # ④ Similarity search
        hits = self.search(question, top_k=top_k, filter_meta=filter_meta)
        context = "\n\n---\n\n".join(h["document"] for h in hits) if hits else ""

        if not context:
            return {
                "answer": "Chưa tìm thấy tài liệu phù hợp. Vui lòng yêu cầu giáo viên tải tài liệu lên lớp học trước.",
                "sources": [],
            }

        # ⑤ LLM
        messages = self._build_messages(question, context, system_prompt)
        answer = AIClient.chat_sync(messages, timeout=timeout)

        return {
            "answer": answer,
            "sources": self._deduplicate_sources(hits),
        }

    def ask_stream(
        self,
        question: str,
        top_k: int = None,
        filter_meta: dict = None,
        system_prompt: str = None,
        timeout: int = 300,
    ) -> Generator[Union[str, tuple], None, None]:
        """
        Streaming version of ask(). Yields text chunks from the LLM.
        Final yield: ('__SOURCES__', [list of matched chunks])
        On error:    ('__ERROR__', message)
        """
        # ④ Similarity search
        hits = self.search(question, top_k=top_k, filter_meta=filter_meta)
        context = "\n\n---\n\n".join(h["document"] for h in hits) if hits else ""

        if not context:
            yield ("__ERROR__", "Chưa tìm thấy tài liệu phù hợp. Vui lòng yêu cầu giáo viên tải tài liệu lên lớp học trước.")
            return

        # ⑤ LLM (streaming)
        messages = self._build_messages(question, context, system_prompt)
        for chunk in AIClient.chat_stream(messages, timeout=timeout):
            if isinstance(chunk, tuple):
                signal, _ = chunk
                if signal == "__FULL__":
                    yield ("__SOURCES__", self._deduplicate_sources(hits))
                else:
                    yield chunk
                return
            yield chunk

    def delete_document(self, filter_meta: dict) -> int:
        """Delete all chunks matching metadata filter. Returns count deleted."""
        store = self._get_store()
        return store.delete_where(filter_meta)
