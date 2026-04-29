"""Service-wide configuration. All values come from environment variables
with sensible defaults so the service runs out of the box in docker-compose."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Backend service URLs (resolved by docker DNS) ----------
BOOK_SERVICE_URL          = os.environ.get("BOOK_SERVICE_URL",          "http://book-service:8000")
ORDER_SERVICE_URL         = os.environ.get("ORDER_SERVICE_URL",         "http://order-service:8000")
COMMENT_RATE_SERVICE_URL  = os.environ.get("COMMENT_RATE_SERVICE_URL",  "http://comment-rate-service:8000")
CATALOG_SERVICE_URL       = os.environ.get("CATALOG_SERVICE_URL",       "http://catalog-service:8000")

# ---------- Neo4j ----------
NEO4J_URI       = os.environ.get("NEO4J_URI",       "bolt://neo4j:7687")
NEO4J_USER      = os.environ.get("NEO4J_USER",      "neo4j")
NEO4J_PASSWORD  = os.environ.get("NEO4J_PASSWORD",  "bookstore-secret")

# ---------- LSTM ----------
LSTM_WEIGHTS_PATH = DATA_DIR / "lstm_weights.pt"
LSTM_HIDDEN_DIM   = int(os.environ.get("LSTM_HIDDEN_DIM",   "64"))
LSTM_SEQ_LENGTH   = int(os.environ.get("LSTM_SEQ_LENGTH",   "5"))
LSTM_EPOCHS       = int(os.environ.get("LSTM_EPOCHS",       "30"))
LSTM_LR           = float(os.environ.get("LSTM_LR",         "0.01"))
LSTM_TRAIN_AT_STARTUP = os.environ.get("LSTM_TRAIN_AT_STARTUP", "true").lower() == "true"

# ---------- FAISS RAG ----------
EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIM        = int(os.environ.get("EMBED_DIM",    "384"))

# ---------- Hybrid scoring weights (must sum ~1.0) ----------
W_LSTM   = float(os.environ.get("W_LSTM",   "0.4"))
W_GRAPH  = float(os.environ.get("W_GRAPH",  "0.4"))
W_RAG    = float(os.environ.get("W_RAG",    "0.2"))

# ---------- LLM (optional — chatbot falls back to template if missing) ----------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.environ.get("OPENAI_MODEL",   "gpt-4o-mini")

# ---------- Bootstrap behaviour ----------
SEED_GRAPH_AT_STARTUP = os.environ.get("SEED_GRAPH_AT_STARTUP", "true").lower() == "true"
BUILD_FAISS_AT_STARTUP = os.environ.get("BUILD_FAISS_AT_STARTUP", "true").lower() == "true"
