import { Audio, Circle, Layout, Rect, Txt, TxtProps, makeScene2D } from "@revideo/2d";
import { ThreadGenerator, all, createRef, makeProject, sequence, useThread, waitFor } from "@revideo/core";
import {
  BRIEF, CHECKS_PF, CHECKS_PLAIN, EXCLUDED, HERO_OLD, HERO_RULE, INCLUDED, PROJECT, REQUEST, USER, type Card,
} from "./data";
import voiced from "./vo.json";

// ---------- look ----------
const C = {
  bg: "#0d0f14", surface: "#161a22", raised: "#1d222c", border: "#2a303c", text: "#e8eaf0", muted: "#8b93a5",
  accent: "#748ffc", accentDeep: "#3b5bdb", ok: "#69db7c", bad: "#ff8787", warn: "#ffc078", cite: "#23294a", citeText: "#bac8ff",
  warnTint: "#3a3020", warnSoft: "#2a2519",
};
const FONT = 'Inter, "Helvetica Neue", Arial, sans-serif';
const MONO = '"SF Mono", Menlo, monospace';

/** Place a node by its top-left corner in 1920×1080 screen pixels (Revideo's origin is the centre). */
const at = (left: number, top: number) => ({ x: left - 960, y: top - 540, offset: [-1, -1] as [number, number] });
const clip = (s: string, n: number) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);

function T(props: TxtProps) {
  return <Txt fontFamily={FONT} fill={C.text} {...props} />;
}
function Cite({ text, hero }: { text: string; hero?: boolean }) {
  return (
    <Rect layout padding={[4, 10]} radius={6} fill={hero ? C.warn : C.cite}>
      <Txt text={text} fontFamily={MONO} fontSize={18} fontWeight={600} fill={hero ? "#1a1300" : C.citeText} />
    </Rect>
  );
}

/** Fade nodes in one after another. */
const reveal = (gap: number, nodes: { opacity: (v: number, d: number) => ThreadGenerator }[], dur = 0.4) =>
  sequence(gap, ...nodes.map((n) => n.opacity(1, dur)));

/**
 * One scene: header, optional ElevenLabs narration, fade in, run `build`, hold until `len` seconds, fade out.
 * Narration plays only for scenes listed in vo.json (written by scripts/voiceover.mjs).
 */
const scene = (name: string, len: number, label: string | null, step: number | null, build: (root: Layout) => ThreadGenerator) =>
  makeScene2D(name, function* (view) {
    view.fill(C.bg);
    const root = createRef<Layout>();
    view.add(
      <Layout ref={root} opacity={0}>
        {label && (
          <Rect {...at(80, 46)} layout gap={16} alignItems="center">
            <Circle size={40} fill={C.accentDeep} layout justifyContent="center" alignItems="center">
              <T text={String(step)} fontSize={22} fontWeight={700} fill="#fff" />
            </Circle>
            <T text={label.toUpperCase()} fontSize={26} fontWeight={600} letterSpacing={1} fill={C.muted} />
          </Rect>
        )}
        <T x={880} y={-472} offsetX={1} fontSize={24} fontWeight={700}>
          Prompt<Txt fill={C.accent}>Forge</Txt>
        </T>
      </Layout>,
    );
    if ((voiced as string[]).includes(name)) view.add(<Audio src={`/vo/${name}.mp3`} play />);
    const start = useThread().time();
    yield* root().opacity(1, 0.3);
    yield* build(root());
    yield* waitFor(Math.max(0, len - 0.4 - (useThread().time() - start)));
    yield* root().opacity(0, 0.4);
  });

const caption = (root: Layout, children: any) => {
  const ref = createRef<Txt>();
  root.add(
    <T ref={ref} y={460} fontSize={38} fontWeight={600} opacity={0} textAlign="center">
      {children}
    </T>,
  );
  return ref;
};

// ---------- 1. hook (5s) ----------
const hook = scene("hook", 5, null, null, function* (root) {
  const a = createRef<Txt>(), b = createRef<Txt>();
  root.add(
    <Layout layout direction="column" alignItems="center" gap={36}>
      <T ref={a} opacity={0} text="Every AI session starts from zero." fontSize={76} fontWeight={800} />
      <T ref={b} opacity={0} fontSize={46} fill={C.muted}>
        PromptForge brings the context <Txt fill={C.accent}>your team already has</Txt>.
      </T>
    </Layout>,
  );
  yield* a().opacity(1, 0.6);
  yield* waitFor(0.4);
  yield* b().opacity(1, 0.6);
});

