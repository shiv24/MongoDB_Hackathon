"""Settings and tunable constants (see skills/memory-loop)."""
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DB = os.environ.get("MONGODB_DB", "promptforge")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "")
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "voyage-3")
EMBED_DIMS = int(os.environ.get("EMBED_DIMS", "1024"))
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev")

# Retrieval
RETRIEVE_LIMIT = 8
RERANK_SIM_WEIGHT = 0.6
RERANK_SCORE_WEIGHT = 0.4

# Condense
CONDENSE_MAX_WORDS = 150

# Lifecycle
DEMOTE_SCORE, DEMOTE_MIN_VOTES = 0.35, 4
RETIRE_SCORE, RETIRE_MIN_VOTES = 0.2, 6
EXPIRY_DAYS = 30
DEDUPE_SIMILARITY = 0.92
