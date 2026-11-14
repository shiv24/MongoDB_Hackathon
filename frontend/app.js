// PromptForge UI: type or dictate a request -> grounded prompt -> generated artifact.
// Server text is inserted with textContent only.


const $ = (id) => document.getElementById(id);
const DEFAULT_USER_ID = "console-alice";
const DEFAULT_PROJECT_ID = "admin-console";
const state = { me: null, projectId: null, run: null, context: null, previewing: false, feedbackRunId: null, baseline: null };

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

let progressStarted = 0;
let progressTimer = null;
function progress(message) {
  if (!progressTimer) {
    progressStarted = Date.now();
    progressTimer = setInterval(() => {
      $('task-time').textContent = `${Math.floor((Date.now()-progressStarted)/1000)}s elapsed · Please wait. The next step opens automatically.`;
    }, 1000);
  }
  $('task-stage').textContent = message;
  $('task-time').textContent = `${Math.floor((Date.now()-progressStarted)/1000)}s elapsed · Please wait. The next step opens automatically.`;
  $('task-progress').classList.remove('hidden');
}
function stopProgress() { clearInterval(progressTimer); progressTimer = null; $('task-progress').classList.add('hidden'); }
$('feedback-scope').addEventListener('change', () => {
  $('scope-help').textContent = {personal:'Only your future requests can use this guidance.',project:'Anyone working on this project can use this guidance.',team:'Anyone on your team can use this guidance across projects.'}[$('feedback-scope').value];
});

const show = (id, on = true) => $(id).classList.toggle("hidden", !on);
const chip = (text) => el("span", { class: `chip ${text}` }, String(text).replace(/_/g, " "));