// ---------- 2. request (9s) ----------
const request = scene("request", 9, "The request", 1, function* (root) {
  const chips = createRef<Rect>(), box = createRef<Rect>(), typed = createRef<Txt>();
  root.add(
    <Layout {...at(200, 220)} layout direction="column" gap={24}>
      <Rect ref={chips} layout gap={20} opacity={0}>
        {[`User: ${USER.name}`, `Project: ${PROJECT.name}`, "Voice or text"].map((t) => (
          <Rect layout padding={[8, 16]} radius={10} stroke={C.border} lineWidth={1}>
            <T text={t} fontSize={24} fill={C.muted} />
          </Rect>
        ))}
      </Rect>
      <Rect ref={box} opacity={0} layout width={1520} height={230} padding={[40, 48]} radius={18} fill={C.surface} stroke={C.accentDeep} lineWidth={2}>
        <T ref={typed} text="" width={1424} textWrap fontSize={48} lineHeight={66} />
      </Rect>
    </Layout>,
  );
  const cap = caption(root, <>A plain model sees <Txt fill={C.bad}>one sentence</Txt>. Your team knows much more.</>);
  yield* all(chips().opacity(1, 0.4), box().opacity(1, 0.4));
  yield* typed().text(`“${REQUEST}”`, 4);
  yield* waitFor(0.6);
  yield* cap().opacity(1, 0.5);
});

// ---------- 3. context (13s) ----------
function MemoryCard({ c, refFn }: { c: Card; refFn: (r: Rect) => void }) {
  const color = c.kind === "Source" ? C.accent : c.kind === "Decision" ? C.ok : C.warn;
  return (
    <Rect ref={refFn} opacity={0} layout direction="column" gap={8} width={568} padding={[16, 20]} radius={14}
      fill={C.surface} stroke={C.border} lineWidth={2}>
      <Rect layout justifyContent="space-between" width={524}>
        <T text={clip(c.title.toUpperCase(), 30)} fontSize={17} fontWeight={700} letterSpacing={0.8} fill={color} />
        <T text={c.tag} fontFamily={MONO} fontSize={17} fill={C.muted} />
      </Rect>
      <T text={clip(c.text, 105)} width={524} textWrap fontSize={20} lineHeight={27} />
      {c.hero && <T text={`corrected: replaces “${clip(HERO_OLD.text, 40)}” (r1)`} width={524} textWrap fontSize={17} fill={C.warn} />}
    </Rect>
  );
}

const context = scene("context", 13, "Retrieve team context · MongoDB Atlas", 2, function* (root) {
  const cards: Rect[] = [], heads: Txt[] = [], excluded: Rect[] = [], reasons: Txt[] = [];
  let hero: Rect | null = null;
  const exHead = createRef<Txt>();
  const cols = [
    { title: "Sources", kind: "Source" },
    { title: "Team decisions", kind: "Decision" },
    { title: "Approved lessons", kind: "Lesson" },
  ];
  root.add(
    <Layout {...at(80, 130)} layout gap={28} alignItems="start">
      {cols.map((col) => (
        <Layout layout direction="column" gap={14}>
          <T ref={(r: Txt) => heads.push(r)} opacity={0} text={col.title} fontSize={22} fontWeight={700} fill={C.muted} />
          {INCLUDED.filter((c) => c.kind === col.kind).map((c) => (
            <MemoryCard c={c} refFn={(r) => { cards.push(r); if (c.hero) hero = r; }} />
          ))}
        </Layout>
      ))}
    </Layout>,
  );
  root.add(
    <Layout {...at(80, 720)} layout direction="column" gap={12}>
      <T ref={exHead} opacity={0} text="Filtered out by scope and status" fontSize={22} fontWeight={700} fill={C.muted} />
      <Layout layout wrap="wrap" gap={12} width={1760}>
        {EXCLUDED.map((x) => (
          <Rect ref={(r: Rect) => excluded.push(r)} opacity={0} layout direction="column" gap={4} width={578} padding={[10, 14]} radius={10}
            fill={C.raised} stroke={C.border} lineWidth={1}>
            <T text={clip(x.text, 52)} fontSize={18} />
            <T ref={(r: Txt) => reasons.push(r)} opacity={0} text={`✕ ${x.reason}`} fontSize={18} fontWeight={600} fill={C.bad} />
          </Rect>
        ))}
      </Layout>
    </Layout>,
  );
  const cap = caption(root, <>Only <Txt fill={C.ok}>approved</Txt>, <Txt fill={C.ok}>current</Txt>, in-scope memory reaches the brief.</>);

  yield* all(reveal(0.1, heads), reveal(0.25, cards));
  if (hero) yield* all(hero.stroke(C.warn, 0.5), hero.shadowColor(C.warn + "88", 0.5), hero.shadowBlur(36, 0.5));
  yield* all(exHead().opacity(1, 0.3), reveal(0.12, excluded));
  yield* sequence(0.3, ...excluded.map((e, i) => all(reasons[i].opacity(1, 0.3), e.opacity(0.55, 0.3))));
  yield* waitFor(0.4);
  yield* cap().opacity(1, 0.5);
});

