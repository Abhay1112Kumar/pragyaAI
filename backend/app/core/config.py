from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
MEMORY_DIR = DATA_DIR / "memory"
CONVERSATION_DATABASE_PATH = MEMORY_DIR / "conversations.sqlite3"
SEMANTIC_CACHE_DATABASE_PATH = MEMORY_DIR / "semantic_cache.sqlite3"
AUTH_DATABASE_PATH = MEMORY_DIR / "users.sqlite3"
METRICS_DATABASE_PATH = MEMORY_DIR / "metrics.sqlite3"

ALLOWED_FILE_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024

EMBEDDING_MODEL = "nomic-embed-text"
CHROMA_COLLECTION_NAME = "pragya_documents"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_RETRIEVAL_COUNT = 4
HYBRID_CANDIDATE_MULTIPLIER = 3
HYBRID_RRF_K = 60

SEMANTIC_CACHE_THRESHOLD = 0.92
SEMANTIC_CACHE_TTL_DAYS = 7
SEMANTIC_CACHE_MAX_ENTRIES = 500

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