// ---------- fixed demo identity and project ----------
async function init() {
  state.me = await api("/login", { method: "POST", body: { user_id: sessionStorage.getItem("pf-console-user") || DEFAULT_USER_ID } });
  $("session-user").value = state.me.user_id;
  $('feedback-scope').querySelector('[value="team"]').disabled = !['publisher','admin'].includes(state.me.role);
  if ($('feedback-scope').selectedOptions[0].disabled) $('feedback-scope').value = 'project';
  $('feedback-scope').dispatchEvent(new Event('change'));
  const projects = await api("/projects");
  const project = projects.find((p) => p._id === DEFAULT_PROJECT_ID);
  if (!project) throw new Error(`Default project ${DEFAULT_PROJECT_ID} is not available to ${DEFAULT_USER_ID}. Seed the demo data first.`);
  state.projectId = project._id;
  $("active-context").textContent = `${state.me.name} · ${project.name}`;
  await loadContext();
  const params = new URLSearchParams(location.hash.slice(1));
  const beforeId = params.get('before') || sessionStorage.getItem(`pf-before-${state.me.user_id}`);
  if (beforeId && /^[a-f0-9]+$/.test(beforeId)) {
    try { state.baseline = await api(`/runs/${beforeId}`); }
    catch { state.baseline = null; sessionStorage.removeItem(`pf-before-${state.me.user_id}`); }
  }
  const saved = location.hash.match(/^#run=([a-f0-9]+)(?:&before=[a-f0-9]+)?$/);
  if (saved) {
    try { await openRun(saved[1]); if (params.get('before') && state.baseline?.artifact && state.run?.artifact) $('compare-preview').click(); }
    catch (err) { if (err.status !== 404 && err.status !== 403) throw err; history.replaceState(null, '', location.pathname); toast('This prompt belongs to another workspace or teammate. Start a new request here.'); }
  }
}

$('session-user').addEventListener('change', async e => {
  const next = e.target.value;
  if (state.previewing || $('send-btn').disabled) { e.target.value = state.me.user_id; toast('Wait for the current request to finish.'); return; }
  try {
    await api('/logout', {method:'POST'});
    state.run = null; state.context = null; state.feedbackRunId = null; state.baseline = null;
    history.replaceState(null, '', location.pathname);
    sessionStorage.setItem('pf-console-user', next);
    $('type-input').value = ''; renderRun();
    await init();
    toast(`Fresh session as ${state.me.name}. Shared lessons stay; personal prompts do not.`);
  } catch (err) { toast(err.message); }
});
$('lesson-example').addEventListener('click', () => {
  if (!state.run?.brief) { toast('Create a prompt first, then add feedback.'); return; }
  $('feedback-text').value = 'Use purple (#7C3AED) backgrounds and white text for all action buttons in this project, including Clear search and pagination. Keep the table background light and its text dark.';
  $('feedback-card').scrollIntoView({behavior:'smooth',block:'center'}); $('feedback-text').focus();
});
async function openRun(id) {
  if (state.previewing) return;
  state.run = await api(`/runs/${id}`);
  $('type-input').value = state.run.request;
  renderRun(); renderContext();
  history.replaceState(null, '', `#run=${id}`);
}

// ---------- direct request and optional microphone ----------
let recording = null;
let microphone = null;
async function submitRequest(clarification = '', lessonIds = []) {
  if (!state.projectId) throw new Error('The default workspace is still loading. Try again in a moment.');
  const request = clarification && state.run ? state.run.request : $('type-input').value.trim();
  if (!request) throw new Error('Describe what you want built.');
  const answers = clarification ? (state.run?.clarification_text || '') + '\n' + clarification : '';
  progress('1 of 2 · Writing your prompt using project memory');
  state.run = await api('/build', {method:'POST', body:{project_id:state.projectId, request, clarification:answers, lesson_ids:lessonIds}});
  renderRun();
  history.replaceState(null, '', `#run=${state.run._id}`);
  await Promise.all([generatePreview(), loadContext()]);
  $('preview-card').scrollIntoView({behavior:'smooth',block:'start'});
}
function tell(text) { busy($('send-btn'), 'Updating…', () => submitRequest(text)); }
$('send-btn').addEventListener('click', e => busy(e.currentTarget, 'Building…', async () => {
  show('request-error', false); show('request-status');
  $('request-status').textContent = 'Using project memory to write the prompt and build your preview…';
  try { await submitRequest(); }
  catch (err) { $('request-error').textContent = err.message; show('request-error'); }
  finally { show('request-status', false); stopProgress(); }
}));
$('demo-request').addEventListener('click', () => { $('type-input').value = state.me?.user_id === 'console-bob' ? 'Add search to the orders table.' : 'Add search to the users table. Show sample results for a search for Alex.'; $('type-input').focus(); });
$('type-input').addEventListener('keydown', e => { if(e.key === 'Enter' && (e.metaKey || e.ctrlKey)) $('send-btn').click(); });

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
      $('talk-btn').textContent='🎙 Record request';
      try {
        const form=new FormData(); form.append('audio',new Blob(parts,{type:recorder.mimeType}),'request.webm');
        const response=await fetch('/api/voice/transcribe',{method:'POST',body:form});
        const result=await response.json();
        if(!response.ok) throw new Error(result.error || 'Transcription failed');
        $('type-input').value=result.text; toast('Review the transcript, then forge your prompt.');
      } catch(e) { toast(e.message); }
    };
    recording.start(); $('talk-btn').textContent='Stop recording';
    setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},60000);
  } catch(e) { toast('Microphone unavailable. You can type your request.'); }
});
async function generatePreview() {
  if (!state.run?._id || state.previewing) return;
  if (!$('save-brief-btn').classList.contains('hidden')) throw new Error('Save your edits before generating a preview.');
  state.previewing = true;
  progress('2 of 2 · Generating your visual preview');
  $('send-btn').disabled = true;
  renderRun();
  try {
    state.run = await api(`/build/${state.run._id}/preview`, { method: 'POST' });
  } catch (err) {
    state.run = await api(`/runs/${state.run._id}`);
    $('request-error').textContent = `Your prompt is saved, but the preview failed: ${err.message}. Open the prompt below and press Preview website to retry.`; show('request-error');
    throw err;
  } finally {
    stopProgress();
    state.previewing = false;
    $('send-btn').disabled = false;
    renderRun();
  }
}

