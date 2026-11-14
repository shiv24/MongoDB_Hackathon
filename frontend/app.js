// PromptForge UI: type or dictate a request -> grounded prompt -> generated artifact.
// Server text is inserted with textContent only.


const $ = (id) => document.getElementById(id);
const DEFAULT_USER_ID = "alice";
const DEFAULT_PROJECT_ID = "lumen-signup";
const state = { me: null, projectId: null, run: null, context: null, recentRuns: [], building: false, previewing: false, feedbackRunId: null,
  previewArtifact: null, feedbackRating: null, feedbackSubmitting: false, feedbackSubmitted: false };

// ---------- helpers ----------
async function api(path, opts = {}) {
  const isFormData = opts.body instanceof FormData;
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !isFormData) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, {
    ...opts, headers, credentials: "same-origin",
    body: opts.body ? (isFormData ? opts.body : JSON.stringify(opts.body)) : undefined,
  });
  const type = res.headers.get("content-type") || "";
  const data = type.includes("json") ? await res.json() : await res.text();
  if (!res.ok) { const err = new Error((data && data.error) || res.statusText); err.status = res.status; err.data = data; throw err; }
  return data;
}

function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) if (c !== null && c !== undefined) n.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return n;
}

function toast(msg) { const t = $("toast"); t.textContent = msg; t.classList.remove("hidden"); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.add("hidden"), 6000); }

async function busy(btn, label, fn) {
  const old = btn.textContent; btn.disabled = true; btn.textContent = label;
  try { return await fn(); } catch (e) { toast(e.message); } finally { btn.disabled = false; btn.textContent = old; }
}

const show = (id, on = true) => $(id).classList.toggle("hidden", !on);
const chip = (text) => el("span", { class: `chip ${text}` }, String(text).replace(/_/g, " "));
const hasSavedArtifact = (run) => !!run?.artifact && run.artifact.brief_revision === run.brief_revision && run.status !== 'stale';

// ---------- fixed demo identity and project ----------
async function init() {
  state.me = await api("/login", { method: "POST", body: { user_id: DEFAULT_USER_ID } });
  const projects = await api("/projects");
  const project = projects.find((p) => p._id === DEFAULT_PROJECT_ID);
  if (!project) throw new Error(`Default project ${DEFAULT_PROJECT_ID} is not available to ${DEFAULT_USER_ID}. Seed the demo data first.`);
  state.projectId = project._id;
  $("active-context").textContent = `${state.me.name} · ${project.name}`;
  const choices = [["personal", "User (Personal)"]];
  if (["publisher", "admin"].includes(state.me.role)) choices.push(["project", "Project"]);
  if (state.me.role === "admin") choices.push(["team", "Company"]);
  $("src-scope").replaceChildren(...choices.map(([value, label]) => el("option", { value }, label)));
  $("src-scope").value = choices.some(([value]) => value === "project") ? "project" : "personal";
  await loadContext();
}

async function openRun(runId) {
  state.run = await api(`/runs/${runId}`);
  $('type-input').value = state.run.request;
  renderRun();
  renderContext();
  renderRecentRuns();
}

