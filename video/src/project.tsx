import { Audio, Img, Layout, Node, Rect, Txt, TxtProps, makeScene2D } from "@revideo/2d";
import { ThreadGenerator, all, createRef, easeInOutCubic, makeProject, sequence, useThread, waitFor } from "@revideo/core";
import { HERO_OLD, HERO_RULE } from "./data";
import vo from "./vo.json";

// ---------- look: matches the app's current UI (frontend/styles.css) ----------
const C = {
  bg: "#f5f4ef", surface: "#fffefa", text: "#202c28", muted: "#65716b", border: "#dedfd5",
  accent: "#245d47", soft: "#e8efe5", lime: "#ddeb9a", warn: "#b36200", warnSoft: "#fbf0dc", bad: "#b42323",
};
const SANS = 'Inter, "Helvetica Neue", Arial, sans-serif';
const SERIF = 'Georgia, "Times New Roman", serif';
const MONO = '"SF Mono", Menlo, monospace';

/** Hard limit: the whole video must stay within 60 seconds. */
const MAX_TOTAL = 60;
const PAD = 0.35;
const clips = vo as Record<string, number>;
const MIN: Record<string, number> = { hook: 5, request: 8, brief: 10, govern: 11, team: 6.5, access: 6.5, close: 5.5 };
const len = (name: string) => Math.max(MIN[name], (clips[name] ?? 0) + PAD);
const total = Object.keys(MIN).reduce((s, n) => s + len(n), 0);
if (total > MAX_TOTAL) throw new Error(`Video is ${total.toFixed(2)}s; shorten the narration to stay within ${MAX_TOTAL}s`);

function T(props: TxtProps) {
  return <Txt fontFamily={SANS} fill={C.text} {...props} />;
}
function Logo({ size = 26 }: { size?: number }) {
  return (
    <Layout layout gap={size * 0.45} alignItems="center">
      <Rect layout width={size * 1.3} height={size * 1.3} radius={size * 0.4} fill={C.accent} justifyContent="center" alignItems="center">
        <Txt text="✳" fontSize={size} fill={C.lime} />
      </Rect>
      <T text="PromptForge" fontSize={size} fontWeight={700} letterSpacing={-size * 0.03} />
    </Layout>
  );
}
function Pill({ text, color = "#ffffff", fill = C.accent, size = 24 }: { text: string; color?: string; fill?: string; size?: number }) {
  return (
    <Rect layout padding={[size * 0.35, size * 0.7]} radius={999} fill={fill} shadowColor="#1f3a2a33" shadowBlur={18} shadowOffsetY={4}>
      <T text={text} fontSize={size} fontWeight={600} fill={color} />
    </Rect>
  );
}

/**
 * One scene: brand header, optional ElevenLabs narration from vo.json, fade in, run `build`,
 * hold until the scene's length (narration + padding), fade out.
 */
const scene = (name: string, build: (root: Layout) => ThreadGenerator, header = true) =>
  makeScene2D(name, function* (view) {
    view.fill(C.bg);
    const root = createRef<Layout>();
    view.add(
      <Layout ref={root} opacity={0}>
        {header && <Layout layout x={-960 + 70} y={-540 + 58} offset={[-1, 0]}><Logo size={22} /></Layout>}
      </Layout>,
    );
    if (clips[name]) view.add(<Audio src={`/vo/${name}.mp3`} play />);
    const start = useThread().time();
    yield* root().opacity(1, 0.3);
    yield* build(root());
    yield* waitFor(Math.max(0, len(name) - 0.35 - (useThread().time() - start)));
    yield* root().opacity(0, 0.35);
  });

/** Caption shown above the screen frame. */
const caption = (root: Layout, text: string) => {
  const ref = createRef<Txt>();
  root.add(<T ref={ref} y={-462} fontFamily={SERIF} fontSize={44} letterSpacing={-1} text={text} opacity={0} />);
  return ref;
};

// ---------- screen frame with a camera over a real UI screenshot ----------
// Screenshots are 1920×1080 captures of the running app (scripts/capture.mjs).
const FRAME = { w: 1564, h: 880, y: 70 };
const BASE = FRAME.h / 1080;

type Screen = { frame: Node; cam: Node; img: Img; hl: (x: number, y: number, w: number, h: number, label?: string) => Rect };

