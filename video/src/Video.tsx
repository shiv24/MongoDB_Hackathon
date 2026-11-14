import React from "react";
import { AbsoluteFill, Easing, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  BRIEF, CHECKS_PF, CHECKS_PLAIN, EXCLUDED, HERO_OLD, HERO_RULE, INCLUDED, PROJECT, REQUEST, USER, type Card,
} from "./data";

// ---------- timing (30 fps) ----------
const S = { hook: [0, 150], request: [150, 270], context: [420, 390], brief: [810, 390], result: [1200, 360], close: [1560, 240] } as const;
export const TOTAL = 1800;

// ---------- look ----------
const C = {
  bg: "#0d0f14", surface: "#161a22", raised: "#1d222c", border: "#2a303c", text: "#e8eaf0", muted: "#8b93a5",
  accent: "#748ffc", accentDeep: "#3b5bdb", ok: "#69db7c", bad: "#ff8787", warn: "#ffc078", cite: "#23294a", citeText: "#bac8ff",
};
const FONT = 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif';
const MONO = '"SF Mono", ui-monospace, Menlo, monospace';

const fade = (f: number, start: number, dur = 15) =>
  interpolate(f, [start, start + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
const rise = (f: number, start: number, dur = 18) => ({
  opacity: fade(f, start, dur),
  transform: `translateY(${(1 - fade(f, start, dur)) * 24}px)`,
});
const outro = (f: number, len: number) => interpolate(f, [len - 12, len], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const Frame: React.FC<{ len: number; children: React.ReactNode; label?: string; step?: number }> = ({ len, children, label, step }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg, color: C.text, fontFamily: FONT, opacity: Math.min(fade(f, 0, 10), outro(f, len)) }}>
      {label && (
        <div style={{ position: "absolute", top: 48, left: 80, display: "flex", alignItems: "center", gap: 16, fontSize: 26, color: C.muted, ...rise(f, 0) }}>
          {step && <span style={{ width: 40, height: 40, borderRadius: 20, background: C.accentDeep, color: "#fff", display: "grid", placeItems: "center", fontWeight: 700 }}>{step}</span>}
          <span style={{ letterSpacing: 1, textTransform: "uppercase", fontWeight: 600 }}>{label}</span>
        </div>
      )}
      <div style={{ position: "absolute", top: 52, right: 80, fontSize: 24, fontWeight: 700, color: C.text, opacity: 0.85 }}>
        Prompt<span style={{ color: C.accent }}>Forge</span>
      </div>
      {children}
    </AbsoluteFill>
  );
};

const Caption: React.FC<{ at: number; children: React.ReactNode }> = ({ at, children }) => {
  const f = useCurrentFrame();
  return (
    <div style={{ position: "absolute", bottom: 56, left: 0, right: 0, textAlign: "center", fontSize: 38, fontWeight: 600, ...rise(f, at) }}>
      {children}
    </div>
  );
};

const Cite: React.FC<{ children: React.ReactNode; hero?: boolean }> = ({ children, hero }) => (
  <span style={{ fontFamily: MONO, fontSize: 18, padding: "3px 10px", borderRadius: 6, whiteSpace: "nowrap",
    background: hero ? C.warn : C.cite, color: hero ? "#1a1300" : C.citeText, fontWeight: 600 }}>{children}</span>
);

// ---------- 1. hook ----------
const Hook = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: f - 40, fps, config: { damping: 14 } });
  return (
    <Frame len={S.hook[1]}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center", padding: 120 }}>
        <div style={{ fontSize: 76, fontWeight: 800, lineHeight: 1.15, ...rise(f, 5) }}>Every AI session starts from zero.</div>
        <div style={{ fontSize: 46, color: C.muted, marginTop: 36, opacity: pop, transform: `scale(${0.9 + pop * 0.1})` }}>
          PromptForge brings the context <span style={{ color: C.accent }}>your team already has</span>.
        </div>
      </AbsoluteFill>
    </Frame>
  );
};

