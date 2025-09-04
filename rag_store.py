"""
RAG Store: ChromaDB + LlamaIndex integration for local vector search over emails/quotes.
- Persists ChromaDB locally in ./rag_test_db (default) or a provided path.
- Uses sentence-transformers (all-MiniLM-L6-v2) for local embeddings (no external calls).
- Exposes a simple API:
    * add_document(email_text: str, metadata: dict) -> str  (returns document ID)
    * query_context(query_text: str, top_k: int = 3) -> list[dict]
    * ingest_email(email_text: str, metadata: dict) -> str   (alias for add_document)
    * retrieve_similar(query_text: str, top_k: int = 3) -> list[dict] (alias)

Notes:
- This module is self-contained and safe for local use only.
- It prepares a clean interface for future integration with email ingestion modules.
"""
from __future__ import annotations

import os
from typing import List, Dict, Any
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings

from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore


class RagStore:
    """Encapsula a gestão do ChromaDB + LlamaIndex para RAG local."""

    def __init__(
        self,
        persist_path: str = "./rag_test_db",
        collection_name: str = "emails_cotacoes",
        embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        # Garante diretório para persistência
        os.makedirs(persist_path, exist_ok=True)
        self.persist_path = persist_path
        self.collection_name = collection_name

        # Inicializa ChromaDB persistente (local)
        self._chroma_client = chromadb.PersistentClient(
            path=self.persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._chroma_collection = self._chroma_client.get_or_create_collection(
            name=self.collection_name
        )

        # Evita backend MPS (Metal) no macOS em processos forkados do RQ
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

        # Embeddings locais via HuggingFace (sem serviços externos) em CPU
        self._embed_model = HuggingFaceEmbedding(model_name=embed_model_name, device="cpu")
        # Define embedder no Settings global do LlamaIndex e desativa LLM (não usamos LLM aqui)
        Settings.embed_model = self._embed_model
        Settings.llm = None

        # Vector store e contexts
        self._vector_store = ChromaVectorStore(chroma_collection=self._chroma_collection)
        self._storage_context = StorageContext.from_defaults(vector_store=self._vector_store)

        # Cria o índice baseado no vector store existente (não reingere dados)
        self._index = VectorStoreIndex.from_vector_store(
            vector_store=self._vector_store,
            storage_context=self._storage_context,
        )

    # -------------------------
    # Public API
    # -------------------------
    def add_document(self, email_text: str, metadata: Dict[str, Any]) -> str:
        """
        Adiciona um documento ao índice/ChromaDB.
        Retorna o ID do documento.
        """
        if not isinstance(email_text, str) or not email_text.strip():
            raise ValueError("email_text deve ser uma string não vazia")
        if not isinstance(metadata, dict):
            raise ValueError("metadata deve ser um dict")

        # Gera um ID estável para o documento e retorna este ID, já que insert() pode não retornar
        doc_id = metadata.get("id") or str(uuid4())
        doc = Document(text=email_text, metadata=metadata, doc_id=doc_id)
        # Insere no índice (irá persistir no Chroma via vector store)
        self._index.insert(doc)
        return doc_id

    def query_context(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Consulta o índice por exemplos semelhantes. Retorna uma lista de entradas:
        [{ 'text': str, 'score': float | None, 'metadata': dict }]
        """
        if not isinstance(query_text, str) or not query_text.strip():
            raise ValueError("query_text deve ser uma string não vazia")
        if top_k <= 0:
            raise ValueError("top_k deve ser > 0")

        # Cria query engine SEM LLM (apenas similaridade por embeddings)
        qe = self._index.as_query_engine(similarity_top_k=top_k)
        resp = qe.query(query_text)

        results: List[Dict[str, Any]] = []
        # source_nodes contém nodes com .text, .score e .metadata
        for sn in getattr(resp, "source_nodes", []) or []:
            results.append(
                {
                    "text": sn.text,
                    "score": getattr(sn, "score", None),
                    "metadata": getattr(sn, "metadata", {}) or {},
                }
            )
        return results

    # Aliases semânticos para futura integração com módulos de e-mail
    def ingest_email(self, email_text: str, metadata: Dict[str, Any]) -> str:
        return self.add_document(email_text, metadata)

    def retrieve_similar(self, query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self.query_context(query_text, top_k)


# Helpers modulares (funções de nível de módulo) se preferir evitar estado de classe fora
_default_store: RagStore | None = None


def get_default_store() -> RagStore:
    global _default_store
    if _default_store is None:
        _default_store = RagStore()
    return _default_store


def add_document(email_text: str, metadata: Dict[str, Any]) -> str:
    return get_default_store().add_document(email_text, metadata)


def query_context(query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    return get_default_store().query_context(query_text, top_k)


# Aliases solicitados
ingest_email = add_document
retrieve_similar = query_context
