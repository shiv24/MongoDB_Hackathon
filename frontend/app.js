// PromptForge UI: talk to the ElevenLabs agent -> cited brief (live) -> export for Claude Code
// -> record result -> feedback -> approved lesson. Server text is inserted with textContent only.


const $ = (id) => document.getElementById(id);
const state = { me: null, projectId: null, run: null, context: null, conversation: null, agentSessionId: null, poll: null };

// ---------- helpers ----------
async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: opts.body ? { "Content-Type": "application/json" } : {}, credentials: "same-origin", ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
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

// ---------- login and projects ----------
async function init() {
  const users = await api("/users");
  for (const u of users) $("user-select").append(el("option", { value: u._id }, u.name));
  try { state.me = await api("/me"); $("user-select").value = state.me.user_id; await loadProjects(); } catch { /* not logged in */ }
}

$("user-select").addEventListener("change", async (e) => {
  if (!e.target.value) return;
  await endConversation();
  state.me = await api("/login", { method: "POST", body: { user_id: e.target.value } });
  state.run = null; renderRun();
  await loadProjects();
  toast(`Signed in as ${state.me.name}. Team and projects come from the server, not the browser.`);
});

async function loadProjects() {
  const sel = $("project-select"); sel.replaceChildren(); sel.disabled = false;
  const projects = await api("/projects");
  for (const p of projects) sel.append(el("option", { value: p._id }, p.name));
  state.projectId = projects[0]?._id || null;
  await loadContext();
}

$("project-select").addEventListener("change", async (e) => {
  await endConversation(); state.projectId = e.target.value; state.run = null; renderRun(); await loadContext();
});

function addLine(role, text) {
  show("transcript");
  const list = $("transcript");
  list.append(el("li", { class: role }, el("span", { class: "who" }, role === "agent" ? "PromptForge agent" : "You"), text));
  list.scrollTop = list.scrollHeight;
}

async function startConversation(textOnly) {
  if (!state.projectId) throw new Error("Choose a user and project first.");
  if (state.conversation) return;
  const { Conversation } = await import("https://cdn.jsdelivr.net/npm/@elevenlabs/client@1.32.1/+esm");
  const s = await api("/voice/session", { method: "POST", body: { project_id: state.projectId } });
  state.agentSessionId = s.agent_session_id;
  $("transcript").replaceChildren();
  state.conversation = await Conversation.startSession({
    signedUrl: s.signed_url,
    dynamicVariables: s.dynamic_variables,      // secret__pf_token is used only in tool headers, never sent to the LLM
    textOnly,
    connectionType: "websocket",
    onConnect: () => { $("agent-status").textContent = textOnly ? "Connected (text)" : "Listening…"; },
    onDisconnect: () => { pollRun(); $("agent-status").textContent = "Conversation ended"; stopConversationUi(); },
    onError: (msg) => toast(`Agent error: ${msg}`),
    onModeChange: ({ mode }) => { if (!textOnly) $("agent-status").textContent = mode === "speaking" ? "Agent speaking…" : "Listening…"; },
    onMessage: ({ message, role }) => addLine(role, message),
  });
  show("agent-btn", false); show("talk-btn", false); show("type-btn", false); show("end-btn"); show("type-row", true);
  clearInterval(state.poll);
  state.poll = setInterval(pollRun, 2000);   // the agent saves briefs through tools; mirror them here
}

function stopConversationUi() {
  state.conversation = null; clearInterval(state.poll);
  show("agent-btn"); show("talk-btn"); show("type-btn"); show("end-btn", false); show("type-row", true);
}

async function endAgentConversation() { if (state.conversation) { try { await state.conversation.endSession(); } catch { /* already closed */ } stopConversationUi(); } }

function tellAgent(text) {
  if (!state.conversation) { toast("Start a conversation with the agent first."); return false; }
  state.conversation.sendUserMessage(text); addLine("user", text); return true;
}

$('agent-btn').addEventListener('click', e => busy(e.target,'Connecting…',()=>startConversation(false)));
$('end-btn').addEventListener('click', endAgentConversation);

async function pollRun() {
  if (!state.agentSessionId) return;
  try {
    const run = await api(`/voice/session/${state.agentSessionId}/run`);
    if (!run) return;
    const changed = !state.run || state.run._id !== run._id || state.run.updated_at !== run.updated_at || state.run.status !== run.status;
    if (changed) { state.run = run; renderRun(); renderContext(); }
  } catch { /* transient */ }
}