// ---------- 2. request ----------
const Request = () => {
  const f = useCurrentFrame();
  const typed = REQUEST.slice(0, Math.floor(interpolate(f, [25, 150], [0, REQUEST.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })));
  const cursor = Math.floor(f / 15) % 2 === 0 && f < 175;
  return (
    <Frame len={S.request[1]} label="The request" step={1}>
      <div style={{ position: "absolute", top: 220, left: 200, right: 200, ...rise(f, 4) }}>
        <div style={{ display: "flex", gap: 20, marginBottom: 24, fontSize: 24, color: C.muted }}>
          <span style={{ padding: "8px 16px", border: `1px solid ${C.border}`, borderRadius: 10 }}>👤 {USER.name}</span>
          <span style={{ padding: "8px 16px", border: `1px solid ${C.border}`, borderRadius: 10 }}>📁 {PROJECT.name}</span>
          <span style={{ padding: "8px 16px", border: `1px solid ${C.border}`, borderRadius: 10 }}>🎙 voice or text</span>
        </div>
        <div style={{ background: C.surface, border: `2px solid ${C.accentDeep}`, borderRadius: 18, padding: "40px 48px", fontSize: 48, lineHeight: 1.35, minHeight: 230 }}>
          “{typed}{cursor && <span style={{ color: C.accent }}>▍</span>}”
        </div>
      </div>
      <Caption at={185}>
        A plain model sees <span style={{ color: C.bad }}>one sentence</span>. Your team knows much more.
      </Caption>
    </Frame>
  );
};