$('copy-btn').addEventListener('click', e => busy(e.currentTarget, 'Copying…', async () => {
  if (!$('save-brief-btn').classList.contains('hidden')) throw new Error('Save your edits before copying.');
  try {
    const md = await api(`/runs/${state.run._id}/export`);
    await navigator.clipboard.writeText(md); toast('Prompt copied. Paste it into your agent.');
  } catch (err) {
    if (err.status === 409) { state.run = await api(`/runs/${state.run._id}`); renderRun(); }
    throw err;
  }
}));
$('pin-preview').addEventListener('click', () => {
  if (!state.run?.artifact || state.previewing) return;
  state.baseline = structuredClone(state.run); sessionStorage.setItem(`pf-before-${state.me.user_id}`, state.run._id); renderRun();
  toast('Before version kept. Approve feedback, then rerun the same request.');
});
$('compare-close').addEventListener('click', () => $('compare-dialog').close());
$('compare-preview').addEventListener('click', () => {
  if (!state.baseline?.artifact || !state.run?.artifact) return;
  const before = state.baseline, after = state.run;
  history.replaceState(null, '', `#run=${after._id}&before=${before._id}`);
  $('before-frame').srcdoc = before.artifact.html;
  $('after-frame').srcdoc = after.artifact.html;
  $('compare-meta').textContent = `${before.request === after.request ? 'Same request' : 'Different requests'} · Before: ${before.artifact.model} · After: ${after.artifact.model}`;
  const used = usedIds();
  const beforeKeys = new Set(['requirements','current_decisions','implementation_context','preferences','acceptance_checks','open_questions'].flatMap(k => (before.brief[k] || []).flatMap(i => i.sources || [])));
  const previousLessons = new Set((before.provenance || []).filter(e => e.type === 'lesson' && beforeKeys.has(e.key)).map(e => `${e.id}:${e.revision}`));
  const learned = (after.provenance || []).filter(e => e.type === 'lesson' && used.has(e.id) && !previousLessons.has(`${e.id}:${e.revision}`));
  $('compare-learning').textContent = learned.length ? 'New learned guidance: ' + learned.map(e => e.text).join(' ') : 'No newly cited lesson compared with the before version. Check approval, relevance and indexing before presenting this as a memory-driven change.';
  $('compare-dialog').showModal();
});
$('generate-btn').addEventListener('click', e => busy(e.target, 'Generating preview…', generatePreview));

// ---------- project context sidebar ----------
async function loadContext() {
  if (!state.projectId) return;
  state.context = await api(`/projects/${state.projectId}/context`);
  renderContext();
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
  $('brain-count').textContent = `${c.sources.length} sources · ${c.decisions.filter(d => d.status === 'current').length} decisions · ${c.lessons.filter(l => l.status === 'approved').length} approved lessons`;
  renderBrain();
  $('recent-runs').replaceChildren(...(c.runs || []).filter(r => r.status !== 'drafting').slice(0, 6).map(r =>
    el('button', {class:'history-item', type:'button', disabled:state.previewing, onclick: e => busy(e.currentTarget, 'Opening…', () => openRun(r._id))}, r.request)));
  if (!(c.runs || []).length) $('recent-runs').append(el('p', {class:'hint'}, 'Your saved prompts will appear here.'));
  $("sources").replaceChildren(...c.sources.map((s) => el("li", { class: used.has(s.source_id) ? "used" : "" },
    el("span", { class: "text" }, s.title), el("span", { class: "meta" }, `${s.kind} · revision ${s.revision} · added by ${s.added_by}`))));
  if (!c.sources.length) $("sources").append(el("li", { class: "muted" }, "No sources yet."));
}

