// Generate per-scene narration with ElevenLabs TTS into public/vo/<scene>.mp3.
// Reads ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID from the repo .env; the key never enters the video bundle.
// Usage (from video/):  node scripts/voiceover.mjs [scene ...]
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const env = Object.fromEntries(
  readFileSync(path.join(here, "../../.env"), "utf8").split("\n")
    .map((l) => l.match(/^\s*([A-Z0-9_]+)\s*=\s*"?(.*?)"?\s*$/)).filter(Boolean).map((m) => [m[1], m[2]]),
);
const KEY = process.env.ELEVENLABS_API_KEY || env.ELEVENLABS_API_KEY;
const VOICE = process.env.ELEVENLABS_VOICE_ID || env.ELEVENLABS_VOICE_ID || "21m00Tcm4TlvDq8ikWAM";
if (!KEY) throw new Error("ELEVENLABS_API_KEY missing");

const script = JSON.parse(readFileSync(path.join(here, "../src/narration.json"), "utf8"));
const only = process.argv.slice(2);
mkdirSync(path.join(here, "../public/vo"), { recursive: true });

for (const [scene, text] of Object.entries(script)) {
  if (only.length && !only.includes(scene)) continue;
  const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${VOICE}?output_format=mp3_44100_128`, {
    method: "POST",
    headers: { "xi-api-key": KEY, "Content-Type": "application/json", Accept: "audio/mpeg" },
    body: JSON.stringify({ text, model_id: "eleven_multilingual_v2", voice_settings: { stability: 0.5, similarity_boost: 0.75 } }),
  });
  if (!res.ok) throw new Error(`${scene}: ${res.status} ${await res.text()}`);
  writeFileSync(path.join(here, `../public/vo/${scene}.mp3`), Buffer.from(await res.arrayBuffer()));
  console.log(`wrote public/vo/${scene}.mp3`);
}

// Manifest of clips that exist, so the video only plays audio that was generated.
const manifest = Object.keys(script).filter((s) => existsSync(path.join(here, `../public/vo/${s}.mp3`)));
writeFileSync(path.join(here, "../src/vo.json"), JSON.stringify(manifest) + "\n");
console.log("voiced scenes:", manifest.join(", ") || "none");
