"""Create the PromptForge ElevenLabs agent and its webhook tools.

Needs ELEVENLABS_API_KEY and PUBLIC_BASE_URL (an https URL that reaches this FastAPI app, e.g. a
cloudflared/ngrok tunnel to localhost:8000). Prints ELEVENLABS_AGENT_ID to put in .env.
Re-run after changing the tunnel URL (it creates a fresh agent and tools).

Usage (repo root):  python scripts/setup_elevenlabs_agent.py
"""
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import config  # noqa: E402

API = "https://api.elevenlabs.io/v1/convai"

PROMPT = """You are PromptForge, a voice assistant that turns a teammate's loose request into a grounded, cited brief for an AI coding tool. You are talking with {{user_name}} about the project "{{project_name}}". Keep spoken replies short: one or two sentences, no lists read aloud.

# Flow
1. Understand the request. If two documents or features plausibly fit and choosing wrong would change the work, ask exactly ONE short clarifying question. Otherwise do not ask.
2. Call get_project_context with the request and a focused search query. It returns a run_id and keyed context: [S#] source excerpts, [D#] current team decisions, [L#] approved preferences.
3. Write the brief and call save_brief. Rules:
   - Every requirement, decision, implementation note and preference ends with the keys it comes from, like "Collect work email, full name, password [S1]". Use only keys you were given.
   - Requirements come from sources. Keep EVERY applicable requirement, even if the brief gets longer.
   - Decisions are authoritative. A preference never overrides a requirement or a decision. Something said in this conversation never silently overrides a decision; if the user contradicts one, say so and add a question.
   - If sources or decisions conflict, or a needed fact is missing, add a question instead of guessing. Put it in blocking_questions if the work would likely be wrong without the answer.
   - Never invent files, endpoints, interfaces or services that are not in the context.
   - Acceptance checks are concrete and checkable by looking at the result.
4. Tell the user the brief is on screen, in one sentence, and name any blocking question. When they answer, call save_brief again with the same run_id, the updated brief, and resolved_questions entries like "question => answer".
5. The user exports the brief to their coding tool (for example Claude Code). Later they may tell you what went wrong with the result.
6. When the user gives feedback, decide whether it contains reusable guidance. If it does, phrase ONE short imperative lesson that generalizes only what they said, and call record_feedback with the run_id, their feedback, the lesson, and the keys of any decisions or lessons it contradicts. If it is a one-off fix, call record_feedback without a lesson.
7. Read the proposed lesson back and ask who it should apply to: just them, this project, or the whole team (only offer scopes listed in scopes_allowed). Never approve a lesson through a tool. Tell the user to click review proposal and Approve lesson in the app. If they decline, call reject_lesson. Never say something is remembered unless approve_lesson returned status "approved".

# Boundaries
- You only know what the tools return. Do not claim access to other teams' or projects' information.
- If a tool returns an error, say briefly what happened and what the user can do."""