// ---------- 4. brief (13s) ----------
const brief = scene("brief", 13, "Build a cited brief", 3, function* (root) {
  const rows: Layout[] = [], stats: Rect[] = [];
  const panel = createRef<Rect>();
  let last = "";
  root.add(
    <Rect ref={panel} opacity={0} {...at(80, 130)} layout direction="column" width={1180} height={800} padding={[28, 40]} radius={18}
      fill={C.surface} stroke={C.border} lineWidth={1}>
      {BRIEF.map((l, i) => {
        const head = l.section !== last;
        last = l.section;
        return (
          <Layout ref={(r: Layout) => rows.push(r)} opacity={0} layout direction="column">
            {head && <T text={l.section.toUpperCase()} fontSize={17} fontWeight={700} letterSpacing={1} fill={C.muted} marginTop={i ? 14 : 0} marginBottom={4} />}
            <Rect layout alignItems="center" gap={14} width={1100} padding={[5, 10]} radius={8}
              fill={l.hero ? C.warnTint : l.question ? C.warnSoft : null}>
              <T text={(l.question ? "? " : "") + l.text} fontSize={24} grow={1} />
              <Cite text={l.cite} hero={l.hero} />
            </Rect>
          </Layout>
        );
      })}
    </Rect>,
  );
  root.add(
    <Layout {...at(1310, 160)} layout direction="column" gap={28}>
      {[
        ["1 → 10", "sentence → cited instructions"],
        ["10 / 10", "instructions cite a revision"],
        ["1", "open question surfaced, not guessed"],
      ].map(([big, small]) => (
        <Rect ref={(r: Rect) => stats.push(r)} opacity={0} layout direction="column" width={530} padding={[24, 28]} radius={16}
          fill={C.surface} stroke={C.border} lineWidth={1}>
          <T text={big} fontSize={60} fontWeight={800} fill={C.accent} />
          <T text={small} fontSize={24} fill={C.muted} />
        </Rect>
      ))}
    </Layout>,
  );
  const cap = caption(root, "Every line points back to the source or memory it came from.");
  yield* panel().opacity(1, 0.4);
  yield* all(reveal(0.6, rows), sequence(2.2, ...stats.map((s) => s.opacity(1, 0.5))));
  yield* cap().opacity(1, 0.5);
});

// ---------- 5. result (12s) ----------
function Field({ label, bad, hint }: { label: string; bad?: boolean; hint?: string }) {
  return (
    <Layout layout direction="column" gap={4} width={380}>
      <Txt text={label} fontFamily={FONT} fontSize={15} fontWeight={600} fill={bad ? "#c92a2a" : "#1f2937"} />
      <Rect width={380} height={34} radius={8} fill={bad ? "#fff5f5" : "#ffffff"} stroke={bad ? "#c92a2a" : "#d1d5db"} lineWidth={1.5} />
      {hint && <Txt text={hint} fontFamily={FONT} fontSize={13} fill="#2b8a3e" />}
    </Layout>
  );
}

function PageMock({ good }: { good: boolean }) {
  return (
    <Rect layout direction="column" alignItems="center" width={850} height={470} padding={24} radius={12} fill={good ? "#ffffff" : "#f3f0ff"}>
      <Layout layout direction="column" gap={12} width={380}>
        <Txt text={good ? "Create your Lumen account" : "Join us today!!"} fontFamily={FONT} fontSize={24} fontWeight={700} fill="#1f2937" />
        <Field label="Work email" />
        {good ? <Field label="Full name" /> : <Field label="Phone number" bad />}
        <Field label="Password" hint={good ? "✓ 12+ characters   ○ one number" : undefined} />
        {good && <Field label="Workspace name" />}
        {good && <Txt text="☑ I agree to the Terms and Privacy Policy" fontFamily={FONT} fontSize={13} fill="#1f2937" />}
        <Rect layout justifyContent="center" alignItems="center" width={good ? 380 : 200} height={42} radius={good ? 8 : 21} fill={good ? "#3B5BDB" : "#e64980"}>
          <Txt text={good ? "Create account" : "Sign Up Now!"} fontFamily={FONT} fontSize={17} fontWeight={700} fill="#ffffff" />
        </Rect>
      </Layout>
    </Rect>
  );
}