// ---------- direct request and optional microphone ----------
let recording = null;
let microphone = null;
async function endConversation() {
  await endAgentConversation();
  if (recording && recording.state !== 'inactive') recording.stop();
  if (microphone) microphone.getTracks().forEach(t => t.stop());
  state.agentSessionId = null;
}
async function submitRequest(clarification = '') {
  if(state.conversation) { tellAgent(clarification || $('type-input').value); return; }
  if (!state.projectId) throw new Error('Choose a user and project first.');
  const request = clarification && state.run ? state.run.request : $('type-input').value.trim();
  if (!request) throw new Error('Describe what you want built.');
  const answers = clarification ? (state.run?.clarification_text || '') + '\n' + clarification : '';
  state.run = await api('/build', {method:'POST', body:{project_id:state.projectId, request, clarification:answers}});
  renderRun(); await loadContext();
}
function tell(text) { if(state.conversation) return tellAgent(text); busy($('send-btn'), 'Updating…', () => submitRequest(text)); }
$('send-btn').addEventListener('click', e => busy(e.target, 'Building brief…', () => submitRequest()));
$('type-input').addEventListener('keydown', e => { if(e.key === 'Enter') $('send-btn').click(); });
$('type-btn').addEventListener('click', () => $('type-input').focus());
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
        $('type-input').value=result.text; toast('Review the transcript, then build the brief.');
      } catch(e) { toast(e.message); }
    };
    recording.start(); $('talk-btn').textContent='Stop recording';
    setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},60000);
  } catch(e) { toast('Microphone unavailable. You can type your request.'); }
});
$('generate-btn').addEventListener('click', e => busy(e.target,'Generating preview…',async()=>{
  try { state.run=await api(`/build/${state.run._id}/preview`,{method:'POST'}); }
  catch(err) { state.run=await api(`/runs/${state.run._id}`); renderRun(); throw err; }
  renderRun();
}));

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
  $("sources").replaceChildren(...c.sources.map((s) => el("li", { class: used.has(s.source_id) ? "used" : "" },
    el("span", { class: "text" }, s.title), el("span", { class: "meta" }, `${s.kind} · revision ${s.revision} · added by ${s.added_by}`))));
  if (!c.sources.length) $("sources").append(el("li", { class: "muted" }, "No sources yet."));

  $("decisions").replaceChildren(...c.decisions.map((d) => el("li", { class: `${d.status} ${used.has(d._id) ? "used" : ""}` },
    el("span", { class: "text" }, d.text),
    el("span", { class: "meta" }, chip(d.status), ` rev ${d.revision} · owner ${d.owner_id} `,
      d.status === "current" ? el("button", { class: "link", onclick: () => correctDecision(d) }, "correct") : null,
      el("button", { class: "link", onclick: () => showHistory(`/projects/decisions/${d._id}/history`) }, "history")))));

  $("lessons").replaceChildren(...c.lessons.map((l) => el("li", { class: `${l.status} ${used.has(l._id) ? "used" : ""}` },
    el("span", { class: "text" }, l.text),
    el("span", { class: "meta" }, chip(l.status), ` ${l.scope} · rev ${l.revision} · by ${l.owner_id}${l.approved_by ? `, approved by ${l.approved_by}` : ""} `,
      l.status === "proposed" ? el("button", {class:"link", onclick:()=>renderProposal({proposed:l, scopes_allowed:state.me.role === "member" ? ["personal","project"] : ["personal","project","team"]})}, "review proposal") : null,
      l.status === "approved" ? [
        el("button", { class: "link", onclick: () => lessonAction(l, "correct") }, "correct"),
        el("button", { class: "link", onclick: () => lessonAction(l, "retire") }, "retire"),
        el("button", { class: "link", onclick: () => lessonAction(l, "forget") }, "forget")] : null,
      el("button", { class: "link", onclick: () => showHistory(`/lessons/${l._id}/history`) }, "history")))));
  if (!c.lessons.length) $("lessons").append(el("li", { class: "muted" }, "No lessons yet."));
}

async function showHistory(path) {
  const events = await api(path);
  $("history").replaceChildren(...events.map((e) => el("li", {},
    el("strong", {}, e.event), ` by ${e.actor} (${e.cause}) `, el("span", { class: "meta" }, new Date(e.at).toLocaleString()))));
}