$("src-btn").addEventListener("click", (e) => busy(e.target, "Adding…", async () => {
  const title = $("src-title").value.trim();
  const text = $("src-text").value.trim();
  const file = $("src-file").files[0];
  if (!file && !text) throw new Error("Paste source text or choose a PDF or text file.");
  if (file) {
    const body = new FormData();
    body.append("title", title);
    body.append("text", text);
    body.append("file", file);
    await api(`/projects/${state.projectId}/sources/file`, { method: "POST", body });
  } else {
    await api(`/projects/${state.projectId}/sources`, {
      method: "POST", body: { title: title || "Pasted source", text },
    });
  }
  $("src-title").value = ""; $("src-text").value = ""; $("src-file").value = "";
  await loadContext();
  toast("Source added to project context.");
}));
// ---------- inspect and maintain project memory ----------
function renderBrain() {
  const c = state.context; if (!c) return;
  const query = $('brain-search').value.trim().toLowerCase();
  const root = $('brain-entries'); root.replaceChildren();
  for (const [title, records] of [['Sources', c.sources.map(s => ({...s, text:s.title, status:'source',owner_id:s.added_by}))], ['Decisions', c.decisions], ['Lessons', c.lessons]]) {
    const matches = records.filter(r => `${r.text} ${r.scope || ''} ${r.status}`.toLowerCase().includes(query));
    root.append(el('h3', {}, title));
    if (!matches.length) root.append(el('p', {class:'hint'}, query ? 'No matches.' : `No ${title.toLowerCase()} yet.`));
    for (const r of matches) root.append(el('article', {class:'memory-entry'},
      el('div', {class:'row'}, chip(r.status), el('span', {class:'muted'}, `${r.scope || 'project'} · ${r.owner_id || 'team'} · revision ${r.revision}`)),
      el('p', {}, r.text),
      r.source_id ? el('button', {class:'secondary', type:'button', onclick: async e => busy(e.currentTarget, 'Loading…', async () => {
        const article = e.currentTarget.closest('article');
        const source = await api(`/projects/${state.projectId}/sources/${r.source_id}`);
        let content = article.querySelector('.source-content');
        if (!content) { content = el('pre', {class:'source-content'}); article.append(content); }
        content.textContent = source.text;
      })}, 'Read source') : null));
  }
}
$('brain-open').addEventListener('click', () => { renderBrain(); $('brain-dialog').showModal(); });
$('brain-close').addEventListener('click', () => $('brain-dialog').close());
$('brain-search').addEventListener('input', renderBrain);
$('rule-save').addEventListener('click', e => busy(e.currentTarget, 'Saving…', async () => {
  const text = $('rule-text').value.trim();
  if (!text) throw new Error('Write the project rule first.');
  await api(`/projects/${state.projectId}/decisions`, {method:'POST', body:{text}});
  $('rule-text').value = ''; await loadContext();
  toast('Project rule saved. It will become searchable after indexing.');
}));
// ---------- brief ----------
const SECTIONS = [["requirements", "Requirements"], ["current_decisions", "Current decisions"], ["implementation_context", "Implementation context"],
  ["preferences", "Preferences"], ["acceptance_checks", "Acceptance checks"]];

function citeChips(keys) {
  const prov = Object.fromEntries((state.run.provenance || []).map((e) => [e.key, e]));
  return (keys || []).map((k) => {
    const e = prov[k]; if (!e) return null;
    const label = e.type === "user" ? "Your explicit request or clarification" : e.type === "source" ? `Source "${e.title}" rev ${e.revision}` : e.type === "decision" ? `Team decision rev ${e.revision} (owner ${e.owner_id})` : `Approved ${e.scope} lesson rev ${e.revision}`;
    return el("span", { class: "cite", tabindex: "0", "aria-label": `${label}: ${e.text}`, title: `${label}\n\n${e.text}` }, e.type === "user" ? "Your request" : `${{source:"Source",decision:"Decision",lesson:"Lesson"}[e.type]} ${k.slice(1)}`);
  });
}

