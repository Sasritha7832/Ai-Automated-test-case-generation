"""
rag_retriever.py
----------------
Thin wrapper around VectorStoreManager for standalone RAG retrieval.
Used by the QA Chatbot and any module that needs direct top-k retrieval
without instantiating the full RAGPipeline.
"""

from vector_store import VectorStoreManager
from config import Config
from logger import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """
    Standalone RAG retriever.
    Wraps VectorStoreManager.retrieve_context with a default top_k=10
    matching the specification requirement.
    """

    def __init__(self, vector_store_manager: VectorStoreManager = None):
        self.vector_store = vector_store_manager or VectorStoreManager()
        logger.info("RAGRetriever initialized (top_k=%d by default).", Config.TOP_K_RETRIEVAL)

    def retrieve(self, query: str, k: int = None) -> str:
        """
        Retrieve top-k relevant chunks from the FAISS vector store.

        Args:
            query: Natural-language query string.
            k: Number of chunks to retrieve (defaults to Config.TOP_K_RETRIEVAL = 10).

        Returns:
            Concatenated context string from top-k chunks.
        """
        k = k or Config.TOP_K_RETRIEVAL
        try:
            context = self.vector_store.retrieve_context(query, k=k)
            logger.info("RAGRetriever.retrieve: returned %d chars for query '%s'.", len(context), query[:60])
            return context
        except Exception as e:
            logger.error("RAGRetriever.retrieve error: %s", e, exc_info=True)
            return ""

    def get_all_texts(self) -> list:
        """Returns all stored document texts from the underlying FAISS docstore."""
        return self.vector_store.get_all_texts()