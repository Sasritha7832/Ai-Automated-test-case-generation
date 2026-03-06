"""
embedding_singleton.py
-----------------------
Shared SentenceTransformer model singleton.

Loads the embedding model ONCE and provides it to all modules
(DeduplicationEngine, CoverageAnalyzer, ImpactAnalyzer).
Section 3 fix: explicit SentenceTransformer import to prevent 'not defined' errors.
"""

# Section 3: Explicit import — fixes 'SentenceTransformer is not defined' errors
from sentence_transformers import SentenceTransformer
from config import Config
from logger import get_logger

logger = get_logger("EmbeddingSingleton")

_model_instance = None


def get_embedding_model() -> SentenceTransformer:
    """
    Returns the shared SentenceTransformer instance, loading it once.
    Thread-safe for Streamlit's single-threaded execution model.
    """
    global _model_instance
    if _model_instance is None:
        logger.info(f"Loading embedding model (once): {Config.EMBEDDING_MODEL}")
        try:
            _model_instance = SentenceTransformer(Config.EMBEDDING_MODEL)
            logger.info("Embedding model loaded and cached.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer '{Config.EMBEDDING_MODEL}': {e}")
            raise RuntimeError(
                f"Cannot load embedding model '{Config.EMBEDDING_MODEL}'. "
                "Run: pip install sentence-transformers"
            ) from e
    return _model_instance
