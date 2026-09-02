// 1440px screenshots for QA, into site/qa/. Reports scrollWidth and any console error.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const site = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const qa = resolve(site, "qa");
mkdirSync(qa, { recursive: true });

const routes = process.argv.slice(2);
const base = process.env.QA_BASE ?? "http://localhost:3100";
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();

for (const route of routes) {
  const errors = [];
  page.removeAllListeners("console");
  page.removeAllListeners("pageerror");
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${base}${route}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  const name = route === "/" ? "home" : route.replace(/^\//, "").replace(/\/$/, "").replace(/\//g, "-");
  await page.screenshot({ path: resolve(qa, `1440-${name}.png`), fullPage: true });
  const sw = await page.evaluate(() => document.documentElement.scrollWidth);
  const cw = await page.evaluate(() => document.documentElement.clientWidth);
  const clipped = await page.evaluate(() =>
    [...document.querySelectorAll(".table-wrap")]
      .map((el, i) => (el.scrollWidth > el.clientWidth + 1 ? `#${i} ${el.scrollWidth}>${el.clientWidth}` : null))
      .filter(Boolean),
  );
  console.log(
    `${route}  page ${sw}/${cw}  sideways-scrolling tables: ${clipped.length ? clipped.join(", ") : "none"}  errors: ${errors.length ? errors.join(" | ") : "none"}`,
  );
}

await ctx.close();
await browser.close();