function renderRun() {
  const r = state.run;
  const hasBrief = !!r?.brief;
  show("brief-card", hasBrief);
  const hasPreview = !!r?.artifact && r.artifact.brief_revision === r.brief_revision && r.status !== 'stale';
  show("feedback-card", hasPreview);
  if (hasBrief && state.feedbackRunId !== r._id) {
    state.feedbackRunId = r._id;
    $("feedback-text").value = "";
    $("feedback-status").textContent = "";
    $("feedback-lesson").replaceChildren();
  }
  show('preview-card', state.previewing || hasPreview);
  $('pin-preview').disabled = !hasPreview || state.previewing;
  $('compare-preview').disabled = !hasPreview || !state.baseline || state.baseline._id === r?._id;
  $('baseline-status').textContent = state.baseline ? 'Before version kept for comparison.' : 'Keep the first version before teaching a lesson.';
  $('preview-status').textContent = state.previewing ? 'Building preview…' : hasPreview ? 'Preview ready' : '';
  if (hasPreview) $('preview-frame').srcdoc = r.artifact.html;
  else if (!state.previewing) $('preview-frame').srcdoc = '';
  show('handoff', false);
  if (!hasBrief) return;
  $("run-status").replaceChildren(chip(r.status));
  $("brief-rev").textContent = r.brief_revision ? `revision ${r.brief_revision} by the agent` : "";
  if (["needs_answers", "stale"].includes(r.status)) $("brief-details").open = true;
  else $("brief-details").open = true;

  show("stale", r.status === "stale");
  if (r.status === "stale") {
    $("stale").replaceChildren(el("strong", {}, "Cited context changed since this brief was prepared. "),
      el("ul", {}, (r.changes || []).map((c) => el("li", {}, `${c.key} (${c.type}): ${c.change}`))),
      el("button", { onclick: () => tell(`The brief is stale: ${(r.changes || []).map((c) => `${c.key} ${c.change}`).join("; ")}. Rebuild with the updated project context.`) }, "Rebuild with updated context"));
  }

  const b = r.brief;
  const cited = usedIds();
  const learned = (r.provenance || []).filter(e => e.type === 'lesson' && cited.has(e.id));
  $('learning-status').replaceChildren(
    el('strong', {}, learned.length ? `Learned guidance used · ${learned.length} ${learned.length === 1 ? 'lesson' : 'lessons'}` : 'No learned lessons used in this prompt'),
    ...learned.map(e => el('p', {}, `${e.text} — approved by ${(e.approved_by || e.owner_id).replace("console-", "")}, ${e.scope} scope`)),
    ...(!learned.length ? [el('p', {class:'hint'}, 'This prompt may use documents and decisions. Approved lessons appear here only when selected and cited for the request.')] : []));
  const contributions = [];
  const provenance = Object.fromEntries((r.provenance || []).map(e => [e.key, e]));
  for (const section of ['preferences', 'current_decisions', 'requirements']) {
    for (const item of b[section] || []) {
      const evidence = (item.sources || []).map(k => provenance[k]).filter(e => e && e.type !== 'user');
      if (!evidence.length || contributions.some(c => c.text === item.text)) continue;
      contributions.push({text: item.text, evidence});
    }
  }
  $('contributions').replaceChildren(el('p', {class:'contribution-heading'}, contributions.length ? 'What your team brought to this prompt' : 'Add team sources to enrich your next prompt'),
    ...contributions.slice(0, 4).map(c => el('details', {class:'contribution'},
      el('summary', {}, c.text), ...c.evidence.map(e => el('p', {}, `${e.title || (e.type === 'decision' ? 'Team decision' : 'Approved lesson')} · ${e.approved_by || e.owner_id || 'source'} · revision ${e.revision}: ${e.text}`)))));

  const root = $("brief"); root.replaceChildren();
  root.append(el("div", { class: "brief-section" }, el("h3", {}, "Objective"), el("p", { contenteditable: "true", "data-path": "objective" }, b.objective)));
  for (const [key, title] of SECTIONS) {
    const items = b[key] || [];
    if (!items.length) continue;
    root.append(el("div", { class: "brief-section" }, el("h3", {}, title),
      items.length ? el("ul", {}, items.map((it, i) => el("li", {},
        el("span", { contenteditable: "true", "data-path": `${key}.${i}` }, it.text), citeChips(it.sources),
        it.uncited ? el("span", { class: "uncited" }, "uncited") : null))) : el("p", { class: "muted" }, "None")));
  }
  const qs = b.open_questions || [];
  if (qs.length) root.append(el("h3", {}, "Open questions"));
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
  if (!$("save-brief-btn").classList.contains("hidden")) throw new Error("Save your edits before downloading.");
  let md;
  try { md = await api(`/runs/${state.run._id}/export`); }
  catch (err) { if (err.status === 409) { state.run = await api(`/runs/${state.run._id}`); renderRun(); } throw err; }
  const a = el("a", { href: URL.createObjectURL(new Blob([md], { type: "text/markdown" })), download: "promptforge-brief.md" });
  a.click(); URL.revokeObjectURL(a.href);
  try { await navigator.clipboard.writeText(md); toast("Brief downloaded and copied."); } catch { toast("Brief downloaded. Clipboard unavailable."); }
  state.run = await api(`/runs/${state.run._id}`); renderRun(); $("brief-details").open = true; show("handoff"); await loadContext();
}));

