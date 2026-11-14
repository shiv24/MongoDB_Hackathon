// All memory text comes from the real seed fixtures, so the video shows the same data the app retrieves.
import fx from "../../scripts/data/fixtures.json";

type Rec = Record<string, any>;
const byId = (list: Rec[], id: string, key = "_id") => {
  const r = list.find((x) => x[key] === id);
  if (!r) throw new Error(`fixture ${id} missing`);
  return r;
};

export const USER = byId(fx.users, "bob");
export const PROJECT = byId(fx.projects, "lumen-signup");

export const REQUEST =
  "On the signup spec, build the signup page in React. Keep it consistent with what we decided.";

// The one rule the whole video follows: a decision that was corrected (r1 -> r2).
export const HERO_RULE = byId(fx.decisions, "dec-a-phone-r2");
export const HERO_OLD = byId(fx.decisions, "dec-a-phone-r1");

export type Card = { id: string; kind: string; title: string; text: string; tag: string; hero?: boolean };

const src = (id: string): Card => {
  const s = byId(fx.sources, id, "source_id");
  return { id, kind: "Source", title: s.title, text: s.text.split("\n\n")[1] ?? s.text, tag: `${s.kind} · r${s.revision ?? 1}` };
};
const dec = (id: string, hero = false): Card => {
  const d = byId(fx.decisions, id);
  return { id, kind: "Decision", title: `Decision · ${d.owner_id}`, text: d.text, tag: `current · r${d.revision}`, hero };
};
const les = (id: string): Card => {
  const l = byId(fx.lessons, id);
  return { id, kind: "Lesson", title: `Lesson · ${l.scope}`, text: l.text, tag: `approved · ${l.scope}` };
};

export const INCLUDED: Card[] = [
  src("lumen-signup-spec"),
  src("lumen-architecture"),
  src("lumen-brand"),
  dec("dec-a-identity"),
  dec("dec-a-labels"),
  dec("dec-a-phone-r2", true),
  les("les-a-pwhint"),
  les("les-a-teamtone"),
];

export const EXCLUDED: { text: string; reason: string }[] = [
  { text: HERO_OLD.text, reason: "superseded by r2" },
  { text: byId(fx.lessons, "les-a-darkmode").text, reason: "proposed, not approved" },
  { text: byId(fx.lessons, "les-a-stale").text, reason: "expired" },
  { text: byId(fx.lessons, "les-a-twocol").text, reason: "retired" },
  { text: byId(fx.lessons, "les-a-singlecol").text, reason: "Alice's personal lesson" },
  { text: byId(fx.sources, "orbit-signup-spec", "source_id").text.split(".")[0] + ".", reason: "other team (team_b)" },
];

export type Line = { section: string; text: string; cite: string; hero?: boolean; question?: boolean };

export const BRIEF: Line[] = [
  { section: "Objective", text: "React signup page for Lumen: account + first workspace in one step", cite: "lumen-signup-spec r1" },
  { section: "Requirements", text: "Fields: work email, full name, password, workspace name", cite: "lumen-signup-spec r1" },
  { section: "Requirements", text: "Password ≥ 12 chars with a number; rules shown before typing", cite: "lumen-signup-spec r1" },
  { section: "Requirements", text: "Terms checkbox must be ticked before the primary action", cite: "lumen-signup-spec r1" },
  { section: "Decisions", text: "Create accounts via Lumen ID: POST /v1/identities, never store passwords", cite: "dec-a-identity r1" },
  { section: "Decisions", text: "Do not collect a phone number at signup", cite: "dec-a-phone r2", hero: true },
  { section: "Decisions", text: "Primary button: sentence case, ≤ 3 words (“Create account”)", cite: "dec-a-labels r1" },
  { section: "Context", text: "Build inputs on FormField (web/src/components/FormField.tsx)", cite: "architecture r1" },
  { section: "Preferences", text: "Live password checklist under the field", cite: "les-a-pwhint" },
  { section: "Open questions", text: "Company size is required but its values are TBD (sales)", cite: "lumen-signup-spec r1", question: true },
];

export const CHECKS_PLAIN = [
  { ok: false, text: "Asks for a phone number" },
  { ok: false, text: "Custom auth, hashes password in the app" },
  { ok: false, text: "No password rules until an error" },
  { ok: false, text: "Button reads “Sign Up Now!”" },
];
export const CHECKS_PF = [
  { ok: true, text: "No phone field", cite: "dec-a-phone r2", hero: true },
  { ok: true, text: "Calls POST /v1/identities", cite: "dec-a-identity r1" },
  { ok: true, text: "Live password checklist", cite: "les-a-pwhint" },
  { ok: true, text: "Button reads “Create account”", cite: "dec-a-labels r1" },
];
