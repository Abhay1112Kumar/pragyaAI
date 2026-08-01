from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"

ALLOWED_FILE_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024

EMBEDDING_MODEL = "nomic-embed-text"
CHROMA_COLLECTION_NAME = "pragya_documents"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_RETRIEVAL_COUNT = 4

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)