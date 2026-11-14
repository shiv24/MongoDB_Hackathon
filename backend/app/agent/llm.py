"""Claude client. Structured calls use messages.parse; long HTML generation streams."""
import anthropic

from app import config

FALLBACK_BETA = "server-side-fallback-2026-07-01"
_client = None


class ModelRefused(RuntimeError):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY (or an `ant auth login` profile)
    return _client


def _check(resp) -> None:
    if resp.stop_reason == "refusal":
        detail = getattr(resp, "stop_details", None)
        raise ModelRefused(f"model declined ({getattr(detail, 'category', None)})")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("model output hit max_tokens; response truncated")


def parse(system: str, user: str, schema, effort: str = "medium", max_tokens: int = 16000):
    """Return (parsed pydantic object, model that served it)."""
    resp = client().beta.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",  # server-side refusal fallback
    )
    _check(resp)
    return resp.parsed_output, resp.model


def generate_text(system: str, user: str, effort: str = "medium", max_tokens: int = 64000) -> tuple[str, str]:
    """Streamed free-text generation. Returns (text, model that served it)."""
    with client().beta.messages.stream(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort},
        betas=[FALLBACK_BETA],
        fallbacks="default",
    ) as stream:
        resp = stream.get_final_message()
    _check(resp)
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.model