// ---------- 3. context ----------
const MemoryCard: React.FC<{ c: Card; at: number }> = ({ c, at }) => {
  const f = useCurrentFrame();
  const color = c.kind === "Source" ? C.accent : c.kind === "Decision" ? C.ok : C.warn;
  const glow = c.hero ? interpolate(f, [at + 60, at + 80], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
  return (
    <div style={{ background: C.surface, borderRadius: 14, padding: "16px 20px", border: `2px solid ${glow ? C.warn : C.border}`,
      boxShadow: glow ? `0 0 ${36 * glow}px ${C.warn}66` : "none", ...rise(f, at) }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 17, marginBottom: 8 }}>
        <span style={{ color, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.8 }}>{c.title}</span>
        <span style={{ color: C.muted, fontFamily: MONO }}>{c.tag}</span>
      </div>
      <div style={{ fontSize: 20, lineHeight: 1.35, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{c.text}</div>
      {c.hero && (
        <div style={{ marginTop: 8, fontSize: 17, color: C.warn, opacity: glow }}>
          corrected: replaces “{HERO_OLD.text.slice(0, 44)}…” (r1)
        </div>
      )}
    </div>
  );
};

const Context = () => {
  const f = useCurrentFrame();
  const cols: { title: string; kind: string }[] = [
    { title: "Sources", kind: "Source" },
    { title: "Team decisions", kind: "Decision" },
    { title: "Approved lessons", kind: "Lesson" },
  ];
  const exAt = 170;
  return (
    <Frame len={S.context[1]} label="Retrieve team context · MongoDB Atlas" step={2}>
      <div style={{ position: "absolute", top: 130, left: 80, right: 80, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 28 }}>
        {cols.map((col, ci) => (
          <div key={col.kind} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 22, color: C.muted, fontWeight: 700, ...rise(f, ci * 10) }}>{col.title}</div>
            {INCLUDED.filter((c) => c.kind === col.kind).map((c, i) => <MemoryCard key={c.id} c={c} at={12 + ci * 30 + i * 12} />)}
          </div>
        ))}
      </div>
      <div style={{ position: "absolute", top: 720, left: 80, right: 80, ...rise(f, exAt - 10) }}>
        <div style={{ fontSize: 22, color: C.muted, fontWeight: 700, marginBottom: 12 }}>Filtered out by scope and status</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {EXCLUDED.map((x, i) => {
            const strike = fade(f, exAt + 20 + i * 10, 12);
            return (
              <div key={i} style={{ background: C.raised, borderRadius: 10, padding: "10px 14px", border: `1px solid ${C.border}`,
                opacity: (1 - strike * 0.45) * fade(f, exAt + i * 6), fontSize: 18 }}>
                <div style={{ textDecoration: strike > 0.5 ? "line-through" : "none", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{x.text}</div>
                <div style={{ color: C.bad, fontWeight: 600, marginTop: 4, opacity: strike }}>✕ {x.reason}</div>
              </div>
            );
          })}
        </div>
      </div>
      <Caption at={300}>
        Only <span style={{ color: C.ok }}>approved</span>, <span style={{ color: C.ok }}>current</span>, in-scope memory reaches the brief.
      </Caption>
    </Frame>
  );
};

// ---------- 4. brief ----------
const Brief = () => {
  const f = useCurrentFrame();
  let last = "";
  return (
    <Frame len={S.brief[1]} label="Build a cited brief" step={3}>
      <div style={{ position: "absolute", top: 130, left: 80, width: 1180, bottom: 150, background: C.surface, borderRadius: 18,
        border: `1px solid ${C.border}`, padding: "28px 40px", ...rise(f, 0) }}>
        {BRIEF.map((l, i) => {
          const at = 15 + i * 20;
          const head = l.section !== last;
          last = l.section;
          return (
            <div key={i}>
              {head && <div style={{ fontSize: 17, color: C.muted, textTransform: "uppercase", letterSpacing: 1, fontWeight: 700, marginTop: i ? 14 : 0, marginBottom: 4, opacity: fade(f, at) }}>{l.section}</div>}
              <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 24, padding: "5px 10px", borderRadius: 8,
                background: l.hero ? `${C.warn}22` : l.question ? `${C.warn}11` : "transparent",
                borderLeft: l.question ? `4px solid ${C.warn}` : "4px solid transparent", ...rise(f, at, 14) }}>
                <span style={{ flex: 1 }}>{l.question ? "? " : ""}{l.text}</span>
                <Cite hero={l.hero}>{l.cite}</Cite>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", top: 160, left: 1310, right: 80, display: "flex", flexDirection: "column", gap: 28 }}>
        {[
          { big: "1 → 10", small: "sentence → cited instructions", at: 60 },
          { big: "10 / 10", small: "instructions cite a revision", at: 150 },
          { big: "1", small: "open question surfaced, not guessed", at: 220 },
        ].map((s) => (
          <div key={s.big} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, padding: "24px 28px", ...rise(f, s.at) }}>
            <div style={{ fontSize: 60, fontWeight: 800, color: C.accent }}>{s.big}</div>
            <div style={{ fontSize: 24, color: C.muted }}>{s.small}</div>
          </div>
        ))}
      </div>
      <Caption at={260}>Every line points back to the source or memory it came from.</Caption>
    </Frame>
  );
};

// ---------- 5. result ----------
const Field: React.FC<{ label: string; bad?: boolean; children?: React.ReactNode }> = ({ label, bad, children }) => (
  <div style={{ marginBottom: 12 }}>
    <div style={{ fontSize: 15, color: bad ? "#c92a2a" : "#1f2937", fontWeight: 600, marginBottom: 4 }}>{label}</div>
    <div style={{ height: 34, border: `1.5px solid ${bad ? "#c92a2a" : "#d1d5db"}`, borderRadius: 8, background: bad ? "#fff5f5" : "#fff" }} />
    {children}
  </div>
);

const PageMock: React.FC<{ good: boolean }> = ({ good }) => (
  <div style={{ background: good ? "#fff" : "#f3f0ff", borderRadius: 12, padding: 24, color: "#1f2937", fontFamily: "system-ui", height: 470 }}>
    <div style={{ maxWidth: 380, margin: "0 auto" }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 14 }}>{good ? "Create your Lumen account" : "Join us today!!"}</div>
      <Field label="Work email" />
      {good ? <Field label="Full name" /> : <Field label="Phone number" bad />}
      <Field label="Password">
        {good && <div style={{ fontSize: 13, color: "#2b8a3e", marginTop: 4 }}>✓ 12+ characters &nbsp; ○ one number</div>}
      </Field>
      {good && <Field label="Workspace name" />}
      {good && <div style={{ fontSize: 13, marginBottom: 12 }}>☑ I agree to the Terms and Privacy Policy</div>}
      <div style={{ height: 42, borderRadius: good ? 8 : 21, background: good ? "#3B5BDB" : "#e64980", color: "#fff", display: "grid", placeItems: "center", fontWeight: 700, width: good ? "100%" : 200 }}>
        {good ? "Create account" : "Sign Up Now!"}
      </div>
    </div>
  </div>
);

const Result = () => {
  const f = useCurrentFrame();
  const panel = (good: boolean, at: number) => {
    const checks = good ? CHECKS_PF : CHECKS_PLAIN;
    return (
      <div style={{ flex: 1, ...rise(f, at) }}>
        <div style={{ fontSize: 26, fontWeight: 700, marginBottom: 14, color: good ? C.ok : C.bad }}>
          {good ? "With the PromptForge brief" : "Same request, plain prompt"}
        </div>
        <PageMock good={good} />
        <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 8 }}>
          {checks.map((c, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 22, ...rise(f, at + 50 + i * 14, 12),
              ...(("hero" in c && c.hero) ? { background: `${C.warn}22`, borderRadius: 8, padding: "2px 8px" } : {}) }}>
              <span style={{ color: c.ok ? C.ok : C.bad, fontWeight: 800 }}>{c.ok ? "✓" : "✕"}</span>
              <span style={{ flex: 1 }}>{c.text}</span>
              {"cite" in c && <Cite hero={"hero" in c && !!c.hero}>{String(c.cite)}</Cite>}
            </div>
          ))}
        </div>
      </div>
    );
  };
  return (
    <Frame len={S.result[1]} label="Generate & check the React page" step={4}>
      <div style={{ position: "absolute", top: 120, left: 80, right: 80, display: "flex", gap: 60 }}>
        {panel(false, 5)}
        {panel(true, 30)}
      </div>
      <div style={{ position: "absolute", bottom: 20, right: 80, fontSize: 16, color: C.muted }}>Prototype render · one illustrative before/after, not a benchmark</div>
    </Frame>
  );
};

