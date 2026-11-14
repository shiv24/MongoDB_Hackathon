// Capture real screens of the PromptForge UI for the video.
// Run the offline preview first (python scripts/dev_preview.py, needs OPENAI_API_KEY for briefs),
// then from video/:  node scripts/capture.mjs [baseUrl]   → public/shots/*.png
import path from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer";

const BASE = process.argv[2] || "http://localhost:8000";
const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), "../public/shots");
const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1.2 });
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
const shot = async (name, opts = {}) => { await new Promise((r) => setTimeout(r, 600)); await page.screenshot({ path: `${OUT}/${name}.png`, ...opts }); console.log("shot", name); };
const vis = (sel, timeout = 180000) => page.waitForSelector(`${sel}:not(.hidden)`, { visible: true, timeout });
const elShot = async (name, sel) => { const h = await page.$(sel); await h.scrollIntoView(); await shot(name); };

async function build(user) {
  await page.evaluate((u) => sessionStorage.setItem("pf-demo-user", u), user);
  await page.goto(BASE, { waitUntil: "networkidle0" });
  await page.waitForFunction(() => !document.getElementById("active-context").textContent.includes("Loading"));
  await page.click("#demo-request");
  await shot(`${user}-home`);
  await page.click("#send-btn");
  await vis("#brief-card");
  await page.waitForFunction(() => document.querySelectorAll("#brief .cite").length > 0, { timeout: 180000 });
  await elShot(`${user}-brief`, "#brief-card");
}

await page.goto(BASE, { waitUntil: "networkidle0" });
await build("alice");
await vis("#feedback-card");
await page.click("#lesson-example");
await page.click("#feedback-down");
await page.waitForSelector(".generated-lesson", { visible: true, timeout: 120000 });
const scopeOk = await page.evaluate(() => {
  const s = document.querySelector(".generated-lesson select");
  if ([...s.options].some((o) => o.value === "project")) { s.value = "project"; return true; }
  return false;
});
console.log("project scope available:", scopeOk);
await elShot("alice-lesson", ".generated-lesson");
await page.evaluate(() => [...document.querySelectorAll(".generated-lesson button")].find((b) => b.textContent === "Save lesson").click());
await page.waitForFunction(() => document.getElementById("feedback-status").textContent.includes("saved"), { timeout: 60000 });
await elShot("alice-saved", "#feedback-card");
await page.click("#brain-open");
await page.waitForSelector("#brain-dialog[open]");
await shot("alice-brain");
await page.click("#brain-close");

await build("bob");
await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1.2 });
await shot("bob-brief-full", { fullPage: true });
await browser.close();
