// Generate per-scene narration with ElevenLabs TTS into public/vo/<scene>.mp3.
// Reads ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID from the repo .env; the key never enters the video bundle.
// Writes src/vo.json: { scene: clipSeconds } so each scene is long enough for its line.
// Usage (from video/):  node scripts/voiceover.mjs [scene ...]
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import ffprobe from "@ffprobe-installer/ffprobe";

const here = path.dirname(fileURLToPath(import.meta.url));
const envFile = path.join(here, "../../.env");
const env = existsSync(envFile) ? Object.fromEntries(
  readFileSync(envFile, "utf8").split("\n")
    .map((l) => l.match(/^\s*([A-Z0-9_]+)\s*=\s*"?(.*?)"?\s*$/)).filter(Boolean).map((m) => [m[1], m[2]]),
) : {};
const KEY = process.env.ELEVENLABS_API_KEY || env.ELEVENLABS_API_KEY;
const VOICE = process.env.ELEVENLABS_VOICE_ID || env.ELEVENLABS_VOICE_ID || "21m00Tcm4TlvDq8ikWAM";

const script = JSON.parse(readFileSync(path.join(here, "../src/narration.json"), "utf8"));
const only = process.argv.slice(2);
const voDir = path.join(here, "../public/vo");
mkdirSync(voDir, { recursive: true });

if (!KEY) console.warn("ELEVENLABS_API_KEY missing: keeping existing clips only");
else for (const [scene, text] of Object.entries(script)) {
  if (only.length && !only.includes(scene)) continue;
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}?output_format=mp3_44100_128`, {
    method: "POST",
    headers: { "xi-api-key": KEY, "Content-Type": "application/json", Accept: "audio/mpeg" },
    body: JSON.stringify({ text, model_id: "eleven_multilingual_v2", voice_settings: { stability: 0.5, similarity_boost: 0.75, speed: 1.05 } }),
  });
  if (!res.ok) throw new Error(`${scene}: ${res.status} ${await res.text()}`);
  writeFileSync(path.join(voDir, `${scene}.mp3`), Buffer.from(await res.arrayBuffer()));
  console.log(`wrote public/vo/${scene}.mp3`);
}

// Manifest of clips that exist, with their lengths, so the video only plays audio that was generated.
const manifest = {};
for (const s of Object.keys(script)) {
  const f = path.join(voDir, `${s}.mp3`);
  if (!existsSync(f)) continue;
  const out = execFileSync(ffprobe.path, ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]);
  manifest[s] = Math.round(parseFloat(String(out)) * 100) / 100;
}
writeFileSync(path.join(here, "../src/vo.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log("voiced scenes:", manifest);