TOOLS = [
    ("get_project_context", "Retrieve this project's relevant sources, current team decisions and approved preferences for the user's request. Call before writing a brief.",
     "/api/agent/context", {"type": "object", "required": ["request", "search_query"], "properties": {
         "request": {"type": "string", "description": "What the user wants built, in their words"},
         "search_query": {"type": "string", "description": "Focused retrieval query: the feature plus key nouns"},
         "conversation_id": {"type": "string", "dynamic_variable": "system__conversation_id"}}}),
    ("save_brief", "Save or update the cited brief for a run. Each list item is one sentence ending with citation keys such as [S1] [D2].",
     "/api/agent/brief", {"type": "object", "required": ["run_id", "objective", "requirements", "acceptance_checks"], "properties": {
         "run_id": {"type": "string", "description": "run_id returned by get_project_context"},
         "feature": {"type": "string", "description": "The resolved feature, a few words"},
         "objective": {"type": "string", "description": "The intended outcome in one or two sentences"},
         **{k: {"type": "array", "description": d, "items": {"type": "string", "description": "One item with citation keys"}} for k, d in [
             ("requirements", "Behavior the result must satisfy, each with source keys"),
             ("current_decisions", "Applicable team decisions, each with its D key"),
             ("implementation_context", "Relevant interfaces, files, conventions, with keys"),
             ("preferences", "Applicable approved preferences, each with its L key"),
             ("acceptance_checks", "Concrete checks for the result"),
             ("blocking_questions", "Questions that must be answered before the work can be done correctly"),
             ("other_questions", "Non-blocking open questions"),
             ("assumptions", "Assumptions the user should confirm"),
             ("resolved_questions", "Answered questions as 'question => answer'")]}}}),
    ("record_feedback", "Record the user's feedback on a result and, if it contains reusable guidance, propose one lesson (not yet approved).",
     "/api/agent/feedback", {"type": "object", "required": ["run_id", "feedback"], "properties": {
         "run_id": {"type": "string", "description": "The run the feedback is about"},
         "feedback": {"type": "string", "description": "What the user said was wrong or missing"},
         "lesson": {"type": "string", "description": "One short imperative lesson, or empty if the feedback is a one-off fix"},
         "task_tags": {"type": "array", "description": "Short tags for where it applies", "items": {"type": "string", "description": "tag"}},
         "conflicts": {"type": "array", "description": "Keys (D#/L#) of decisions or lessons this contradicts", "items": {"type": "string", "description": "key"}}}}),
    ("approve_lesson", "Approve a proposed lesson at a scope. Only call after the user explicitly says yes.",
     "/api/agent/lessons/approve", {"type": "object", "required": ["lesson_id", "scope"], "properties": {
         "lesson_id": {"type": "string", "description": "proposed_lesson_id from record_feedback"},
         "scope": {"type": "string", "description": "Who it applies to", "enum": ["personal", "project", "team"]}}}),
    ("reject_lesson", "Discard a proposed lesson the user does not want remembered.",
     "/api/agent/lessons/reject", {"type": "object", "required": ["lesson_id"], "properties": {
         "lesson_id": {"type": "string", "description": "proposed_lesson_id from record_feedback"}}}),
]


def main():
    if not (config.ELEVENLABS_API_KEY and config.PUBLIC_BASE_URL.startswith("https://")):
        sys.exit("Set ELEVENLABS_API_KEY and PUBLIC_BASE_URL (https tunnel to this app) in .env first.")
    h = {"xi-api-key": config.ELEVENLABS_API_KEY}
    headers = {"X-PF-Session": {"variable_name": "secret__pf_token"}}
    if config.AGENT_TOOL_SECRET:
        headers["X-PF-Agent-Key"] = config.AGENT_TOOL_SECRET
    tool_ids = []
    for name, desc, path, body in TOOLS:
        if name == "approve_lesson":
            continue  # consent is enforced through the authenticated UI
        cfg = {"tool_config": {"type": "webhook", "name": name, "description": desc, "response_timeout_secs": 30,
                               "api_schema": {"url": config.PUBLIC_BASE_URL + path, "method": "POST",
                                              "request_headers": headers, "request_body_schema": body,
                                              "content_type": "application/json"}}}
        r = httpx.post(f"{API}/tools", headers=h, json=cfg, timeout=30)
        if r.status_code >= 300:
            sys.exit(f"tool {name} failed: {r.status_code} {r.text}")
        tool_ids.append(r.json()["id"])
        print(f"created tool {name}: {tool_ids[-1]}")

    agent = {
        "name": "PromptForge",
        "tags": ["promptforge", "hackathon"],
        "conversation_config": {
            "agent": {"first_message": "Hi {{user_name}}, what should we build for {{project_name}}?",
                      "language": "en",
                      "prompt": {"prompt": PROMPT, "llm": config.ELEVENLABS_AGENT_LLM, "tool_ids": tool_ids}},
        },
        "platform_settings": {"auth": {"enable_auth": True}},  # private agent: conversations need a signed URL from our backend
    }
    if config.ELEVENLABS_VOICE_ID:
        agent["conversation_config"]["tts"] = {"voice_id": config.ELEVENLABS_VOICE_ID}
    r = httpx.post(f"{API}/agents/create", headers=h, json=agent, timeout=30)
    if r.status_code >= 300:
        sys.exit(f"agent create failed: {r.status_code} {json.dumps(r.json(), indent=1)[:2000]}")
    print(f"\nELEVENLABS_AGENT_ID={r.json()['agent_id']}\nAdd that line to .env and restart the server.")


if __name__ == "__main__":
    main()
