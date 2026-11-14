// Render the Revideo project to out/promptforge-demo.mp4.  Usage (from video/):  npm run render
import path from "node:path";
import { fileURLToPath } from "node:url";
import { renderVideo } from "@revideo/renderer";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const file = await renderVideo({
  projectFile: "./src/project.tsx",
  settings: {
    outDir: "./out",
    outFile: "promptforge-demo.mp4",
    logProgress: true,
    // src/data.ts imports ../scripts/data/fixtures.json from the repo root.
    viteConfig: { server: { fs: { allow: [repoRoot] } } },
  },
});
console.log(`Rendered ${file}`);
