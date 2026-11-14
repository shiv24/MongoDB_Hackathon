"""Settings and constants. Stack: MongoDB Atlas + partner resources (ElevenLabs, Voyage AI, LangSmith)."""
import os

from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI", "")
MONGODB_DB = os.environ.get("MONGODB_DB", "promptforge")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev")

# Voyage AI: embeddings + reranking
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "voyage-3.5")
EMBED_DIMS = int(os.environ.get("EMBED_DIMS", "1024"))
RERANK_MODEL = os.environ.get("RERANK_MODEL", "rerank-2.5")

# ElevenLabs Agents: the conversational agent and the only LLM in the stack
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "")
ELEVENLABS_AGENT_LLM = os.environ.get("ELEVENLABS_AGENT_LLM", "claude-sonnet-5-5")  # runs inside ElevenLabs, on ElevenLabs credits
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")  # public https URL ElevenLabs can reach (tunnel)
AGENT_TOOL_SECRET = os.environ.get("AGENT_TOOL_SECRET", "")  # shared header value sent on every agent tool call
AGENT_SESSION_HOURS = 2

# LangSmith tracing is enabled by LANGSMITH_TRACING=true + LANGSMITH_API_KEY (read by the langsmith SDK)

# Scopes, roles and statuses (see docs/DESIGN.md "Data model")
LESSON_SCOPES = ("personal", "project", "team")
LESSON_STATUSES = ("proposed", "approved", "rejected", "superseded", "retired", "expired")
DECISION_STATUSES = ("current", "superseded")
TEAM_PUBLISH_ROLES = ("publisher", "admin")

# Retrieval
RETRIEVE_LIMIT = 6               # per record type (source chunks, decisions, lessons)
NUM_CANDIDATES = 100
CHUNK_CHARS = 1200               # source chunk size

# Learning
DUPLICATE_SCORE = 0.92           # vectorSearchScore (cosine, normalised 0..1) at or above -> duplicate
EXPIRY_DAYS = 30                 # approved lesson not cited this long -> expired by the sweep
PURGE_GRACE_DAYS = 7             # TTL index on purge_at = expires_at + this
