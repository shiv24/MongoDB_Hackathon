// PromptForge UI: request -> cited brief -> export or run -> result -> feedback -> approved lesson.
// All text from the server is inserted with textContent (never innerHTML).

const $ = (id) => document.getElementById(id);
const state = { me: null, projectId: null, run: null, context: null };

// ---------- helpers ----------
async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {},
    credentials: "same-origin", ...opts,
    body: opts.body && !(opts.body instanceof FormData) ? JSON.stringify(opts.body) : opts.body,
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

function toast(msg) { const t = $("toast"); t.textContent = msg; t.classList.remove("hidden"); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.add("hidden"), 5000); }

async function busy(btn, label, fn) {
  const old = btn.textContent; btn.disabled = true; btn.textContent = label;
  try { return await fn(); } catch (e) { toast(e.message); throw e; } finally { btn.disabled = false; btn.textContent = old; }
}

const show = (id, on = true) => $(id).classList.toggle("hidden", !on);
const chip = (text) => el("span", { class: `chip ${text}` }, String(text).replace("_", " "));

// ---------- login and projects ----------
async function init() {
  const users = await api("/users");
  for (const u of users) $("user-select").append(el("option", { value: u._id }, u.name));
  try { state.me = await api("/me"); $("user-select").value = state.me.user_id; await loadProjects(); } catch { /* not logged in */ }
}

$("user-select").addEventListener("change", async (e) => {
  if (!e.target.value) return;
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

$("project-select").addEventListener("change", async (e) => { state.projectId = e.target.value; state.run = null; renderRun(); await loadContext(); });

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
      if (!confirm("Forget this lesson? It is removed from future use and briefs that cited it are marked stale. Text already in past briefs or artifacts is not erased.")) return;
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

// ---------- request ----------
$("build-btn").addEventListener("click", (e) => busy(e.target, "Finding context…", async () => {
  if (!state.projectId) throw new Error("Choose a user and project first.");
  state.run = await api("/runs", { method: "POST", body: { project_id: state.projectId, request: $("request-text").value } });
  $("proposal").replaceChildren(); renderRun(); await loadContext();
}));

$("clarify-btn").addEventListener("click", (e) => busy(e.target, "Building…", async () => {
  state.run = await api(`/runs/${state.run._id}/clarify`, { method: "POST", body: { answer: $("clarify-a").value } });
  renderRun(); renderContext();
}));

// voice: browser records, our backend forwards to ElevenLabs; the key never reaches the browser
let recorder = null;
$("mic-btn").addEventListener("click", async () => {
  if (recorder && recorder.state === "recording") { recorder.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const chunks = []; recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (ev) => chunks.push(ev.data);
    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      $("mic-btn").textContent = "🎙 Speak"; $("mic-status").textContent = "Transcribing…";
      const fd = new FormData(); fd.append("audio", new Blob(chunks, { type: recorder.mimeType }), "request.webm");
      try { const { text } = await api("/transcribe", { method: "POST", body: fd }); $("request-text").value = text; $("mic-status").textContent = "Review the transcript, then build."; }
      catch (err) { $("mic-status").textContent = ""; toast(`Voice failed (${err.message}). Type the request instead.`); }
    };
    recorder.start(); $("mic-btn").textContent = "■ Stop"; $("mic-status").textContent = "Listening…";
  } catch (err) { toast(`Microphone unavailable: ${err.message}`); }
});

// ---------- brief ----------
const SECTIONS = [["requirements", "Requirements"], ["current_decisions", "Current decisions"], ["implementation_context", "Implementation context"],
  ["preferences", "Preferences"], ["acceptance_checks", "Acceptance checks"]];

function citeChips(keys) {
  const prov = Object.fromEntries((state.run.provenance || []).map((e) => [e.key, e]));
  return (keys || []).map((k) => {
    const e = prov[k]; if (!e) return null;
    const label = e.type === "source" ? `Source "${e.title}" rev ${e.revision}` : e.type === "decision" ? `Team decision rev ${e.revision} (owner ${e.owner_id})` : `Approved ${e.scope} lesson rev ${e.revision}`;
    return el("span", { class: "cite", title: `${label}\n\n${e.text}` }, k);
  });
}

function renderRun() {
  const r = state.run;
  show("brief-card", !!r?.brief); show("result-card", !!r?.artifact); show("feedback-card", !!r?.artifact);
  show("clarify", r?.status === "needs_clarification");
  if (!r) return;
  if (r.status === "needs_clarification") { $("clarify-q").textContent = r.question; return; }
  $("run-status").replaceChildren(chip(r.status));

  const stale = r.status === "stale";
  show("stale", stale);
  if (stale) {
    $("stale").replaceChildren(el("strong", {}, "Cited context changed since this brief was prepared. "), r.stale_reason || "",
      el("ul", {}, (r.changes || []).map((c) => el("li", {}, `${c.key} (${c.type}): ${c.change}`))),
      el("button", { onclick: (ev) => busy(ev.target, "Refreshing…", async () => { state.run = await api(`/runs/${r._id}/refresh`, { method: "POST" }); renderRun(); renderContext(); }) }, "Refresh brief"));
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
    el("div", { class: "row" }, el("input", { id: `qa-${i}`, placeholder: "Answer" }),
      el("button", { class: "secondary", onclick: (ev) => answerQuestion(ev.target, i) }, "Answer")))));
  if ((r.answers || []).length || r.clarification) {
    root.append(el("h3", {}, "Resolved"), el("ul", {}, [r.clarification, ...(r.answers || [])].filter(Boolean).map((a) => el("li", {}, `${a.question} → ${a.answer}`))));
  }
  if ((b.assumptions || []).length) root.append(el("h3", {}, "Assumptions"), el("ul", {}, b.assumptions.map((a) => el("li", {}, a))));
  if ((b.citation_warnings || []).length) root.append(el("p", { class: "uncited" }, `Dropped unknown citations: ${b.citation_warnings.join(", ")}`));
  root.querySelectorAll("[contenteditable]").forEach((n) => n.addEventListener("input", () => show("save-brief-btn")));
  show("save-brief-btn", false);

  if (r.artifact) {
    $("artifact").srcdoc = r.artifact.html;
    $("checks").replaceChildren(...(r.checks || []).map((c) => el("li", {}, chip(c.result), " ", c.name, " ",
      el("span", { class: "chip" }, c.method === "static" ? "static check" : "model review"),
      c.evidence ? el("span", { class: "evidence" }, c.evidence) : null)));
  }
}

