// Crop a screenshot for review. Usage: node scripts/_crop.mjs <png> <y> <height> [out]
import { chromium } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
const [file, y, h, out] = process.argv.slice(2);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: Number(h) } });
const data = readFileSync(resolve(file)).toString("base64");
await p.setContent(`<body style="margin:0"><img src="data:image/png;base64,${data}" style="display:block;margin-top:-${y}px"></body>`);
await p.screenshot({ path: out ?? "/tmp/bench-crop.png" });
await b.close();