// ---------- direct request and optional microphone ----------
let recording = null;
let microphone = null;
async function submitRequest(clarification = '') {
  if (!state.projectId) throw new Error('The default workspace is still loading. Try again in a moment.');
  const request = clarification && state.run ? state.run.request : $('type-input').value.trim();
  if (!request) throw new Error('Describe what you want built.');
  const answers = clarification ? (state.run?.clarification_text || '') + '\n' + clarification : '';
  if (!clarification) {
    state.run = null;
    state.feedbackRunId = null;
    $('brief-details').open = false;
    $('brief').replaceChildren();
    renderRecentRuns();
  }
  state.building = true;
  renderRun();
  try {
    state.run = await api('/build', {method:'POST', body:{project_id:state.projectId, request, clarification:answers}});
    renderRun();
    await loadContext();
    if (state.run.status === 'draft') await generatePreview();
  } finally {
    state.building = false;
    renderRun();
  }
}
function tell(text) { busy($('send-btn'), 'Updating…', () => submitRequest(text)); }
$('send-btn').addEventListener('click', e => busy(e.target, 'Building artifact…', () => submitRequest()));
$('type-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    $('send-btn').click();
  }
});
$('talk-btn').addEventListener('click', async () => {
  try {
    if (recording && recording.state === 'recording') { recording.stop(); return; }
    microphone = await navigator.mediaDevices.getUserMedia({audio:true});
    const parts=[];
    const stream = microphone;
    const recorder = new MediaRecorder(stream);
    recording = recorder;
    recording.ondataavailable = e => parts.push(e.data);
    recording.onstop = async () => {
      stream.getTracks().forEach(t=>t.stop());
      $('talk-btn').querySelector('span').textContent = 'Record';
      $('talk-btn').setAttribute('aria-label', 'Record request');
      try {
        const form=new FormData(); form.append('audio',new Blob(parts,{type:recorder.mimeType}),'request.webm');
        const response=await fetch('/api/voice/transcribe',{method:'POST',body:form});
        const result=await response.json();
        if(!response.ok) throw new Error(result.error || 'Transcription failed');
        $('type-input').value=result.text; toast('Review the transcript, then build the artifact.');
      } catch(e) { toast(e.message); }
    };
    recording.start(); $('talk-btn').querySelector('span').textContent = 'Stop recording';
    $('talk-btn').setAttribute('aria-label', 'Stop recording');
    setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},60000);
  } catch(e) { toast('Microphone unavailable. You can type your request.'); }
});
async function generatePreview() {
  if (!state.run?._id || state.previewing) return;
  state.previewing = true;
  renderRun();
  try {
    state.run = await api(`/build/${state.run._id}/preview`, { method: 'POST' });
  } catch (err) {
    state.run = await api(`/runs/${state.run._id}`);
    toast(`Preview could not be generated: ${err.message}`);
  } finally {
    state.previewing = false;
    renderRun();
    await loadContext();
  }
}

$('generate-btn').addEventListener('click', e => busy(e.target, 'Generating preview…', generatePreview));
$('upgrade-btn').addEventListener('click', e => busy(e.target, 'Rebuilding…', generatePreview));
$('upgrade-inline-btn').addEventListener('click', e => busy(e.target, 'Rebuilding…', generatePreview));

// ---------- project context sidebar ----------
async function loadContext() {
  if (!state.projectId) return;
  state.context = await api(`/projects/${state.projectId}/context`);
  renderContext();
  const candidates = state.context.runs.filter((run) => ['exported', 'reviewed'].includes(run.status)).slice(0, 10);
  state.recentRuns = (await Promise.all(candidates.map(async (run) => {
    try { return await api(`/runs/${run._id}`); }
    catch { return null; }
  }))).filter(Boolean);
  renderRecentRuns();
}

function renderRecentRuns() {
  const runs = state.recentRuns;
  const list = $('recent-runs');
  list.replaceChildren(...runs.filter(hasSavedArtifact)
    .slice(0, 6).map((run) => el('li', {},
      el('button', { class: state.run?._id === run._id ? 'recent-run active' : 'recent-run',
        type: 'button', onclick: (event) => busy(event.currentTarget, 'Opening…', () => openRun(run._id)) },
      el('span', { class: 'recent-run-title' }, run.request),
      el('span', { class: 'recent-run-meta' }, run.artifact.version === 2 ? 'View artifact ↗' : 'Update preview ↗')))));
  if (!list.childElementCount) list.append(el('li', { class: 'muted' }, 'Your builds will appear here.'));
}

function usedIds() {
  const cited = new Set();
  const b = state.run?.brief;
  if (b) for (const s of ["requirements", "current_decisions", "implementation_context", "preferences", "acceptance_checks", "open_questions"])
    for (const i of b[s] || []) for (const k of i.sources || []) cited.add(k);
  return new Set((state.run?.provenance || []).filter((e) => cited.has(e.key)).map((e) => e.id));
}

function renderContext() {
  const c = state.context; if (!c) return;
  const used = usedIds();
  $("sources").replaceChildren(...c.sources.map((s) => el("li", { class: used.has(s.source_id) ? "used" : "" },
    el("span", { class: "text" }, s.title), el("span", { class: "meta" },
      `${s.scope === "team" ? "Company" : s.scope === "personal" ? "Personal" : "Project"} · ${s.kind} · revision ${s.revision} · added by ${s.added_by}`))));
  if (!c.sources.length) $("sources").append(el("li", { class: "muted" }, "No sources yet."));
}