async function correctDecision(d) {
  const text = prompt("Corrected decision (creates a new revision; the old one is superseded):", d.text);
  if (!text || text === d.text) return;
  try { await api(`/projects/decisions/${d._id}/supersede`, { method: "POST", body: { text } }); toast("Decision superseded."); await loadContext(); }
  catch (e) { toast(e.message); }
}

async function lessonAction(l, action) {
  try {
    if (action === "correct") {
      const text = prompt("Corrected lesson (new revision):", l.text);
      if (!text || text === l.text) return;
      await api(`/lessons/${l._id}/correct`, { method: "POST", body: { text } });
    } else if (action === "retire") {
      if (!confirm("Retire this lesson? It will no longer shape new briefs.")) return;
      await api(`/lessons/${l._id}/retire`, { method: "POST" });
    } else {
      if (!confirm("Forget this lesson? It is removed from future use and briefs that cited it are marked stale. Text already in exported briefs is not erased.")) return;
      const r = await api(`/lessons/${l._id}`, { method: "DELETE" });
      toast(`Forgotten. ${r.runs_marked_stale} run(s) marked stale.`);
    }
    await loadContext();
    if (state.run) { state.run = await api(`/runs/${state.run._id}`); renderRun(); }
  } catch (e) { toast(e.message); }
}

$("src-btn").addEventListener("click", (e) => busy(e.target, "Adding…", async () => {
  await api(`/projects/${state.projectId}/sources`, { method: "POST", body: { title: $("src-title").value, text: $("src-text").value } });
  $("src-title").value = ""; $("src-text").value = ""; await loadContext();
}));
$("dec-btn").addEventListener("click", (e) => busy(e.target, "Adding…", async () => {
  await api(`/projects/${state.projectId}/decisions`, { method: "POST", body: { text: $("dec-text").value } });
  $("dec-text").value = ""; await loadContext();
}));

// ---------- brief ----------
const SECTIONS = [["requirements", "Requirements"], ["current_decisions", "Current decisions"], ["implementation_context", "Implementation context"],
  ["preferences", "Preferences"], ["acceptance_checks", "Acceptance checks"]];

function citeChips(keys) {
  const prov = Object.fromEntries((state.run.provenance || []).map((e) => [e.key, e]));
  return (keys || []).map((k) => {
    const e = prov[k]; if (!e) return null;
    const label = e.type === "user" ? "Your explicit request or clarification" : e.type === "source" ? `Source "${e.title}" rev ${e.revision}` : e.type === "decision" ? `Team decision rev ${e.revision} (owner ${e.owner_id})` : `Approved ${e.scope} lesson rev ${e.revision}`;
    return el("span", { class: "cite", title: `${label}\n\n${e.text}` }, k);
  });
}

function renderRun() {
  const r = state.run;
  const hasBrief = !!r?.brief;
  show("brief-card", hasBrief);
  show("result-card", hasBrief && ["exported", "reviewed"].includes(r.status));
  show("feedback-card", hasBrief && ["exported", "reviewed"].includes(r.status));
  show('preview-card', !!r?.artifact && r.artifact.brief_revision === r.brief_revision && r.status !== 'stale');
  $('preview-frame').srcdoc = r?.artifact?.html || '';
  show('handoff', false);
  if (!hasBrief) return;
  $("run-status").replaceChildren(chip(r.status));
  $("brief-rev").textContent = r.brief_revision ? `revision ${r.brief_revision} by the agent` : "";

  show("stale", r.status === "stale");
  if (r.status === "stale") {
    $("stale").replaceChildren(el("strong", {}, "Cited context changed since this brief was prepared. "),
      el("ul", {}, (r.changes || []).map((c) => el("li", {}, `${c.key} (${c.type}): ${c.change}`))),
      el("button", { onclick: () => tell(`The brief is stale: ${(r.changes || []).map((c) => `${c.key} ${c.change}`).join("; ")}. Please get the project context again and save an updated brief.`) }, "Ask the agent to redo it"));
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
    el("div", { class: "row" }, el("input", { id: `qa-${i}`, placeholder: "Answer (sent to the agent)" }),
      el("button", { class: "secondary", onclick: () => { const a = $(`qa-${i}`).value.trim(); if (a) tell(`Answer to "${q.text}": ${a}`); } }, "Answer")))));
  if ((r.answers || []).length) root.append(el("h3", {}, "Resolved"), el("ul", {}, r.answers.map((a) => el("li", {}, `${a.question} → ${a.answer}`))));
  if ((b.assumptions || []).length) root.append(el("h3", {}, "Assumptions"), el("ul", {}, b.assumptions.map((a) => el("li", {}, a))));
  if ((b.citation_warnings || []).length) root.append(el("p", { class: "uncited" }, `Dropped unknown citations: ${b.citation_warnings.join(", ")}`));
  root.querySelectorAll("[contenteditable]").forEach((n) => n.addEventListener("input", () => show("save-brief-btn")));
  show("save-brief-btn", false);

  const checks = b.acceptance_checks || [];
  const recorded = Object.fromEntries((r.checks || []).map((c, i) => [i, c]));
  $("outcome-checks").replaceChildren(...checks.map((c, i) => {
    const sel = el("select", { id: `oc-${i}` }, ...["not_run", "passed", "failed"].map((v) => el("option", { value: v }, v.replace("_", " "))));
    sel.value = recorded[i]?.result || "not_run";
    const ev = el("input", { id: `oe-${i}`, placeholder: "Evidence (what you saw)" }); ev.value = recorded[i]?.evidence || "";
    return el("li", {}, sel, c.text, citeChips(c.sources), ev);
  }));
  if (!checks.length) $("outcome-checks").append(el("li", { class: "muted" }, "The brief has no acceptance checks."));
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
  state.run = await api(`/runs/${state.run._id}`); renderRun(); show("handoff"); await loadContext();
}));

