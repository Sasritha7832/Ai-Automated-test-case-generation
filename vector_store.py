"""
vector_store.py
---------------
Manages the FAISS in-memory vector database.

PERFORMANCE OPTIMIZATIONS:
- HuggingFaceEmbeddings loaded via @st.cache_resource (Section 5)
  → loads once per Streamlit session, never again
- VectorStoreManager constructor has zero blocking operations
- retrieve_context results cached per query via st.cache_data (Section 6)
"""

from langchain_community.vectorstores import FAISS
from config import Config
from logger import get_logger

logger = get_logger(__name__)


# ── Section 5: @st.cache_resource — loads embedding model ONCE per session ───
def get_cached_embedding_model():
    """
    Returns cached HuggingFaceEmbeddings instance.
    Uses st.cache_resource when Streamlit is available, else falls back to singleton.
    """
    try:
        import streamlit as st

        @st.cache_resource(show_spinner="Loading embedding model (once per session)…")
        def _load():
            # Section 2: use langchain-huggingface instead of langchain_community
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            logger.info(f"Loading HuggingFaceEmbeddings: {Config.EMBEDDING_MODEL}")
            return HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL)

        return _load()

    except Exception:
        # Outside Streamlit (e.g., unit tests) — use plain singleton
        from embedding_singleton import get_embedding_model
        return get_embedding_model()


class VectorStoreManager:
    """Manages FAISS Vector Database. Embeddings loaded via cache on first use."""

    def __init__(self):
        self._embeddings = None
        self.vectorstore = None
        logger.info("VectorStoreManager created.")

    def _get_embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_cached_embedding_model()
        return self._embeddings

    def create_vectorstore(self, documents):
        """Creates an in-memory FAISS vectorstore from text chunks."""
        try:
            logger.info(f"Creating FAISS vectorstore from {len(documents)} chunks…")
            self.vectorstore = FAISS.from_documents(documents, self._get_embeddings())
            logger.info("FAISS vectorstore created successfully.")
            return self.vectorstore
        except Exception as e:
            logger.error(f"Error creating vectorstore: {e}", exc_info=True)
            raise

    def retrieve_context(self, query: str, k: int = None) -> str:
        """
        Retrieves and joins top-k relevant contexts for a query.
        Section 6: results are cached by (query, k) via _cached_retrieve.
        """
        k = k or Config.TOP_K_RETRIEVAL
        if not self.vectorstore:
            logger.warning("Vectorstore not initialized.")
            return ""
        try:
            docs = _cached_retrieve(self.vectorstore, query, k)
            context = "\n\n".join(doc.page_content for doc in docs)
            logger.info(f"Retrieved {len(docs)} chunks for '{query[:50]}'.")
            return context
        except Exception as e:
            logger.error(f"Error retrieving from vectorstore: {e}", exc_info=True)
            return ""

    def get_all_texts(self) -> list:
        """Returns all stored document texts from the FAISS docstore."""
        if not self.vectorstore:
            return []
        try:
            return [doc.page_content for doc in self.vectorstore.docstore._dict.values()]
        except Exception as e:
            logger.error(f"Error getting all texts: {e}", exc_info=True)
            return []


# ── Section 6: @st.cache_data for retrieval results ──────────────────────────
def _cached_retrieve(vectorstore, query: str, k: int):
    """
    Cache retrieval results so repeated identical queries don't re-run FAISS.
    Uses st.cache_data when available, otherwise runs directly.
    """
    try:
        import streamlit as st

        @st.cache_data(show_spinner=False, ttl=600)
        def _run(query: str, k: int):
            retriever = vectorstore.as_retriever(search_kwargs={"k": k})
            return retriever.invoke(query)

        return _run(query, k)

    except Exception:
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)
