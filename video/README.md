# PromptForge demo video

A 60-second demo video built with [Revideo](https://github.com/redotvideo/revideo) (MIT; TypeScript scenes rendered to MP4), narrated with ElevenLabs text-to-speech. The memory text on screen is imported from `scripts/data/fixtures.json`, so it matches what the app seeds.

> Prototyped with Remotion while evaluating whether the Remotion software is a good fit. The final build of the submitted demo video uses Revideo (MIT) instead.

## Requirements

- Node.js 18 or later (tested on 22)
- An ElevenLabs API key with text-to-speech access (needed only for the voiceover)
- About 5 minutes. The first render downloads a headless Chrome. ffmpeg is bundled.

## Setup

From the repo root:

```bash
cd video
npm install
```

Add your ElevenLabs settings to the **repo root** `.env` (the one next to the main `README.md`, not `video/.env`):

```
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=optional_voice_id
```

- If `ELEVENLABS_VOICE_ID` is empty, the script uses the default "Rachel" voice (`21m00Tcm4TlvDq8ikWAM`). Find other voice IDs in the ElevenLabs Voice Library under "Copy voice ID".
- The script can also read the key from your shell: `ELEVENLABS_API_KEY=... npm run voice`.
- Never commit `.env`. The key is used only by the Node script and is not bundled into the video.

## Make the video

```bash
npm run voice    # ElevenLabs narration → public/vo/<scene>.mp3 and clip lengths in src/vo.json
npm run render   # write out/promptforge-demo.mp4 (1920×1080, with voice)
```

`scripts/capture.mjs` is a legacy capture helper, not a working quickstart for the current UI. It targets older selectors (`#lesson-example`, `#feedback-down`), uses the old `pf-demo-user` session key, and imports Puppeteer, which is not a declared video dependency. Update it and provide its browser dependency before attempting a fresh capture; no offline preview server is currently included. The render command uses the committed screenshots. Those screenshots were captured with vector search stubbed, so they do not demonstrate Atlas-ranked retrieval. For a current live walkthrough, follow [DEMO.md](../DEMO.md).

To preview and scrub the timeline in the browser while you edit: `npm run editor`. `npm run typecheck` checks the TypeScript without rendering.

## Change the narration

The script is a condensed version of the project description, one line per scene in `src/narration.json`:

| Scene | Key | Shows |
|---|---|---|
| Hook | `hook` | The problem and tagline |
| Request | `request` | Voice/typed request; specs, decisions, preferences from Atlas |
| Brief | `brief` | Cited instructions, assumptions, Markdown export / website preview |
| Governance | `govern` | Proposed lesson + scope choice; versioned decisions, exclusions, audit log |
| Team | `team` | Alice's approved lesson in Bob's fresh session |
| Accessibility | `access` | Voice input; accessibility standards in every brief |
| Close | `close` | Logo and stack |

Each scene lasts as long as its clip plus 0.35s. **The whole video must stay within 60 seconds**: `src/project.tsx` throws at render time if the clips add up to more. Regenerate one line with `node scripts/voiceover.mjs brief`, then `npm run render`.

## Troubleshooting

- **`ELEVENLABS_API_KEY missing`**: the key is empty in the root `.env`, or you put it in `video/.env`.
- **`401`**: the key is wrong or revoked.
- **`402` / quota error**: the account is out of character credits. The full script is about 800 characters.
- **`404 voice_not_found`**: `ELEVENLABS_VOICE_ID` doesn't exist on your account. Clear it to use the default voice.
- **Voice cut off at a scene change**: the line is too long for its scene. See "Change the narration" above.
- **Render fails to import `fixtures.json`**: run commands from `video/`. `scripts/render.mjs` allows Vite to read the repo root.

## Notes

- Screens are real captures of the current UI. The governance board (statuses, audit log) is a diagram of what the app records, not a screenshot.
- Revideo and its packages are MIT-licensed, so there is no team-size limit.