$("outcome-btn").addEventListener("click", (e) => busy(e.target, "Saving…", async () => {
  const n = (state.run.brief.acceptance_checks || []).length;
  const results = [...Array(n).keys()].map((i) => ({ index: i, result: $(`oc-${i}`).value, evidence: $(`oe-${i}`).value }));
  state.run = await api(`/runs/${state.run._id}/outcome`, { method: "POST", body: { results, tool: $("outcome-tool").value || null } });
  renderRun(); toast("Result recorded as outcome evidence.");
}));

// ---------- feedback -> proposed lesson -> approval ----------
$("feedback-btn").addEventListener("click", (e) => busy(e.target, "Saving…", async () => {
  const text = $("feedback-text").value.trim(); if (!text) throw new Error("Write the feedback first.");

  const r = await api(`/runs/${state.run._id}/feedback`, { method: "POST", body: { text, lesson: $("feedback-lesson").value } });
  renderProposal(r); await loadContext();
}));

function renderProposal(r) {
  const box = $("proposal"); box.replaceChildren();
  if (!r.proposed) { box.append(el("p", { class: "muted" }, "Feedback saved. No lesson was proposed.")); return; }
  const l = r.proposed;
  const allowed = r.scopes_allowed || ["personal"];
  const text = el("textarea", { rows: 2 }); text.value = l.text;
  const radio = (value, label) => el("label", { title: allowed.includes(value) ? "" : "Requires publisher or admin role" },
    el("input", { type: "radio", name: "scope", value, checked: value === "personal", disabled: !allowed.includes(value) }), label);
  box.append(el("div", { class: "proposal" },
    el("strong", {}, "Suggested lesson"), " ", chip("proposed"), text,
    r.duplicate_of ? el("p", { class: "uncited" }, `Looks like a duplicate of an existing lesson (${r.duplicate_of}).`) : null,
    (l.conflicts || []).length ? el("div", { class: "callout warn" }, el("strong", {}, "Conflicts with: "),
      el("ul", {}, l.conflicts.map((c) => el("li", {}, `${c.type}: ${c.text}`)))) : null,
    el("p", { class: "hint" }, "Who should this apply to?"),
    el("div", { class: "scopes" }, radio("personal", "Just me"), radio("project", "This project"), radio("team", "Whole team")),
    el("div", { class: "row" },
      el("button", { class: "secondary", onclick: (ev) => busy(ev.target, "…", async () => { await api(`/lessons/${l._id}/reject`, { method: "POST" }); box.replaceChildren(el("p", { class: "muted" }, "Rejected. Nothing was remembered.")); await loadContext(); }) }, "Don't remember"),
      el("span", { class: "spacer" }),
      el("button", { onclick: (ev) => busy(ev.target, "Saving…", async () => {
        const scope = box.querySelector("input[name=scope]:checked").value;
        await api(`/lessons/${l._id}/approve`, { method: "POST", body: { scope, text: text.value } });
        box.replaceChildren(el("p", {}, `Remembered at ${scope} scope. The next relevant request will cite it.`)); await loadContext();
      }) }, "Approve lesson"))));
}



setInterval(()=>{if(state.conversation) loadContext().catch(()=>{});},5000);
init().catch((e) => toast(e.message));
