import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Cloud LLM (Fastest) ──────────────────────────
    GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL         = os.getenv("GROQ_MODEL", "llama3-8b-8192")

    # ── Local LLM Settings (Ollama) ──────────────────
    PRIMARY_LLM_MODEL  = os.getenv("PRIMARY_LLM_MODEL",  "llama3:8b")
    FALLBACK_LLM_MODEL = os.getenv("FALLBACK_LLM_MODEL", "gemma3:4b")
    # Legacy alias used by qa_planner / qa_chatbot
    OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL", FALLBACK_LLM_MODEL)
    OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", 0.25))

    # RAG Settings
    CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE",      800))
    CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP",   100))
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 4))   # reduced for speed

    # Module detection safeguard (Section 6)
    MAX_MODULES = int(os.getenv("MAX_MODULES", 6))

    # Coverage threshold — requirement considered "covered" above this cosine sim
    COVERAGE_THRESHOLD = float(os.getenv("COVERAGE_THRESHOLD", 0.35))

    # Paths
    DATASET_DIR    = "dataset"
    MODELS_DIR     = "models"
    ML_MODEL_PATH  = os.path.join(MODELS_DIR, "random_forest_model.pkl")
    DATASET_PATH   = os.path.join(DATASET_DIR, "requirements_dataset.csv")

    @staticmethod
    def setup_directories():
        os.makedirs(Config.DATASET_DIR, exist_ok=True)
        os.makedirs(Config.MODELS_DIR, exist_ok=True)

# Initialize dirs
Config.setup_directories()
