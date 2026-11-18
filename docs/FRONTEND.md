# Frontend guide

PromptForge's browser interface turns a short request into a grounded prompt and an interactive website prototype. It also lets users explicitly approve feedback as reusable memory and compare a rebuild with an earlier result.

## Run and edit

Start FastAPI from the repository root after following the [setup instructions](../README.md#run-locally):

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload --app-dir backend
```

Open http://localhost:8000. FastAPI serves the UI at `/`, API endpoints under `/api`, and API documentation at `/docs`. There is no npm install, bundler, or separate frontend development server. Refresh the browser after changing frontend files. If the port is occupied, add `--port 8001` and use that port in the browser.

| File | Responsibility |
| --- | --- |
| `frontend/index.html` | Request, preview, prompt editor, feedback, context sidebar, and dialogs |
| `frontend/styles.css` | Layout, colors, responsive rules, and progress indicators |
| `frontend/app.js` | Session selection, API calls, in-memory state, rendering, and event handlers |
| `frontend/preview.mjs` | Preview document helper that tolerates blocked History API URL updates |
| `frontend/tests/preview.test.mjs` | Node tests for preview document and History API bridge behavior |

Preserve element IDs when restyling: JavaScript attaches handlers and renders into those elements. The app loads JavaScript as a browser module.

## Current workflow

1. The app logs into the simulated Alice session (`console-alice`) and loads the Admin console project. The header can switch to Bob (`console-bob`). Both identities are fixtures, not secure authentication.
2. The user types a request or uses **Record request**. Microphone dictation sends audio to the backend; ElevenLabs credentials stay server-side. Users can edit the transcript before submission.
3. **Build preview** sends the request to `POST /api/build`. The backend retrieves context and returns a cited brief. The frontend then requests `POST /api/build/{id}/preview` to generate the artifact.
4. The preview appears first. **View the prompt and what shaped it** exposes citations, context contributions, editable instructions, copying, and Markdown download.
5. **Save feedback & rebuild** saves the user's exact feedback as a lesson, explicitly approves it at the chosen scope, and rebuilds the same request with that lesson selected. This button changes persistent memory. The separate suggestion flow prepares wording for review before approval.
6. The app keeps the previous run as a baseline and can open **Compare before & after**. An approved lesson's presence in a prompt is evidence of its use; unrelated layout differences are not proof that memory caused them.

**Start fresh demo** creates an isolated sample team/project and loads a saved starting preview. It requires `python scripts/prepare_demo.py` first. Feedback generates the after-result live. **Team workspace** returns to the original shared workspace without deleting prior demo rounds. See [DEMO.md](../DEMO.md).

## State and API boundaries

The `state` object tracks the current user, project, context, run, baseline, and pending tasks. Event handlers call the shared `api()` helper, update state, then render the affected sections. Session cookies accompany same-origin requests.

| Interaction | Endpoint |
| --- | --- |
| Log in / leave session | `POST /api/login`, `POST /api/logout` |
| Load projects and context | `GET /api/projects`, `GET /api/projects/{id}/context` |
| Create prompt / preview | `POST /api/build`, `POST /api/build/{id}/preview` |
| Reopen a run | `GET /api/runs/{id}` |
| Save prompt / export Markdown | `PATCH /api/runs/{id}/brief`, `GET /api/runs/{id}/export` |
| Feedback and approval | `POST /api/runs/{id}/feedback`, `POST /api/lessons/{id}/approve` |
| Add a source | `POST /api/projects/{id}/sources` or `/sources/file` |
| Dictate audio | `POST /api/voice/transcribe` |
| Start isolated demo | `POST /api/demo/start` |

Run links use `#run=<id>`; comparisons can also include `&before=<id>`. These identify database records, not portable exported examples. The backend restricts run reads to their owner. Switching users does not grant access to another user's run link.

The backend owns identity, membership, scope, citation checks, model calls, and persistence. Hiding a control in the browser does not enforce permissions. Never place provider keys or MongoDB credentials in frontend files.

## Preview behavior and errors

Server-provided text is inserted with DOM text nodes or `textContent`. Generated HTML is handled separately in sandboxed iframes. Inline scripts can support interactions over sample data, but previews have an opaque origin and a content security policy blocking network calls, external assets, and form submission. A generated login or search form is a prototype, not a connected backend service.

Build and generation are separate operations. A prompt can succeed while the preview fails; use the displayed retry control. A stale-context conflict requires refreshing or rebuilding with current context. Progress messages indicate an outstanding request, not guaranteed completion time. If saving feedback succeeds but rebuilding fails, the lesson remains saved; the UI reports that distinction.

## Checks and debugging

```bash
node --check frontend/app.js
node --test frontend/tests/preview.test.mjs
```

These checks do not exercise the complete browser workflow. Manually check request → preview → prompt inspection → feedback → approval/rebuild → comparison, and then test session switching and source visibility.

Use browser developer tools: Console for JavaScript errors, Network for `/api` responses, and Elements for styling. The backend terminal contains server errors. A failed startup may indicate Atlas connectivity; a loaded page with failed API calls may indicate session, permissions, credentials, or provider access. Use `python scripts/doctor.py` for redacted configuration checks.
