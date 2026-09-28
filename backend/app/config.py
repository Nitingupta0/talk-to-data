"""Runtime configuration, read once from the environment (and an optional .env file)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Load .env from the repo root first, then backend/ (backend wins).
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
LLM_MODEL = os.getenv("TTD_MODEL", "llama-3.3-70b-versatile")

STORAGE_DIR = Path(os.getenv("TTD_STORAGE_DIR", BACKEND_DIR / "storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
DB_PATH = STORAGE_DIR / "talk_to_data.db"
SAMPLE_DIR = BACKEND_DIR / "sample_data"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

MAX_UPLOAD_MB = int(os.getenv("TTD_MAX_UPLOAD_MB", "50"))
EXEC_TIMEOUT_S = float(os.getenv("TTD_EXEC_TIMEOUT_S", "15"))
MAX_REPAIR_ATTEMPTS = int(os.getenv("TTD_MAX_REPAIR_ATTEMPTS", "2"))
MAX_RESULT_ROWS = 500

CORS_ORIGINS = [o.strip() for o in os.getenv("TTD_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