// ---------- 6. close ----------
const Close = () => {
  const f = useCurrentFrame();
  return (
    <Frame len={S.close[1] + 12} label="Governed, auditable memory" step={5}>
      <div style={{ position: "absolute", top: 160, left: 200, right: 200, ...rise(f, 5) }}>
        <div style={{ fontSize: 22, color: C.muted, marginBottom: 12, fontFamily: MONO }}>memory_events (append-only)</div>
        {[
          { a: "created", t: HERO_OLD.text, who: HERO_OLD.owner_id, r: "r1" },
          { a: "superseded", t: HERO_RULE.text, who: HERO_RULE.owner_id, r: "r2", hero: true },
        ].map((e, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "180px 1fr 100px 60px", gap: 20, alignItems: "center", fontSize: 22,
            padding: "14px 20px", borderRadius: 10, marginBottom: 8, background: e.hero ? `${C.warn}22` : C.surface,
            border: `1px solid ${e.hero ? C.warn : C.border}`, ...rise(f, 10 + i * 18) }}>
            <span style={{ fontFamily: MONO, color: e.hero ? C.warn : C.muted }}>{e.a}</span>
            <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{e.t}</span>
            <span style={{ color: C.muted }}>{e.who}</span>
            <span style={{ fontFamily: MONO }}>{e.r}</span>
          </div>
        ))}
        <div style={{ fontSize: 30, marginTop: 20, color: C.muted, ...rise(f, 50) }}>
          One correction, made once, by its owner, shapes every teammate's next prompt.
        </div>
      </div>
      <div style={{ position: "absolute", bottom: 110, left: 0, right: 0, textAlign: "center", ...rise(f, 110) }}>
        <div style={{ fontSize: 84, fontWeight: 800 }}>Prompt<span style={{ color: C.accent }}>Forge</span></div>
        <div style={{ fontSize: 30, color: C.muted, marginTop: 8 }}>Say what you want to build. We bring the context your team already has.</div>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", marginTop: 26 }}>
          {["MongoDB Atlas Vector Search", "Voyage AI", "ElevenLabs Agents", "LangSmith"].map((s) => (
            <span key={s} style={{ fontSize: 20, padding: "8px 16px", borderRadius: 999, border: `1px solid ${C.border}`, color: C.text }}>{s}</span>
          ))}
        </div>
      </div>
    </Frame>
  );
};

export const PromptForgeDemo = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    <Sequence from={S.hook[0]} durationInFrames={S.hook[1]}><Hook /></Sequence>
    <Sequence from={S.request[0]} durationInFrames={S.request[1]}><Request /></Sequence>
    <Sequence from={S.context[0]} durationInFrames={S.context[1]}><Context /></Sequence>
    <Sequence from={S.brief[0]} durationInFrames={S.brief[1]}><Brief /></Sequence>
    <Sequence from={S.result[0]} durationInFrames={S.result[1]}><Result /></Sequence>
    <Sequence from={S.close[0]} durationInFrames={S.close[1]}><Close /></Sequence>
  </AbsoluteFill>
);
