# PromptForge demo video

A 60-second demo video built with [Remotion](https://www.remotion.dev/) (React → MP4), narrated with ElevenLabs text-to-speech. The memory text on screen is imported from `scripts/data/fixtures.json`, so it matches what the app seeds.

## Requirements

- Node.js 18 or later (tested on 22)
- An ElevenLabs API key with text-to-speech access
- About 5 minutes. The first render also downloads a headless Chrome.

## Setup

From the repo root:

```bash
cd video
npm install
```

Add your ElevenLabs settings to the **repo root** `.env` (the one next to `README.md`, not `video/.env`):

```
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=optional_voice_id
```

- If `ELEVENLABS_VOICE_ID` is empty, the script uses the default "Rachel" voice (`21m00Tcm4TlvDq8ikWAM`). Find other voice IDs in the ElevenLabs Voice Library under "Copy voice ID".
- The script can also read the key from your shell: `ELEVENLABS_API_KEY=... npm run voice`.
- Never commit `.env`. The key is used only by the Node script and is not bundled into the video.

## Make the video

```bash
npm run voice    # generate narration → public/vo/<scene>.mp3
npm run render   # write out/promptforge-demo.mp4 (1920×1080, 30 fps, with voice)
```

To preview or scrub the timeline in the browser while you edit:

```bash
npm run studio
```

## Change the narration

1. Edit the lines in `src/narration.json`. There is one line per scene.
2. Regenerate only what changed, for example `node scripts/voiceover.mjs brief`. Run `npm run voice` with no arguments to regenerate all scenes.
3. Run `npm run render` again.

Each clip starts about 0.25s into its scene. Keep each line under the time its scene allows, at roughly 2.5 words per second:

| Scene | Key | Length | Max words (approx.) |
|---|---|---|---|
| Hook | `hook` | 5s | 12 |
| Request | `request` | 9s | 21 |
| Retrieve context | `context` | 13s | 31 |
| Cited brief | `brief` | 13s | 31 |
| Result | `result` | 12s | 28 |
| Close | `close` | 8s | 18 |

To check a clip's real length:

```bash
npx remotion ffprobe -v error -show_entries format=duration -of csv=p=0 public/vo/brief.mp3
```

If a clip runs over, shorten the line or lengthen the scene in `src/Video.tsx`. Scene timings are in the `S` object as `[startFrame, durationFrames]`, at 30 frames per second. If you lengthen one scene, shift the start of every later scene by the same amount, and update `TOTAL`.

## How it fits together

| File | Purpose |
|---|---|
| `src/narration.json` | Voiceover script, one line per scene |
| `scripts/voiceover.mjs` | Calls the ElevenLabs TTS API, writes the MP3s and `src/vo.json` (the list of scenes that have audio) |
| `src/Video.tsx` | Scenes, animation and timing. Plays each scene's MP3 with `<Audio>` |
| `src/data.ts` | Loads the fixtures and holds the brief lines and checks shown on screen. `HERO_RULE` is the rule highlighted across scenes |
| `public/vo/` | Generated audio (safe to delete and regenerate) |
| `out/` | Rendered video (gitignored) |

Scenes without an MP3 render silently, so the video always builds, with or without a key.

## Troubleshooting

- **`ELEVENLABS_API_KEY missing`**: the key is empty in the root `.env`, or you put it in `video/.env`.
- **`401`**: the key is wrong or revoked.
- **`402` / quota error**: the account is out of character credits. The full script is about 1,000 characters.
- **`404 voice_not_found`**: `ELEVENLABS_VOICE_ID` doesn't exist on your account. Clear it to use the default voice.
- **Voice cut off at a scene change**: the line is too long for its scene. See "Change the narration" above.

## Notes

- The page mockups in the result scene are illustrative and are labelled as such on screen. Swap in real screen recordings of the app with Remotion's `<OffthreadVideo>` before submitting if you can.
- Remotion is free for individuals and companies of up to 3 people. Larger teams need a [company licence](https://www.remotion.dev/license).