const result = scene("result", 12, "Generate & check the React page", 4, function* (root) {
  const panels: Layout[] = [], plain: Rect[] = [], pf: Rect[] = [];
  const panel = (good: boolean) => (
    <Layout ref={(r: Layout) => panels.push(r)} opacity={0} layout direction="column" gap={14}>
      <T text={good ? "With the PromptForge brief" : "Same request, plain prompt"} fontSize={26} fontWeight={700} fill={good ? C.ok : C.bad} />
      <PageMock good={good} />
      <Layout layout direction="column" gap={8} marginTop={4}>
        {(good ? CHECKS_PF : CHECKS_PLAIN).map((c: any) => (
          <Rect ref={(r: Rect) => (good ? pf : plain).push(r)} opacity={0} layout alignItems="center" gap={12} width={850} padding={[2, 8]} radius={8}
            fill={c.hero ? C.warnTint : null}>
            <T text={c.ok ? "✓" : "✕"} fontSize={22} fontWeight={800} fill={c.ok ? C.ok : C.bad} />
            <T text={c.text} fontSize={22} grow={1} />
            {c.cite && <Cite text={c.cite} hero={c.hero} />}
          </Rect>
        ))}
      </Layout>
    </Layout>
  );
  root.add(
    <Layout {...at(80, 120)} layout gap={60}>
      {panel(false)}
      {panel(true)}
    </Layout>,
  );
  root.add(<T x={880} y={510} offsetX={1} text="Prototype render · one illustrative before/after, not a benchmark" fontSize={16} fill={C.muted} />);
  yield* sequence(0.8, ...panels.map((p) => p.opacity(1, 0.5)));
  yield* waitFor(0.5);
  yield* reveal(0.4, plain);
  yield* reveal(0.45, pf);
});

// ---------- 6. close (8s) ----------
const close = scene("close", 8, "Governed, auditable memory", 5, function* (root) {
  const rows: Rect[] = [];
  const note = createRef<Txt>(), logo = createRef<Layout>();
  const events = [
    { a: "created", t: HERO_OLD.text, who: HERO_OLD.owner_id, r: "r1", hero: false },
    { a: "superseded", t: HERO_RULE.text, who: HERO_RULE.owner_id, r: "r2", hero: true },
  ];
  root.add(
    <Layout {...at(200, 160)} layout direction="column" gap={8}>
      <T text="memory_events (append-only)" fontFamily={MONO} fontSize={22} fill={C.muted} marginBottom={4} />
      {events.map((e) => (
        <Rect ref={(r: Rect) => rows.push(r)} opacity={0} layout alignItems="center" gap={20} width={1520} padding={[14, 20]} radius={10}
          fill={e.hero ? C.warnTint : C.surface} stroke={e.hero ? C.warn : C.border} lineWidth={1}>
          <T text={e.a} fontFamily={MONO} fontSize={22} width={180} fill={e.hero ? C.warn : C.muted} />
          <T text={clip(e.t, 84)} fontSize={22} grow={1} />
          <T text={e.who} fontSize={22} width={90} fill={C.muted} />
          <T text={e.r} fontFamily={MONO} fontSize={22} width={40} />
        </Rect>
      ))}
      <T ref={note} opacity={0} marginTop={14} fontSize={30} fill={C.muted}
        text="One correction, made once, by its owner, shapes every teammate's next prompt." />
    </Layout>,
  );
  root.add(
    <Layout ref={logo} opacity={0} y={300} layout direction="column" alignItems="center" gap={10}>
      <T fontSize={84} fontWeight={800}>Prompt<Txt fill={C.accent}>Forge</Txt></T>
      <T text="Say what you want to build. We bring the context your team already has." fontSize={30} fill={C.muted} />
      <Layout layout gap={14} marginTop={16}>
        {["MongoDB Atlas Vector Search", "Voyage AI", "ElevenLabs Agents", "LangSmith"].map((s) => (
          <Rect layout padding={[8, 16]} radius={999} stroke={C.border} lineWidth={1}>
            <T text={s} fontSize={20} />
          </Rect>
        ))}
      </Layout>
    </Layout>,
  );
  yield* reveal(0.6, rows);
  yield* note().opacity(1, 0.5);
  yield* waitFor(1);
  yield* logo().opacity(1, 0.6);
});

export default makeProject({
  scenes: [hook, request, context, brief, result, close],
  settings: { shared: { size: { x: 1920, y: 1080 } } },
});