$("src-btn").addEventListener("click", (e) => busy(e.target, "Adding…", async () => {
  const title = $("src-title").value.trim();
  const text = $("src-text").value.trim();
  const file = $("src-file").files[0];
  const sourceScope = $("src-scope").value;
  if (!file && !text) throw new Error("Paste source text or choose a PDF or text file.");
  if (file) {
    const body = new FormData();
    body.append("title", title);
    body.append("text", text);
    body.append("scope", sourceScope);
    body.append("file", file);
    await api(`/projects/${state.projectId}/sources/file`, { method: "POST", body });
  } else {
    await api(`/projects/${state.projectId}/sources`, {
      method: "POST", body: { title: title || "Pasted source", text, scope: sourceScope },
    });
  }
  $("src-title").value = ""; $("src-text").value = ""; $("src-file").value = "";
  await loadContext();
  toast("Source added.");
}));
// ---------- brief ----------
const SECTIONS = [["requirements", "Requirements"], ["current_decisions", "Current decisions"], ["implementation_context", "Implementation context"],
  ["preferences", "Preferences"], ["acceptance_checks", "Acceptance checks"]];

function citeChips(keys) {
  const prov = Object.fromEntries((state.run.provenance || []).map((e) => [e.key, e]));
  return (keys || []).map((k) => {
    const e = prov[k]; if (!e) return null;
    const label = e.type === "user" ? "Your explicit request or clarification" : e.type === "source" ? `${e.scope === "team" ? "Company" : e.scope === "personal" ? "Personal" : "Project"} source "${e.title}" rev ${e.revision}` : e.type === "decision" ? `Team decision rev ${e.revision} (owner ${e.owner_id})` : `Approved ${e.scope} lesson rev ${e.revision}`;
    return el("span", { class: "cite", title: `${label}\n\n${e.text}` }, k);
  });
}