function screen(root: Layout, src: string): Screen {
  const frame = createRef<Node>(), cam = createRef<Node>(), img = createRef<Img>();
  // The shadow sits on a separate backing card: a shadow on the clipping Rect hides its animated children.
  root.add(
    <Node ref={frame} opacity={0}>
      <Rect y={FRAME.y} width={FRAME.w} height={FRAME.h} radius={22} fill={C.bg} shadowColor="#1f3a2a22" shadowBlur={60} shadowOffsetY={18} />
      <Rect y={FRAME.y} width={FRAME.w} height={FRAME.h} radius={22} fill={C.bg} clip stroke={C.border} lineWidth={2}>
        <Node ref={cam} scale={BASE}>
          <Img ref={img} src={src} width={1920} height={1080} />
        </Node>
      </Rect>
    </Node>,
  );
  /** A highlight box in screenshot pixel coordinates, with an optional tag above it. */
  const hl = (x: number, y: number, w: number, h: number, label?: string) => {
    const r = createRef<Rect>();
    cam().add(
      <Rect ref={r} x={x + w / 2 - 960} y={y + h / 2 - 540} width={w + 16} height={h + 12} radius={12}
        stroke={C.warn} lineWidth={5} fill={"#ffb02e18"} opacity={0}>
        {label && (
          <Rect layout y={-(h + 12) / 2 - 26} offsetX={-1} x={-(w + 16) / 2} padding={[6, 14]} radius={8} fill={C.warn}>
            <T text={label} fontSize={22} fontWeight={700} fill="#fff" />
          </Rect>
        )}
      </Rect>,
    );
    return r();
  };
  return { frame: frame(), cam: cam(), img: img(), hl };
}

/** Move the camera so screenshot pixel (px, py) is centred, at zoom `z` relative to fit. */
const look = (s: Screen, px: number, py: number, z: number, d: number) => {
  // Keep the screenshot filling the frame: never pan past its edges.
  const hw = FRAME.w / 2 / (BASE * z), hh = FRAME.h / 2 / (BASE * z);
  px = Math.min(Math.max(px, hw), 1920 - hw);
  py = Math.min(Math.max(py, hh), 1080 - hh);
  return all(
    s.cam.scale(BASE * z, d, easeInOutCubic),
    s.cam.position([-(px - 960) * BASE * z, -(py - 540) * BASE * z], d, easeInOutCubic),
  );
};

// ---------- 1. hook ----------
const hook = scene("hook", function* (root) {
  const a = createRef<Txt>(), b = createRef<Txt>(), logo = createRef<Layout>();
  root.add(
    <Layout layout direction="column" alignItems="center" gap={34}>
      <Layout ref={logo} opacity={0}><Logo size={40} /></Layout>
      <T ref={a} opacity={0} fontFamily={SERIF} fontSize={92} letterSpacing={-3} text="Every AI session starts from zero." />
      <T ref={b} opacity={0} fontFamily={SERIF} fontSize={54} letterSpacing={-1.5} fill={C.muted}>
        PromptForge brings the context <Txt fill={C.accent}>your team already has.</Txt>
      </T>
    </Layout>,
  );
  yield* all(logo().opacity(1, 0.5), a().opacity(1, 0.7));
  yield* waitFor(1.6);
  yield* b().opacity(1, 0.7);
}, false);

// ---------- 2. request → team context ----------
const request = scene("request", function* (root) {
  const cap = caption(root, "Say or type a loose request.");
  const s = screen(root, "/shots/alice-home.png");
  const mic = s.hl(321, 581, 146, 33, "Voice · ElevenLabs");
  const box = s.hl(313, 659, 930, 165);
  const brain = s.hl(1297, 463, 335, 330, "From MongoDB Atlas");
  const chips = createRef<Layout>();
  root.add(
    <Layout ref={chips} opacity={0} y={470} layout gap={18}>
      <Pill text="Specs" /><Pill text="Team decisions" /><Pill text="Approved preferences" />
    </Layout>,
  );
  yield* all(cap().opacity(1, 0.4), s.frame.opacity(1, 0.4));
  yield* all(look(s, 780, 640, 1.35, 1.2), mic.opacity(1, 0.4));
  yield* box.opacity(1, 0.4);
  yield* waitFor(1.2);
  yield* all(mic.opacity(0, 0.3), box.opacity(0, 0.3), look(s, 1180, 620, 1.3, 1.2),
    cap().text("It pulls in what your team already knows.", 0.6));
  yield* all(brain.opacity(1, 0.4), chips().opacity(1, 0.5));
});