// ---------- simple artifact feedback ----------
$('feedback-example').addEventListener('click', () => $('lesson-example').click());
async function submitFeedback() {
  show('feedback-error', false);
  const text = $('feedback-text').value.trim();
  if (!text) {
    $('feedback-error').textContent = 'Type your feedback in the box above first, or click Use example feedback. The gray example text is not submitted.';
    show('feedback-error'); $('feedback-text').focus(); return;
  }
  if (!state.run?.brief) { $('feedback-error').textContent = 'Build a preview first.'; show('feedback-error'); return; }
  const runId = state.run._id;
  $('remember-rebuild').disabled = true; $('send-btn').disabled = true; $('session-user').disabled = true;
  $('feedback-status').textContent = 'Reading your feedback and preparing a lesson…';
  progress('Turning your feedback into a reusable lesson');
  try {
    const result = await api(`/runs/${runId}/feedback`, {method:'POST', body:{text, propose_lesson:true}});
    $('feedback-status').textContent = result.proposed ? 'Lesson ready below. Review it, choose who should remember it, then approve.' : 'Feedback saved, but no reusable lesson was identified. Describe a rule for future requests, or use Save feedback & rebuild to save your exact wording.';
    renderFeedbackLesson(result);
    if (result.proposed) $('feedback-lesson').scrollIntoView({behavior:'smooth',block:'center'});
  } catch (err) {
    $('feedback-status').textContent = 'Lesson could not be prepared.';
    $('feedback-error').textContent = err.message + ' Your feedback is still in the box. You can retry.';
    show('feedback-error');
  } finally { stopProgress(); $('remember-rebuild').disabled = false; $('send-btn').disabled = false; $('session-user').disabled = false; }
}
$('remember-rebuild').addEventListener('click', e => busy(e.currentTarget, 'Remembering and rebuilding…', async () => {
  const text = $('feedback-text').value.trim();
  if (!text) throw new Error('Tell us what to change first.');
  if (state.previewing || $('send-btn').disabled) throw new Error('Wait for the current build to finish.');
  const previous = structuredClone(state.run);
  const chosenScope = $('feedback-scope').value;
  let remembered = false;
  show('feedback-error', false);
  progress('Saving your guidance to memory');
  $('send-btn').disabled = true; $('session-user').disabled = true;
  try {
    const result = await api(`/runs/${previous._id}/feedback`, {method:'POST',body:{text,lesson:text}});
    if (!result.proposed) throw new Error('No lesson was created. Your current preview is unchanged.');
    await api(`/lessons/${result.proposed._id}/approve`, {method:'POST',body:{scope:chosenScope,text}});
    remembered = true;
    state.baseline = previous; sessionStorage.setItem(`pf-before-${state.me.user_id}`, previous._id);
    $('type-input').value = previous.request;
    toast('Guidance saved. Rebuilding the same request…');
    await submitRequest('', [result.proposed._id]);
    if (state.run?.artifact) $('compare-preview').click();
  } catch (err) { $('feedback-error').textContent = (remembered ? 'Your guidance was saved, but rebuilding failed. ' : '') + err.message; show('feedback-error'); }
  finally { stopProgress(); $('send-btn').disabled = false; $('session-user').disabled = false; }
}));
$('suggest-lesson').addEventListener('click', e => busy(e.currentTarget, 'Preparing lesson…', submitFeedback));

