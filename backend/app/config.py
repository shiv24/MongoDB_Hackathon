"""Settings and constants. Keep tunables here, not inline."""
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
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_STT_MODEL = os.environ.get("ELEVENLABS_STT_MODEL", "scribe_v1")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev")

# Scopes and statuses (see docs/DESIGN.md "Data model")
LESSON_SCOPES = ("personal", "project", "team")
LESSON_STATUSES = ("proposed", "approved", "rejected", "superseded", "retired", "expired")
DECISION_STATUSES = ("current", "superseded")

# Retrieval
RETRIEVE_LIMIT = 8               # per record type (source chunks, decisions, lessons)
NUM_CANDIDATES = 100

# Learning
DUPLICATE_SIMILARITY = 0.92      # proposed lesson this close to an approved one -> flag duplicate
EXPIRY_DAYS = 30                 # approved lesson unused this long -> expired by the sweep
PURGE_GRACE_DAYS = 7             # TTL index on purge_at = expires_at + this