// ---------- 3. cited brief ----------
const brief = scene("brief", function* (root) {
  const cap = caption(root, "Every instruction cites its source.");
  const s = screen(root, "/shots/alice-brief.png");
  const cites = [s.hl(527, 820, 33, 24), s.hl(1008, 857, 72, 24), s.hl(903, 893, 33, 24), s.hl(347, 957, 33, 24)];
  const req = s.hl(321, 760, 914, 225, "Cited to sources & decisions");
  yield* all(cap().opacity(1, 0.4), s.frame.opacity(1, 0.4));
  yield* look(s, 780, 760, 1.25, 1.4);
  yield* all(req.opacity(1, 0.4), sequence(0.25, ...cites.map((c) => c.opacity(1, 0.3))));
  yield* waitFor(1.6);

  // Assumptions + export, from the same brief
  yield* all(s.frame.opacity(0, 0.35), cap().opacity(0, 0.35));
  s.img.src("/shots/alice-lesson.png");
  [req, ...cites].forEach((c) => c.opacity(0));

  const assume = s.hl(321, 18, 914, 295);
  const md = s.hl(1090, 343, 145, 48, "Export Markdown");
  const pills = createRef<Layout>();
  root.add(
    <Layout ref={pills} opacity={0} y={470} layout gap={18}>
      <Pill text="Copy or download .md → any coding tool" /><Pill text="Or preview a sandboxed website" />
    </Layout>,
  );
  cap().text("Gaps become explicit assumptions.");
  yield* look(s, 780, 220, 1.3, 0.01);
  yield* all(s.frame.opacity(1, 0.35), cap().opacity(1, 0.35), assume.opacity(1, 0.4));
  yield* waitFor(1.4);
  yield* all(md.opacity(1, 0.4), pills().opacity(1, 0.4), look(s, 900, 260, 1.3, 1));
});

// ---------- 4. governed memory ----------
function Row({ left, mid, right, tone = C.muted, strike = false }: { left: string; mid: string; right?: string; tone?: string; strike?: boolean }) {
  return (
    <Rect layout alignItems="center" gap={18} width={720} padding={[12, 18]} radius={12} fill={C.surface} stroke={C.border} lineWidth={1.5}>
      <T text={left} fontFamily={MONO} fontSize={19} fontWeight={600} fill={tone} width={150} />
      <T text={mid} fontSize={21} grow={1} fill={strike ? C.muted : C.text} />
      {right && <T text={right} fontFamily={MONO} fontSize={19} fill={C.muted} />}
    </Rect>
  );
}

const govern = scene("govern", function* (root) {
  const cap = caption(root, "Memory you can govern.");
  const s = screen(root, "/shots/alice-lesson.png");
  const lesson = s.hl(321, 770, 914, 170, "Proposed: does nothing yet");
  const scope = s.hl(336, 957, 883, 44, "You choose: me · project · team");
  yield* all(cap().opacity(1, 0.4), s.frame.opacity(1, 0.4), look(s, 780, 860, 1.25, 0.01));
  yield* lesson.opacity(1, 0.4);
  yield* waitFor(1.1);
  yield* all(lesson.opacity(0, 0.3), scope.opacity(1, 0.4));
  yield* waitFor(1.2);

  const left: Rect[] = [], right: Rect[] = [];
  const board = createRef<Layout>();
  const clip = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1).trimEnd() + "…" : t);
  root.add(
    <Layout ref={board} opacity={0} y={60} layout gap={60} alignItems="start">
      <Layout layout direction="column" gap={14}>
        <T text="Only approved, current memory reaches a brief" fontSize={24} fontWeight={700} fill={C.accent} />
        {[
          <Row left="approved" mid="Bulk exports include a manifest" right="project" tone={C.accent} />,
          <Row left="superseded" mid={clip(HERO_OLD.text, 42)} right="r1" tone={C.warn} strike />,
          <Row left="current" mid={clip(HERO_RULE.text, 42)} right="r2" tone={C.accent} />,
          <Row left="left out" mid="Proposed, expired or retired lessons" tone={C.bad} />,
          <Row left="left out" mid="Another teammate's private notes" tone={C.bad} />,
        ].map((r) => <Rect ref={(n: Rect) => left.push(n)} opacity={0}>{r}</Rect>)}
      </Layout>
      <Layout layout direction="column" gap={14}>
        <T text="memory_events · append-only audit log" fontFamily={MONO} fontSize={22} fontWeight={600} fill={C.muted} />
        {[
          ["approved", "lesson · by alice · scope project"],
          ["superseded", "decision r1 → r2 · by alice"],
          ["expired", "stale lesson removed from use"],
          ["stale brief", "export blocked: its memory changed"],
        ].map(([a, b]) => (
          <Rect ref={(n: Rect) => right.push(n)} opacity={0} layout gap={16} width={720} padding={[14, 18]} radius={12} fill={C.soft}>
            <T text={a} fontFamily={MONO} fontSize={20} fontWeight={700} fill={C.accent} width={170} />
            <T text={b} fontSize={21} />
          </Rect>
        ))}
      </Layout>
    </Layout>,
  );
  yield* all(s.frame.opacity(0, 0.35), cap().text("Versioned, scoped, and logged.", 0.5));
  yield* board().opacity(1, 0.3);
  yield* all(sequence(0.45, ...left.map((r) => r.opacity(1, 0.35))), sequence(0.55, ...right.map((r) => r.opacity(1, 0.35))));
});