function renderFeedbackLesson(result) {
  const box = $("feedback-lesson");
  box.replaceChildren();
  if (!result.proposed) return;

  const lesson = result.proposed;
  const scopePicker = el('select', {'aria-label':'Who should remember this lesson?'},
    ...(result.scopes_allowed || ['personal']).map(s => el('option', {value:s}, {personal:'Just me',project:'This project',team:'Whole team'}[s])));
  const text = el("textarea", { rows: 2, "aria-label": "Suggested lesson" });
  text.value = lesson.text;
  if ((result.scopes_allowed || []).includes($('feedback-scope').value)) scopePicker.value = $('feedback-scope').value;
  box.append(el("div", { class: "generated-lesson" },
    el("strong", {}, "Suggested lesson"),
    el("p", { class: "hint" }, "Not active yet. Review the wording and choose who should benefit."),
    text, el("label", {class:"hint"}, "Who should use this in future prompts?"), scopePicker,
    el("div", { class: "row" },
      el("button", { class: "secondary", onclick: (event) => busy(event.currentTarget, "Dismissing…", async () => {
        await api(`/lessons/${lesson._id}/reject`, { method: "POST" });
        box.replaceChildren();
        $("feedback-status").textContent = "Feedback saved. Suggested lesson dismissed.";
      }) }, "Dismiss"),
      el("span", { class: "spacer" }),
      el("button", { onclick: (event) => busy(event.currentTarget, "Saving…", async () => {
        const scope = scopePicker.value;
        await api(`/lessons/${lesson._id}/approve`, { method: "POST", body: { scope, text: text.value.trim() } });
        box.replaceChildren(el('div', {class:'lesson-success'},
          el('strong', {}, 'Approved for future relevant prompts'),
          el('p', {}, text.value.trim()),
          el('p', {class:'hint'}, 'This does not rewrite the current prompt. Create a new request; when this lesson is relevant, its citation will appear under “Learned guidance used”. Newly saved lessons may need a moment to become searchable.'),
          el('button', {class:'secondary',type:'button',onclick:() => { $('type-input').value = state.baseline?.request || state.run.request; $('request-card').scrollIntoView({behavior:'smooth',block:'center'}); $('type-input').focus(); }}, 'Use the same request again')));
        $("feedback-status").textContent = ({project:"Lesson saved for this project.",team:"Lesson saved for your team.",personal:"Lesson saved for you."})[scope];
        await loadContext();
      }) }, "Approve for future prompts"))));
}
window.addEventListener('hashchange', () => { const match = location.hash.match(/^#run=([a-f0-9]+)$/); if (state.me && match && match[1] !== state.run?._id) openRun(match[1]).catch(e => toast(e.message)); });
init().catch((e) => {
  $("active-context").textContent = "Workspace unavailable";
  toast(e.message);
});