async function answerQuestion(btn, i) {
  const answer = $(`qa-${i}`).value.trim(); if (!answer) return;
  await busy(btn, "Updating…", async () => { state.run = await api(`/runs/${state.run._id}/answers`, { method: "POST", body: { answers: [{ index: i, answer }] } }); renderRun(); renderContext(); });
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

$("export-btn").addEventListener("click", (e) => busy(e.target, "Exporting…", async () => {
  const md = await api(`/runs/${state.run._id}/export`);
  const a = el("a", { href: URL.createObjectURL(new Blob([md], { type: "text/markdown" })), download: "promptforge-brief.md" });
  a.click(); URL.revokeObjectURL(a.href);
  try { await navigator.clipboard.writeText(md); toast("Brief downloaded and copied to clipboard."); } catch { toast("Brief downloaded."); }
  state.run = await api(`/runs/${state.run._id}`); renderRun();
}));

$("run-btn").addEventListener("click", (e) => busy(e.target, "Rechecking memory and generating…", async () => {
  try { state.run = await api(`/runs/${state.run._id}/execute`, { method: "POST" }); }
  catch (err) { if (err.status === 409) state.run = await api(`/runs/${state.run._id}`); renderRun(); throw err; }
  renderRun(); await loadContext();
}));

// ---------- feedback -> proposed lesson -> approval ----------
$("feedback-btn").addEventListener("click", (e) => busy(e.target, "Thinking…", async () => {
  const r = await api(`/runs/${state.run._id}/feedback`, { method: "POST", body: { text: $("feedback-text").value } });
  renderProposal(r);
}));

function renderProposal(r) {
  const box = $("proposal"); box.replaceChildren();
  if (!r.proposed) { box.append(el("p", { class: "muted" }, r.reason)); return; }
  const l = r.proposed;
  const canTeam = ["publisher", "admin"].includes(state.me.role);
  const text = el("textarea", { rows: 2 }); text.value = l.text;
  box.append(el("div", { class: "proposal" },
    el("strong", {}, "Suggested lesson"), " ", chip("proposed"), text,
    l.duplicate_of ? el("p", { class: "uncited" }, `Looks like a duplicate of an existing lesson (${l.duplicate_of}).`) : null,
    (l.conflicts || []).length ? el("div", { class: "callout warn" }, el("strong", {}, "Conflicts with: "),
      el("ul", {}, l.conflicts.map((c) => el("li", {}, `${c.type}: ${c.text}`)))) : null,
    el("p", { class: "hint" }, `Evidence: your feedback on run ${l.evidence_run_id.slice(0, 8)}. Who should this apply to?`),
    el("div", { class: "scopes" },
      el("label", {}, el("input", { type: "radio", name: "scope", value: "personal", checked: true }), "Just me"),
      el("label", {}, el("input", { type: "radio", name: "scope", value: "project" }), "This project"),
      el("label", { title: canTeam ? "" : "Requires publisher or admin role" }, el("input", { type: "radio", name: "scope", value: "team", disabled: !canTeam }), "Whole team")),
    el("div", { class: "row" },
      el("button", { class: "secondary", onclick: (ev) => busy(ev.target, "…", async () => { await api(`/lessons/${l._id}/reject`, { method: "POST" }); box.replaceChildren(el("p", { class: "muted" }, "Rejected. Nothing was remembered.")); await loadContext(); }) }, "Don't remember"),
      el("span", { class: "spacer" }),
      el("button", { onclick: (ev) => busy(ev.target, "Saving…", async () => {
        const scope = box.querySelector("input[name=scope]:checked").value;
        await api(`/lessons/${l._id}/approve`, { method: "POST", body: { scope, text: text.value } });
        box.replaceChildren(el("p", {}, `Remembered at ${scope} scope. The next relevant request will cite it.`)); await loadContext();
      }) }, "Approve lesson"))));
}

init().catch((e) => toast(e.message));