function renderRun() {
  const r = state.run;
  const hasBrief = !!r?.brief;
  show("brief-card", hasBrief);
  const hasPreview = hasSavedArtifact(r);
  const legacyPreview = hasPreview && r.artifact.version !== 2;
  const preview = hasPreview && !legacyPreview ? r.artifact : null;
  if (preview && (state.previewArtifact?.runId !== r._id || state.previewArtifact?.html !== preview.html || state.previewArtifact?.revision !== r.brief_revision)) {
    const artifact = { runId: r._id, html: preview.html, revision: r.brief_revision, loaded: false };
    state.previewArtifact = artifact;
    state.feedbackRunId = null;
    // A fresh frame keeps old load events from revealing feedback for a new artifact.
    const frame = $("preview-frame").cloneNode(false);
    frame.addEventListener("load", () => {
      if (state.previewArtifact !== artifact) return;
      artifact.loaded = true;
      renderFeedbackVisibility();
    }, { once: true });
    frame.srcdoc = preview.html;
    $("preview-frame").replaceWith(frame);
  } else if (!preview && state.previewArtifact) {
    state.previewArtifact = null;
    $("preview-frame").srcdoc = "";
  }
  renderFeedbackVisibility();
  if (hasPreview && !legacyPreview && state.feedbackRunId !== r._id) {
    state.feedbackRunId = r._id;
    state.feedbackRating = null;
    state.feedbackSubmitted = false;
    $("feedback-text").value = "";
    $("feedback-up").setAttribute("aria-pressed", "false");
    $("feedback-down").setAttribute("aria-pressed", "false");
    $("feedback-status").textContent = "";
    $("feedback-lesson").replaceChildren();
    renderFeedbackControls();
  }
  show('preview-card', state.building || state.previewing || hasPreview);
  show('upgrade-btn', legacyPreview && !state.previewing);
  show('preview-legacy', legacyPreview && !state.previewing);
  show('preview-empty', ((state.building || state.previewing) && !hasPreview) || (state.previewing && legacyPreview));
  show('preview-frame', hasPreview && !legacyPreview);
  $('preview-status').textContent = state.previewing ? 'Building preview…' : state.building ? 'Preparing prompt…' : legacyPreview ? 'Update needed' : hasPreview ? 'Preview ready' : '';
  show('handoff', false);
  if (!hasBrief) return;
  $("run-status").replaceChildren(chip(r.status));
  $("brief-rev").textContent = r.brief_revision ? `Rev ${r.brief_revision}` : "";
  if (["needs_answers", "stale"].includes(r.status)) $("brief-details").open = true;
  else if (state.previewing || hasPreview) $("brief-details").open = false;

  show("stale", r.status === "stale");
  if (r.status === "stale") {
    $("stale").replaceChildren(el("strong", {}, "Cited context changed since this brief was prepared. "),
      el("ul", {}, (r.changes || []).map((c) => el("li", {}, `${c.key} (${c.type}): ${c.change}`))),
      el("button", { onclick: () => tell(`The brief is stale: ${(r.changes || []).map((c) => `${c.key} ${c.change}`).join("; ")}. Rebuild with the updated project context.`) }, "Rebuild with updated context"));
  }

  const b = r.brief;
  const root = $("brief"); root.replaceChildren();
  root.append(el("div", { class: "brief-section" }, el("h3", {}, "Objective"), el("p", { contenteditable: "true", "data-path": "objective" }, b.objective)));
  for (const [key, title] of SECTIONS) {
    const items = b[key] || [];
    root.append(el("div", { class: "brief-section" }, el("h3", {}, title),
      items.length ? el("ul", {}, items.map((it, i) => el("li", {},
        el("span", { contenteditable: "true", "data-path": `${key}.${i}` }, it.text), citeChips(it.sources),
        it.uncited ? el("span", { class: "uncited" }, "uncited") : null))) : el("p", { class: "muted" }, "None")));
  }
  const qs = b.open_questions || [];
  root.append(el("h3", {}, "Open questions"));
  if (!qs.length) root.append(el("p", { class: "muted" }, "None"));
  qs.forEach((q, i) => root.append(el("div", { class: `question ${q.blocking ? "blocking" : ""}` },
    q.blocking ? chip("blocking") : chip("non-blocking"), " ", q.text, citeChips(q.sources),
    el("div", { class: "row" }, el("input", { id: `qa-${i}`, placeholder: "Additional guidance" }),
      el("button", { class: "secondary", onclick: () => { const a = $(`qa-${i}`).value.trim(); if (a) tell(`Answer to "${q.text}": ${a}`); } }, "Answer")))));
  if ((r.answers || []).length) root.append(el("h3", {}, "Resolved"), el("ul", {}, r.answers.map((a) => el("li", {}, `${a.question} → ${a.answer}`))));
  if ((b.assumptions || []).length) root.append(el("h3", {}, "Assumptions"), el("ul", {}, b.assumptions.map((a) => el("li", {}, a))));
  if ((b.citation_warnings || []).length) root.append(el("p", { class: "uncited" }, `Dropped unknown citations: ${b.citation_warnings.join(", ")}`));
  root.querySelectorAll("[contenteditable]").forEach((n) => n.addEventListener("input", () => show("save-brief-btn")));
  show("save-brief-btn", false);

}

$("save-brief-btn").addEventListener("click", (e) => busy(e.target, "Saving…", async () => {
  const b = structuredClone(state.run.brief);
  document.querySelectorAll("#brief [contenteditable]").forEach((n) => {
    const [key, idx] = n.dataset.path.split(".");
    if (idx === undefined) b[key] = n.textContent.trim(); else b[key][Number(idx)].text = n.textContent.trim();
  });
  state.run = await api(`/runs/${state.run._id}/brief`, { method: "PATCH", body: { brief: b } });
  renderRun(); toast("Brief saved.");
}));

$("export-btn").addEventListener("click", (e) => busy(e.target, "Rechecking memory…", async () => {
  let md;
  try { md = await api(`/runs/${state.run._id}/export`); }
  catch (err) { if (err.status === 409) { state.run = await api(`/runs/${state.run._id}`); renderRun(); } throw err; }
  const a = el("a", { href: URL.createObjectURL(new Blob([md], { type: "text/markdown" })), download: "promptforge-brief.md" });
  a.click(); URL.revokeObjectURL(a.href);
  try { await navigator.clipboard.writeText(md); toast("Brief downloaded and copied."); } catch { toast("Brief downloaded. Clipboard unavailable."); }
  state.run = await api(`/runs/${state.run._id}`); renderRun(); $("brief-details").open = true; show("handoff"); await loadContext();
}));