// ---------- 5. team learning ----------
const team = scene("team", function* (root) {
  const cap = caption(root, "Alice teaches once. Bob benefits.");
  const s = screen(root, "/shots/bob-brief.png");
  const row = s.hl(321, 214, 914, 58, "Alice's approved lesson, in Bob's fresh session");
  const tag = createRef<Layout>();
  root.add(
    <Layout ref={tag} opacity={0} y={470} layout gap={18}>
      <Pill text="Different teammate" /><Pill text="Different feature: invoice export" /><Pill text="Never asked for a manifest" />
    </Layout>,
  );
  yield* all(cap().opacity(1, 0.4), s.frame.opacity(1, 0.4));
  yield* look(s, 780, 330, 1.35, 1.2);
  yield* all(row.opacity(1, 0.4), tag().opacity(1, 0.5));
});

// ---------- 6. accessibility ----------
const access = scene("access", function* (root) {
  const cap = caption(root, "Accessible by default.");
  const s = screen(root, "/shots/bob-brief.png");
  const line = s.hl(321, 896, 914, 56, "Accessibility standard, in every brief");
  const tags = createRef<Layout>();
  root.add(
    <Layout ref={tags} opacity={0} y={470} layout gap={18}>
      <Pill text="🎙 Speak instead of typing" /><Pill text="Color contrast" /><Pill text="Keyboard navigation" /><Pill text="Alt text" />
    </Layout>,
  );
  yield* all(cap().opacity(1, 0.4), s.frame.opacity(1, 0.4), look(s, 780, 330, 1.35, 0.01));
  yield* look(s, 780, 880, 1.35, 1.2);
  yield* all(line.opacity(1, 0.4), tags().opacity(1, 0.5));
});

// ---------- 7. close ----------
const close = scene("close", function* (root) {
  const logo = createRef<Layout>(), line = createRef<Txt>(), stack = createRef<Layout>();
  root.add(
    <Layout layout direction="column" alignItems="center" gap={30}>
      <Layout ref={logo} opacity={0}><Logo size={64} /></Layout>
      <T ref={line} opacity={0} fontFamily={SERIF} fontSize={52} letterSpacing={-1.5} fill={C.muted}
        text="Teach it once. Every teammate's next prompt gets better." />
      <Layout ref={stack} opacity={0} layout gap={16} marginTop={20}>
        {["MongoDB Atlas", "Voyage AI", "ElevenLabs", "OpenAI", "LangSmith"].map((t) => (
          <Pill text={t} size={26} fill={C.surface} color={C.text} />
        ))}
      </Layout>
    </Layout>,
  );
  yield* all(logo().opacity(1, 0.5), line().opacity(1, 0.6));
  yield* stack().opacity(1, 0.5);
}, false);

export default makeProject({
  scenes: [hook, request, brief, govern, team, access, close],
  settings: { shared: { size: { x: 1920, y: 1080 } } },
});
