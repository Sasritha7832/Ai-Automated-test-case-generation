from document_processor import process_prd_document
from vector_store import VectorStoreManager
from logger import get_logger

logger = get_logger(__name__)

class RAGPipeline:
    """End-to-End RAG Pipeline for test case generation context extraction."""
    def __init__(self):
        self.vector_manager = VectorStoreManager()
        self._documents = []   # store the processed Document list for requirement extraction

    @property
    def vector_store(self):
        """Alias for vector_manager for backward compatibility."""
        return self.vector_manager

    @vector_store.setter
    def vector_store(self, value):
        self.vector_manager = value

    def process_and_store(self, uploaded_file):
        """Processes a PDF file and builds the vector database."""
        try:
            logger.info("RAGPipeline processing uploaded file...")
            documents = process_prd_document(uploaded_file)
            self._documents = documents          # cache for later retrieval
            self.vector_manager.create_vectorstore(documents)
            logger.info(f"RAG vectorization complete. {len(documents)} documents stored.")
            return True
        except Exception as e:
            logger.error("Failed to complete RAG processing.", exc_info=True)
            return False

    def get_documents(self):
        """Return the processed Document objects (with requirement metadata)."""
        return self._documents

    def retrieve_feature_context(self, feature: str) -> str:
        """Retrieves context specific to a feature requested by the user."""
        try:
            return self.vector_manager.retrieve_context(feature)
        except Exception as e:
            logger.error(f"Failed retrieving RAG context for feature: {feature}", exc_info=True)
            return ""