// ---------- simple artifact feedback ----------
function renderFeedbackVisibility() {
  show("feedback-card", state.previewArtifact?.loaded && hasSavedArtifact(state.run)
    && state.previewArtifact.runId === state.run._id && !state.building && !state.previewing);
}

function renderFeedbackControls() {
  for (const rating of ["up", "down"]) {
    $(`feedback-${rating}`).setAttribute("aria-pressed", String(state.feedbackRating === rating));
    $(`feedback-${rating}`).disabled = state.feedbackSubmitting;
  }
  $("feedback-text").disabled = state.feedbackSubmitting;
  $("feedback-submit").disabled = state.feedbackSubmitting || state.feedbackSubmitted
    || (!state.feedbackRating && !$("feedback-text").value.trim());
  $("feedback-submit").textContent = state.feedbackSubmitting ? "Submitting…" : "Submit feedback";
}

function feedbackChanged() {
  state.feedbackSubmitted = false;
  $("feedback-status").textContent = "";
  renderFeedbackControls();
}

async function submitFeedback() {
  if (state.feedbackSubmitting || state.feedbackSubmitted || !state.previewArtifact?.loaded || state.building || state.previewing) return;
  const comment = $("feedback-text").value.trim();
  if (!state.feedbackRating && !comment) return;
  const label = state.feedbackRating === "up" ? "Thumbs up" : state.feedbackRating === "down" ? "Thumbs down" : "";
  const text = [label, comment].filter(Boolean).join(": ");
  const artifact = state.previewArtifact;
  state.feedbackSubmitting = true;
  $("feedback-status").textContent = "";
  renderFeedbackControls();
  try {
    const result = await api(`/runs/${artifact.runId}/feedback`, {
      method: "POST", body: { text, propose_lesson: Boolean(comment) },
    });
    if (state.previewArtifact !== artifact) return;
    state.feedbackSubmitted = true;
    $("feedback-status").textContent = "Thanks for the feedback.";
    renderFeedbackLesson(result);
  } catch (err) {
    if (state.previewArtifact === artifact) $("feedback-status").textContent = `Could not submit feedback: ${err.message}. Please try again.`;
  } finally {
    state.feedbackSubmitting = false;
    renderFeedbackControls();
  }
}

for (const rating of ["up", "down"]) {
  $(`feedback-${rating}`).addEventListener("click", () => {
    state.feedbackRating = state.feedbackRating === rating ? null : rating;
    feedbackChanged();
  });
}
$("feedback-text").addEventListener("input", feedbackChanged);
$("feedback-form").addEventListener("submit", (event) => {
  event.preventDefault();
  submitFeedback();
});

function renderFeedbackLesson(result) {
  const box = $("feedback-lesson");
  box.replaceChildren();
  if (!result.proposed) return;

  const lesson = result.proposed;
  const scope = (result.scopes_allowed || []).includes("project") ? "project" : "personal";
  const text = el("textarea", { rows: 2, "aria-label": "Suggested lesson" });
  text.value = lesson.text;
  box.append(el("div", { class: "generated-lesson" },
    el("strong", {}, "Suggested lesson"),
    el("p", { class: "hint" }, "Generated from your feedback. Review it before saving."),
    text,
    el("div", { class: "row" },
      el("button", { class: "secondary", onclick: (event) => busy(event.currentTarget, "Dismissing…", async () => {
        await api(`/lessons/${lesson._id}/reject`, { method: "POST" });
        box.replaceChildren();
        $("feedback-status").textContent = "Feedback saved. Suggested lesson dismissed.";
      }) }, "Dismiss"),
      el("span", { class: "spacer" }),
      el("button", { onclick: (event) => busy(event.currentTarget, "Saving…", async () => {
        await api(`/lessons/${lesson._id}/approve`, { method: "POST", body: { scope, text: text.value.trim() } });
        box.replaceChildren();
        $("feedback-status").textContent = scope === "project" ? "Lesson saved for this project." : "Lesson saved for you.";
        await loadContext();
      }) }, "Save lesson"))));
}
init().catch((e) => {
  $("active-context").textContent = "Workspace unavailable";
  toast(e.message);
});
