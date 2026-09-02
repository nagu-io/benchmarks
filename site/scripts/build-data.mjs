/**
 * build-data.mjs — the only place this site gets a number from.
 *
 * It reads the repository root (charter, datasets, harness, results, day-60) and writes
 * `data/benchmarks.json`. Every page is prerendered from that file. Nothing in `app/`
 * or `components/` contains a figure, and nothing here invents one: a value that is not
 * present in a source file is emitted as null and rendered as "not run" with the reason
 * the source gives, per charter 3.1.8.
 *
 * Run by `pnpm build` (prebuild) and `pnpm dev` (predev). Never edit data/benchmarks.json.
 */
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ROOT = resolve(process.env.BENCH_ROOT ?? join(SITE, ".."));

const sources = [];

function record(abs) {
  const rel = relative(ROOT, abs).split("\\").join("/");
  if (sources.some((s) => s.path === rel)) return;
  const bytes = statSync(abs).size;
  sources.push({ path: rel, bytes, sha256: createHash("sha256").update(readFileSync(abs)).digest("hex").slice(0, 16) });
}

function readText(rel) {
  const abs = join(ROOT, rel);
  if (!existsSync(abs)) return null;
  record(abs);
  return readFileSync(abs, "utf8");
}

function readJson(rel) {
  const text = readText(rel);
  return text === null ? null : JSON.parse(text);
}

function readLines(rel) {
  const text = readText(rel);
  return text === null ? null : text.split("\n").filter((l) => l.trim() !== "");
}

function exists(rel) {
  return existsSync(join(ROOT, rel));
}

/* ------------------------------------------------------------------ markdown */

/** Split a GFM table row into cells, honouring escaped pipes. */
function tableCells(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split(/(?<!\\)\|/)
    .map((c) => c.trim().replace(/\\\|/g, "|"));
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/**
 * Markdown to a block list. Handles the subset the charter, the reproduce files and
 * the dataset READMEs actually use: ATX headings, paragraphs, GFM tables, fenced code,
 * blockquotes, and `-` / `1.` lists. Inline markup is left in the text and rendered by
 * components/Markdown.tsx.
 */
function toBlocks(md) {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let i = 0;
  const isTableSep = (l) => /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(l) && l.includes("-");

  while (i < lines.length) {
    const line = lines[i] ?? "";

    if (line.trim() === "") {
      i += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const body = [];
      i += 1;
      while (i < lines.length && !(lines[i] ?? "").startsWith("```")) {
        body.push(lines[i]);
        i += 1;
      }
      i += 1;
      blocks.push({ t: "code", lang, code: body.join("\n") });
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const level = (heading[1] ?? "#").length;
      const text = (heading[2] ?? "").trim();
      blocks.push({ t: "h", level, text, id: slugify(text) });
      i += 1;
      continue;
    }

    if (line.trim() === "---" || line.trim() === "***") {
      blocks.push({ t: "hr" });
      i += 1;
      continue;
    }

    if (line.startsWith(">")) {
      const body = [];
      while (i < lines.length && (lines[i] ?? "").startsWith(">")) {
        body.push((lines[i] ?? "").replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ t: "quote", blocks: toBlocks(body.join("\n")) });
      continue;
    }

    if (line.trimStart().startsWith("|") && isTableSep(lines[i + 1] ?? "")) {
      const head = tableCells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && (lines[i] ?? "").trimStart().startsWith("|")) {
        rows.push(tableCells(lines[i] ?? ""));
        i += 1;
      }
      blocks.push({ t: "table", head, rows });
      continue;
    }

    const bullet = /^\s*[-*]\s+/.test(line);
    const ordered = /^\s*\d+[.)]\s+/.test(line);
    if (bullet || ordered) {
      const items = [];
      const marker = bullet ? /^\s*[-*]\s+/ : /^\s*\d+[.)]\s+/;
      while (i < lines.length && marker.test(lines[i] ?? "")) {
        let item = (lines[i] ?? "").replace(marker, "");
        i += 1;
        while (i < lines.length && /^\s{2,}\S/.test(lines[i] ?? "") && !marker.test(lines[i] ?? "")) {
          item += ` ${(lines[i] ?? "").trim()}`;
          i += 1;
        }
        items.push(item.trim());
      }
      blocks.push({ t: bullet ? "ul" : "ol", items });
      continue;
    }

    const para = [];
    while (
      i < lines.length &&
      (lines[i] ?? "").trim() !== "" &&
      !(lines[i] ?? "").startsWith("```") &&
      !(lines[i] ?? "").startsWith("#") &&
      !(lines[i] ?? "").startsWith(">") &&
      !(lines[i] ?? "").trimStart().startsWith("|") &&
      !/^\s*[-*]\s+/.test(lines[i] ?? "") &&
      !/^\s*\d+[.)]\s+/.test(lines[i] ?? "")
    ) {
      para.push((lines[i] ?? "").trim());
      i += 1;
    }
    if (para.length) blocks.push({ t: "p", text: para.join(" ") });
  }
  return blocks;
}

/** Every fenced code block in a markdown file, with the nearest heading above it. */
function codeBlocksWithHeadings(md) {
  const blocks = toBlocks(md);
  const out = [];
  let heading = null;
  for (const b of blocks) {
    if (b.t === "h") heading = b.text;
    if (b.t === "code") out.push({ heading, lang: b.lang, code: b.code });
  }
  return out;
}

/* ----------------------------------------------------------------- the charter */

const CHARTER_PATH = "charter/methodology.md";
const CLAUSES_PATH = "charter/contract-clauses.md";
const charterMd = readText(CHARTER_PATH);
if (charterMd === null) throw new Error(`build-data: ${CHARTER_PATH} is missing. This site cannot be built without the charter.`);
const clausesMd = readText(CLAUSES_PATH);

/**
 * The charter and the clause set are each published as an index file plus a directory of
 * numbered parts, so that a section can be linked and cited on its own. The index carries
 * the front matter and the parts table; the parts carry the numbered sections themselves.
 * Parsing the index alone therefore finds no section 3, which is why this reads the parts
 * back into one document, in filename order, before the parser walks it.
 *
 * If the parts directory is absent the index is used as it stands, so a single-file charter
 * still builds. Every part is recorded as a source, so the provenance list names all of them.
 */
function withParts(indexRel, indexMd) {
  const dirRel = indexRel.replace(/\.md$/, "");
  if (!exists(dirRel)) return indexMd;
  const parts = readdirSync(join(ROOT, dirRel))
    .filter((f) => f.endsWith(".md"))
    .sort()
    .map((f) => readText(`${dirRel}/${f}`))
    .filter((t) => t !== null);
  return parts.length ? `${indexMd}\n\n${parts.join("\n\n")}` : indexMd;
}

const charterFull = withParts(CHARTER_PATH, charterMd);
const clausesFull = clausesMd === null ? null : withParts(CLAUSES_PATH, clausesMd);

const charterVersion = /^Charter version (\S+)/m.exec(charterMd)?.[1] ?? null;
const charterWritten = /^Written (\S+)/m.exec(charterMd)?.[1] ?? null;
const clausesVersion = /^Version (\S+), issued against charter version (\S+)/m.exec(clausesMd ?? "")?.[1] ?? null;

const charterBlocks = toBlocks(charterFull);

/** The `## n. Title` sections of the charter, each with its blocks. */
function topSections(blocks) {
  const out = [];
  let cur = null;
  for (const b of blocks) {
    if (b.t === "h" && b.level === 2) {
      cur = { number: /^(\d+)\./.exec(b.text)?.[1] ?? null, title: b.text, id: b.id, blocks: [] };
      out.push(cur);
    } else if (cur) {
      cur.blocks.push(b);
    }
  }
  return out;
}

const charterSections = topSections(charterBlocks);

/**
 * Everything above the first `## ` heading. The front matter is a run of short lines that
 * markdown treats as one paragraph; it is kept as its lines so it renders as the list it is,
 * while the standing warning stays a block.
 */
const charterPreamble = (() => {
  const out = [];
  for (const b of charterBlocks) {
    if (b.t === "h" && b.level === 2) break;
    if (b.t === "h" && b.level === 1) continue;
    out.push(b);
  }
  return out.filter((b) => b.t !== "p");
})();

const charterFrontMatter = (() => {
  const lines = [];
  for (const raw of charterMd.split("\n")) {
    const line = raw.trim();
    if (line.startsWith("## ")) break;
    if (line.startsWith("# ") || line.startsWith(">") || line === "") continue;
    lines.push(line);
  }
  return lines;
})();

/** The `### 3.n Title` metric sections. */
function metricSections(blocks) {
  const out = new Map();
  let cur = null;
  for (const b of blocks) {
    // A heading at level 2 or above closes the current metric: section 3.21 must not
    // swallow section 4 just because section 4's first child heading comes later.
    if (b.t === "h" && b.level <= 2) {
      cur = null;
      continue;
    }
    if (b.t === "h" && b.level === 3) {
      const m = /^(3\.\d+)\s+(.*)$/.exec(b.text);
      cur = m ? { section: m[1], title: m[2], id: b.id, blocks: [] } : null;
      if (cur) out.set(cur.section, cur);
    } else if (cur) {
      cur.blocks.push(b);
    }
  }
  return out;
}

const metricBodies = metricSections(charterBlocks);

/** The metric index, charter 3.2: metric -> suite, section, clause. */
const suiteBySlug = {
  "Messy Scan": "messy-scan",
  "Honest Containment": "honest-containment",
  "Exception Economics": "exception-economics",
  "Day-60": "day-60",
};

function findTable(blocks, headMatch) {
  return blocks.find((b) => b.t === "table" && headMatch(b.head)) ?? null;
}

const indexTable = findTable(charterBlocks, (h) => h[0] === "Metric" && h[1] === "Suite" && h[2] === "Section");
if (!indexTable) throw new Error("build-data: charter 3.2 metric index table not found.");

const metrics = indexTable.rows.map((r) => {
  const section = (r[2] ?? "").replace(/`/g, "").trim();
  const body = metricBodies.get(section);
  const kept = (body?.blocks ?? []).filter(
    (b) => !(b.t === "p" && /^\d+\.\d+\.\d+\s+Arithmetic example/.test(b.text)),
  );
  return {
    name: (r[0] ?? "").trim(),
    suite: suiteBySlug[(r[1] ?? "").trim()] ?? null,
    section,
    clause: (r[3] ?? "").trim(),
    title: body?.title ?? (r[0] ?? "").trim(),
    anchor: body?.id ?? null,
    blocks: kept,
  };
});

/** Charter 2.1: what each suite measures. */
const suiteTable = findTable(charterBlocks, (h) => h[0] === "Suite" && h.includes("Unit scored"));
const suiteFacts = {};
for (const r of suiteTable?.rows ?? []) {
  const slug = suiteBySlug[(r[0] ?? "").trim()];
  if (!slug) continue;
  suiteFacts[slug] = {
    name: (r[0] ?? "").trim(),
    line: (r[1] ?? "").trim(),
    measures: (r[2] ?? "").trim(),
    unit: (r[3] ?? "").trim(),
    headline: (r[4] ?? "").trim(),
    builtFrom: (r[5] ?? "").replace(/`/g, "").trim(),
  };
}

/** Charter 10.2: status by suite, and 10.3: what a first run needs from a person. */
const statusSection = charterSections.find((s) => s.number === "10");
const statusTable = findTable(statusSection?.blocks ?? [], (h) => h[0] === "Suite" && h.includes("Runs"));
const charterStatus = {};
for (const r of statusTable?.rows ?? []) {
  const slug = suiteBySlug[(r[0] ?? "").trim()];
  if (!slug) continue;
  charterStatus[slug] = {
    dataset: (r[1] ?? "").trim(),
    harness: (r[2] ?? "").trim(),
    runs: (r[3] ?? "").trim(),
    status: (r[4] ?? "").trim(),
  };
}
const firstRunNeeds =
  statusSection?.blocks.find((b) => b.t === "p" && /^10\.3/.test(b.text))?.text.replace(/^10\.3\s+/, "") ?? null;
const noRunStatement =
  statusSection?.blocks.find((b) => b.t === "p" && /^10\.1/.test(b.text))?.text.replace(/^10\.1\s+/, "") ?? null;

/** Charter 4.x: the tier table for each suite. */
const tierSectionBySuite = {
  "messy-scan": "4.2",
  "honest-containment": "4.3",
  "exception-economics": "4.4",
  "day-60": "4.5",
};
const tierBlocks = {};
{
  let cur = null;
  for (const b of charterBlocks) {
    if (b.t === "h" && b.level <= 2) {
      cur = null;
      continue;
    }
    if (b.t === "h" && b.level === 3) {
      const m = /^(4\.\d+)\s+(.*)$/.exec(b.text);
      cur = m ? m[1] : null;
      if (cur) tierBlocks[cur] = { title: m[2], id: b.id, blocks: [] };
    } else if (cur && tierBlocks[cur]) {
      tierBlocks[cur].blocks.push(b);
    }
  }
}

/* ------------------------------------------------------------------- datasets */

function tally(list) {
  const m = new Map();
  for (const k of list) m.set(k, (m.get(k) ?? 0) + 1);
  return [...m.entries()].sort((a, b) => String(a[0]).localeCompare(String(b[0]), "en", { numeric: true }));
}

const LANGUAGE_LABELS = {
  en: "English",
  "en+hi": "English and Hindi",
  "en+gu": "English and Gujarati",
  "en+tl": "English and Tagalog",
  indian_english: "Indian English",
  filipino_english: "Filipino English",
  hindi_english: "Hindi and English",
  tagalog_english: "Tagalog and English",
};

function crossTab(records, tierOf, langOf) {
  const tiers = tally(records.map(tierOf));
  const langs = tally(records.map(langOf));
  const cells = {};
  for (const r of records) {
    const key = `${tierOf(r)}|${langOf(r)}`;
    cells[key] = (cells[key] ?? 0) + 1;
  }
  return {
    total: records.length,
    tiers: tiers.map(([key, count]) => ({ key: String(key), label: String(key), count })),
    languages: langs.map(([key, count]) => ({
      key: String(key),
      label: LANGUAGE_LABELS[String(key)] ?? String(key),
      count,
    })),
    cells,
  };
}

/**
 * Fallbacks for a checkout that does not carry the regenerated data files.
 *
 * `ground-truth.jsonl`, `scenarios.jsonl` and the sample splits are rebuilt from a seed
 * rather than committed (LAYOUT 2.6), so a build from a clone of the public repository has
 * no line-level file to count. The manifests and datasheets ARE committed and carry the
 * same counts, so the counts come from those instead. A build beside the full working tree
 * still reads the ground truth and is unchanged.
 *
 * Without this the site said "not a dataset" for all three suites on a clone, which is
 * false: the datasets exist, and the repository documents them. `countedFrom` records which
 * of the two routes produced the figures, and the pages print it.
 */

/** A table's rows as [firstCell, number] pairs, for the count tables in the datasheets. */
function countsFromTable(table, keyCol, valueCol) {
  const out = [];
  for (const r of table?.rows ?? []) {
    const key = (r[keyCol] ?? "").replace(/[`*]/g, "").trim();
    const n = Number((r[valueCol] ?? "").replace(/[^0-9]/g, ""));
    if (key && Number.isFinite(n) && n > 0) out.push([key, n]);
  }
  return out;
}

const MESSY_SCAN_LANGUAGE_KEYS = {
  "English only": "en",
  "English and Hindi": "en+hi",
  "English and Gujarati": "en+gu",
  "English and Tagalog": "en+tl",
};

/** Messy Scan from MANIFEST.md and datasheet.md, when ground-truth.jsonl is absent. */
function messyScanFromDocs() {
  const man = readText("datasets/messy-scan/MANIFEST.md");
  const sheet = readText("datasets/messy-scan/datasheet.md");
  if (!man || !sheet) return { present: false };
  const manBlocks = toBlocks(man);
  const sheetBlocks = toBlocks(sheet);

  const splits = countsFromTable(
    findTable(manBlocks, (h) => h[0] === "Split" && h[1] === "Documents"), 0, 1,
  );
  const tiers = countsFromTable(
    findTable(sheetBlocks, (h) => h[0] === "Tier" && h.includes("Documents")), 0, 3,
  );
  const langs = countsFromTable(
    findTable(sheetBlocks, (h) => h[0] === "Languages on the page"), 0, 1,
  );
  const types = countsFromTable(
    findTable(sheetBlocks, (h) => h[0] === "Type" && h[1] === "Subtype"), 1, 2,
  ).filter(([k]) => k.toLowerCase() !== "total");

  if (!tiers.length) return { present: false };
  const total = tiers.reduce((n, [, c]) => n + c, 0);
  const version = /Dataset version (\S+)/.exec(man)?.[1] ?? null;
  const seed = Number(/Seed (\d+)/.exec(man)?.[1] ?? "") || null;
  const bySplit = Object.fromEntries(splits);

  return {
    present: true,
    countedFrom: "MANIFEST.md and datasheet.md",
    version,
    seed,
    unit: "document",
    unitPlural: "documents",
    path: "datasets/messy-scan",
    samplePath: "datasets/messy-scan/sample",
    sampleCount: bySplit.public_sample ?? null,
    privateCount: bySplit.private_holdout ?? null,
    splits: splits.map(([key, count]) => ({ key, count })),
    types: types.map(([key, count]) => ({ key, count })),
    // No per-cell breakdown is published, so the tier and language counts stand alone and
    // the cross-tab carries no cells. The filter then reports a tier or a language total
    // rather than an invented intersection.
    cross: {
      total,
      tiers: tiers.map(([key, count]) => ({ key: `T${key}`, label: `T${key}`, count })),
      languages: langs.map(([key, count]) => ({
        key: MESSY_SCAN_LANGUAGE_KEYS[key] ?? key,
        label: key,
        count,
      })),
      cells: {},
    },
  };
}

function datasetMessyScan() {
  const gt = readLines("datasets/messy-scan/ground-truth.jsonl");
  if (!gt) return messyScanFromDocs();
  const records = gt.map((l) => JSON.parse(l));
  const sample = readLines("datasets/messy-scan/sample/ground-truth.jsonl");
  const priv = readLines("datasets/messy-scan/private/ground-truth.jsonl");
  const first = records[0] ?? {};
  return {
    present: true,
    countedFrom: "ground-truth.jsonl",
    version: first.dataset_version ?? null,
    seed: first.seed ?? null,
    unit: "document",
    unitPlural: "documents",
    path: "datasets/messy-scan",
    samplePath: "datasets/messy-scan/sample",
    sampleCount: sample ? sample.length : null,
    privateCount: priv ? priv.length : null,
    splits: tally(records.map((r) => r.split)).map(([key, count]) => ({ key, count })),
    types: tally(records.map((r) => r.doc_type)).map(([key, count]) => ({ key, count })),
    cross: crossTab(
      records,
      (r) => `T${r.tier}`,
      (r) => (r.languages ?? []).join("+"),
    ),
  };
}

/** Honest Containment from manifest.json, when scenarios.jsonl is absent. */
function honestContainmentFromManifest(manifest) {
  const mix = manifest.mix ?? {};
  const counts = manifest.counts ?? {};
  const tiers = Object.entries(mix.tier ?? {}).map(([key, count]) => ({ key, label: key, count }));
  const languages = Object.entries(mix.language ?? {}).map(([key, count]) => ({
    key,
    label: LANGUAGE_LABELS[key] ?? key,
    count,
  }));
  return {
    present: true,
    countedFrom: "manifest.json",
    version: manifest.dataset_version ?? null,
    seed: manifest.seed ?? null,
    unit: "contact",
    unitPlural: "contacts",
    path: "datasets/honest-containment",
    samplePath: "datasets/honest-containment",
    sampleCount: counts.scenarios_public ?? null,
    privateCount: counts.scenarios_private ?? null,
    splits: [],
    types: Object.entries(mix.domain ?? {}).map(([key, count]) => ({ key, count })),
    audio: counts.audio_selected ?? null,
    // The manifest publishes each dimension's totals, not their intersection, so the
    // cross-tab carries no cells and a two-way filter reports no count rather than a guess.
    cross: { total: counts.scenarios_public ?? null, tiers, languages, cells: {} },
  };
}

function datasetHonestContainment() {
  const lines = readLines("datasets/honest-containment/scenarios.jsonl");
  const manifest = readJson("datasets/honest-containment/manifest.json");
  if (!manifest) return { present: false };
  // scenarios.jsonl is rebuilt rather than committed, so on a clone the counts come from
  // manifest.json, which carries the same mix tables the records would have been tallied into.
  if (!lines) return honestContainmentFromManifest(manifest);
  const records = lines.map((l) => JSON.parse(l));
  const sample = readLines("datasets/honest-containment/private/scenarios.jsonl");
  return {
    present: true,
    countedFrom: "scenarios.jsonl",
    version: manifest.dataset_version ?? null,
    seed: manifest.seed ?? null,
    unit: "contact",
    unitPlural: "contacts",
    path: "datasets/honest-containment",
    samplePath: "datasets/honest-containment",
    sampleCount: manifest.counts?.scenarios_public ?? null,
    privateCount: manifest.counts?.scenarios_private ?? (sample ? sample.length : null),
    splits: tally(records.map((r) => r.split)).map(([key, count]) => ({ key, count })),
    types: tally(records.map((r) => r.domain)).map(([key, count]) => ({ key, count })),
    audio: manifest.counts?.audio_selected ?? null,
    cross: crossTab(
      records,
      (r) => r.tier,
      (r) => r.language?.label ?? "unknown",
    ),
  };
}

/** Exception Economics from manifest.json, when ground-truth.jsonl is absent. */
function exceptionEconomicsFromManifest(manifest) {
  const splits = manifest.split_counts ?? {};
  return {
    present: true,
    countedFrom: "manifest.json",
    version: manifest.dataset_version ?? null,
    seed: manifest.seed ?? null,
    unit: "work item",
    unitPlural: "work items",
    path: "datasets/exception-economics",
    samplePath: "datasets/exception-economics/sample",
    sampleCount: splits.public_sample ?? null,
    privateCount: splits.private_holdout ?? null,
    splits: Object.entries(splits).map(([key, count]) => ({ key, count })),
    types: Object.entries(manifest.work_type_counts ?? {}).map(([key, count]) => ({ key, count })),
    groundTruthSha: manifest.ground_truth_sha256 ?? null,
    populations: manifest.populations ?? null,
    lifecycle: manifest.lifecycle_counts ?? null,
    cross: {
      total: manifest.items ?? null,
      tiers: Object.entries(manifest.tier_counts ?? {}).map(([key, count]) => ({
        key: `T${key}`,
        label: `T${key}`,
        count,
      })),
      languages: [{ key: "not-applicable", label: "not-applicable", count: manifest.items ?? null }],
      cells: {},
    },
  };
}

function datasetExceptionEconomics() {
  const manifest = readJson("datasets/exception-economics/manifest.json");
  const lines = readLines("datasets/exception-economics/ground-truth.jsonl");
  if (!manifest) return { present: false };
  // As above: the ground truth is rebuilt, and manifest.json carries every count it holds.
  if (!lines) return exceptionEconomicsFromManifest(manifest);
  const records = lines.map((l) => JSON.parse(l));
  const sample = readLines("datasets/exception-economics/sample/ground-truth.jsonl");
  return {
    present: true,
    countedFrom: "ground-truth.jsonl",
    version: manifest.dataset_version ?? null,
    seed: manifest.seed ?? null,
    unit: "work item",
    unitPlural: "work items",
    path: "datasets/exception-economics",
    samplePath: "datasets/exception-economics/sample",
    sampleCount: sample ? sample.length : null,
    privateCount: manifest.split_counts?.private_holdout ?? null,
    splits: Object.entries(manifest.split_counts ?? {}).map(([key, count]) => ({ key, count })),
    types: Object.entries(manifest.work_type_counts ?? {}).map(([key, count]) => ({ key, count })),
    groundTruthSha: manifest.ground_truth_sha256 ?? null,
    populations: manifest.populations ?? null,
    lifecycle: manifest.lifecycle_counts ?? null,
    cross: crossTab(
      records,
      (r) => `T${r.tier}`,
      () => "not-applicable",
    ),
  };
}

/* -------------------------------------------------------------------- harness */

function harnessFacts() {
  const pyproject = readText("harness/pyproject.toml") ?? "";
  const version = /^version\s*=\s*"([^"]+)"/m.exec(pyproject)?.[1] ?? null;
  const yaml = readText("harness/src/entail_bench/data/models.yaml") ?? "";
  // Minimal reader for this file's shape: a list of `- name:` blocks with flat keys.
  const models = [];
  let cur = null;
  for (const raw of yaml.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (/^\s*-\s+name:\s*(\S+)/.test(line)) {
      cur = { name: /^\s*-\s+name:\s*(\S+)/.exec(line)[1] };
      models.push(cur);
      continue;
    }
    if (!cur) continue;
    const kv = /^\s{4}([a-z_]+):\s*(.*)$/.exec(line);
    if (kv) {
      const key = kv[1];
      let value = (kv[2] ?? "").trim();
      if (key === "note" || key === "options") {
        cur[key] = null;
        continue;
      }
      if (value.startsWith("[")) {
        cur[key] = value.replace(/^\[|\]$/g, "").split(",").map((s) => s.trim()).filter(Boolean);
      } else if (value !== "" && value !== ">-") {
        cur[key] = value.replace(/^[\"']|[\"']$/g, "");
      }
    }
  }
  const readme = readText("harness/README.md");
  return {
    version,
    models: models.filter((m) => m.kind !== "fixture"),
    readmePath: "harness/README.md",
    readme: readme ? toBlocks(readme) : [],
    licence: readText("harness/LICENSE") ? "harness/LICENSE" : null,
  };
}

const harness = harnessFacts();

/* -------------------------------------------------------------------- results */

const NOT_RUN = "not run";

function resultsDirFor(suite) {
  const base = join(ROOT, "results");
  if (!existsSync(base)) return null;
  const match = readdirSync(base).find((d) => d === suite || d.startsWith(`${suite}-v`));
  return match ? `results/${match}` : null;
}

function reproduceFor(dir, fallbacks, documents = []) {
  const docs = documents
    .map((path) => {
      const md = readText(path);
      if (md === null) return null;
      const h1 = /^#\s+(.*)$/m.exec(md)?.[1] ?? path;
      const headings = toBlocks(md)
        .filter((b) => b.t === "h" && b.level === 2)
        .map((b) => b.text);
      return { path, title: h1, headings };
    })
    .filter(Boolean);

  if (dir && exists(`${dir}/reproduce.md`)) {
    const md = readText(`${dir}/reproduce.md`);
    return { source: `${dir}/reproduce.md`, present: true, commands: codeBlocksWithHeadings(md), documents: docs };
  }
  const out = [];
  for (const f of fallbacks) {
    const md = readText(f.path);
    if (!md) continue;
    const found = codeBlocksWithHeadings(md).filter((c) => c.lang === "bash" || c.lang === "sh");
    for (const c of found.slice(0, f.take ?? 99)) out.push({ ...c, heading: `${f.label}: ${c.heading ?? ""}`.trim() });
  }
  return { source: fallbacks.map((f) => f.path).join(", "), present: false, commands: out, documents: docs };
}

/** Messy Scan: no results folder exists, so the roster comes from the harness registry. */
function resultsMessyScan(dir) {
  // Charter 10.2 gives the suite-level reason; strip its "not run — " prefix, because the
  // status column already carries the words "not run" and would otherwise print them twice.
  const reason = (charterStatus["messy-scan"]?.status ?? NOT_RUN).replace(/^not run\s*[—-]\s*/, "");
  const rows = harness.models.map((m) => {
    const vars = m.env_vars ?? [];
    const why = vars.length ? `${vars.join(", ")} not set; no reachable model interface` : reason;
    return {
      id: m.name,
      system: m.name,
      provider: m.provider ?? "",
      kind: m.kind ?? "",
      modelVersion: m.model_id ?? null,
      runs: 0,
      status: NOT_RUN,
      reason: why,
      cells: {},
    };
  });
  return {
    present: Boolean(dir),
    dir,
    status: NOT_RUN,
    reason,
    runDate: null,
    datasetVersion: null,
    harnessVersion: harness.version,
    scorerVersion: null,
    columns: [
      { key: "system", label: "System", type: "text", sortable: true },
      { key: "provider", label: "Provider", type: "text", sortable: true },
      { key: "modelVersion", label: "Model version", type: "text", sortable: true },
      { key: "stp", label: "Straight-through %", type: "number", sortable: true },
      { key: "accuracy", label: "Field accuracy %", type: "number", sortable: true },
      { key: "cost", label: "Cost per doc", type: "number", sortable: true },
      { key: "runs", label: "Runs", type: "number", sortable: true },
    ],
    rows,
  };
}

/**
 * A preflight failure is written for an engineer reading a log. The leaderboard cell needs
 * the same fact in a few words; the verbatim text is published under the table, unchanged.
 */
function shortenPreflight(failures) {
  const parts = [];
  for (const f of failures ?? []) {
    const key = /environment variable ([A-Z_]+) is not set/.exec(f);
    if (key) {
      parts.push(`${key[1]} not set`);
      continue;
    }
    const cfg = /^(\S+) is not configured:/.exec(f);
    if (cfg) {
      parts.push(`${cfg[1]} endpoints still read placeholder`);
      continue;
    }
    parts.push(f.length > 80 ? `${f.slice(0, 77)}...` : f);
  }
  return [...new Set(parts)].join("; ");
}

function resultsHonestContainment(dir) {
  if (!dir || !exists(`${dir}/results.csv`)) return { present: false, dir, rows: [], columns: [] };
  const csv = readText(`${dir}/results.csv`);
  const table = parseCsv(csv);
  const head = table[0] ?? [];
  const idx = (name) => head.indexOf(name);
  const runHeaders = [];
  for (const sys of table.slice(1)) {
    const name = sys[idx("system")];
    const runJson = readJson(`${dir}/runs/${name}/run-1/run.json`);
    if (runJson) runHeaders.push(runJson);
  }
  const first = runHeaders[0] ?? {};
  const preflightBySystem = new Map();
  for (const header of runHeaders) preflightBySystem.set(header.agent, header.preflight_failures ?? []);

  const rows = table.slice(1).map((r) => {
    const id = r[idx("system")] ?? "";
    const failures = preflightBySystem.get(id) ?? [];
    return {
      id,
      system: r[idx("display_name")] ?? id,
      provider: "",
      kind: "",
      modelVersion: null,
      runs: Number(r[idx("runs")] ?? 0),
      status: r[idx("status")] ?? NOT_RUN,
      reason: shortenPreflight(failures) || r[idx("reason")] || "",
      reasonFull: failures.length ? failures : [r[idx("reason")] ?? ""],
      cells: {},
    };
  });
  return {
    present: true,
    dir,
    status: NOT_RUN,
    reason: rows[0]?.reason ?? NOT_RUN,
    runDate: first.started_at ? String(first.started_at).slice(0, 10) : null,
    datasetVersion: first.dataset_version ?? null,
    harnessVersion: first.harness_version ?? harness.version,
    harnessCommit: first.harness_commit ?? null,
    datasetManifestSha: first.dataset_manifest_sha256 ? String(first.dataset_manifest_sha256).slice(0, 16) : null,
    promptHashes: first.prompt_hashes ?? null,
    scenarios: first.scenarios ?? null,
    columns: [
      { key: "system", label: "System", type: "text", sortable: true },
      { key: "ours", label: "Containment 3.9 %", type: "number", sortable: true },
      { key: "refB", label: "Containment, def. B %", type: "number", sortable: true },
      { key: "false", label: "False containment %", type: "number", sortable: true },
      { key: "escRecall", label: "Escalation recall %", type: "number", sortable: true },
      { key: "hallucinated", label: "Hallucinated policy %", type: "number", sortable: true },
      { key: "runs", label: "Runs", type: "number", sortable: true },
    ],
    rows,
  };
}

function resultsExceptionEconomics(dir) {
  if (!dir) return { present: false, dir, rows: [], columns: [] };
  const scores = readJson(`${dir}/scores-baseline.json`);
  const all = readJson(`${dir}/scores-all.json`);
  const leaderboardMd = readText(`${dir}/leaderboard.md`);
  const statusTableBlock = leaderboardMd
    ? findTable(toBlocks(leaderboardMd), (h) => h[0] === "System" && h.includes("Status"))
    : null;
  const rows = (statusTableBlock?.rows ?? []).map((r) => ({
    id: slugify(r[0] ?? ""),
    system: (r[0] ?? "").trim(),
    provider: "",
    kind: "",
    modelVersion: null,
    runs: 0,
    status: NOT_RUN,
    reason: (r[r.length - 1] ?? "").replace(/^not run —\s*/, "").trim(),
    cells: {},
  }));
  return {
    present: true,
    dir,
    status: NOT_RUN,
    reason: rows[0]?.reason ?? NOT_RUN,
    runDate: null,
    datasetVersion: scores?.dataset_version ?? null,
    harnessVersion: harness.version,
    scorerVersion: scores?.scorer_version ?? null,
    groundTruthSha: scores?.ground_truth_sha256 ? String(scores.ground_truth_sha256).slice(0, 16) : null,
    columns: [
      { key: "system", label: "System", type: "text", sortable: true },
      { key: "automation", label: "Automation rate %", type: "number", sortable: true },
      { key: "rework", label: "Rework min / 1,000 automated", type: "number", sortable: true },
      { key: "reviewer", label: "Reviewer min / 1,000 items", type: "number", sortable: true },
      { key: "net", label: "Net cost per item", type: "number", sortable: true },
      { key: "runs", label: "Runs", type: "number", sortable: true },
    ],
    rows,
    reference: referencePolicy(scores, all),
  };
}

/** The dataset's own reference decision policy. A property of the data, not a system result. */
function referencePolicy(scores, all) {
  if (!scores) return null;
  const thresholds = (scores.thresholds ?? []).map((t) => ({
    threshold: t.threshold ?? null,
    counts: t.counts ?? null,
    rates: t.rates ?? null,
    cost: t.cost ?? null,
    rework: t.rework
      ? {
          minutesPer1000Automated: t.rework.minutes_per_1000_automated ?? null,
          minutesTotal: t.rework.minutes_total ?? null,
          openExposureItems: t.rework.open_exposure?.items ?? null,
          openExposureByClass: t.rework.open_exposure?.by_class ?? null,
          byErrorClass: t.rework.by_error_class ?? null,
        }
      : null,
    reviewer: t.reviewer_minutes
      ? {
          meanPerException: t.reviewer_minutes.mean_per_exception ?? null,
          medianPerException: t.reviewer_minutes.median_per_exception ?? null,
          per1000ItemsAdmitted: t.reviewer_minutes.per_1000_items_admitted ?? null,
          total: t.reviewer_minutes.total ?? null,
          byEntryCode: t.reviewer_minutes.by_entry_code ?? null,
        }
      : null,
    auditMinutes: t.audit_minutes?.total ?? null,
    manualHandlingMinutes: t.manual_handling_minutes?.total ?? null,
    byTier: Object.entries(t.breakdowns?.by_tier ?? {}).map(([tier, v]) => ({
      tier: `T${tier}`,
      admitted: v.admitted ?? null,
      automationRate: v.automation_rate ?? null,
      automatedWrong: v.automated_wrong ?? null,
      wrongShare: v.wrong_automation_rate_of_automated ?? null,
      reviewerMinutes: v.reviewer_minutes ?? null,
      reworkMinutes: v.rework_minutes ?? null,
      openExposure: v.open_exposure ?? null,
    })),
  }));
  return {
    note: scores.decision_policy ?? null,
    isModelRun: scores.decision_policy_is_a_model_run ?? false,
    labourStatus: scores.labour_model_status ?? null,
    population: scores.population ?? null,
    populationAll: all?.population ?? null,
    thresholds,
    sweepBest: scores.sweep?.best ?? null,
    sweepMinimising: scores.sweep?.minimising_threshold ?? null,
    sweepPoints: (scores.sweep?.points ?? []).filter((_, n) => n % 5 === 0),
  };
}

function resultsDay60(dir) {
  const csv = readText("day-60/scoresheet.csv");
  const lines = csv ? parseCsv(csv) : [];
  const head = lines[0] ?? [];
  const at = (row, key) => row[head.indexOf(key)] ?? "";
  const SCORED = new Set(["ratio", "checklist", "computed", "banded"]);
  const TOTALS = new Set(["subtotal", "total", "score"]);
  const rubric = lines
    .slice(1)
    .filter((r) => SCORED.has(at(r, "kind")))
    .map((r) => ({
      section: at(r, "section"),
      lineId: at(r, "line_id"),
      line: at(r, "line"),
      kind: at(r, "kind"),
      maxPoints: at(r, "max_points") === "" ? null : Number(at(r, "max_points")),
      measure: at(r, "measure"),
      unit: at(r, "unit"),
      observed: at(r, "observed_value") === "" ? null : at(r, "observed_value"),
      awarded: at(r, "points_awarded") === "" ? null : Number(at(r, "points_awarded")),
    }));
  const totals = lines
    .slice(1)
    .filter((r) => TOTALS.has(at(r, "kind")))
    .map((r) => ({
      lineId: at(r, "line_id"),
      line: at(r, "line"),
      kind: at(r, "kind"),
      maxPoints: at(r, "max_points") === "" ? null : Number(at(r, "max_points")),
      awarded: at(r, "points_awarded") === "" ? null : Number(at(r, "points_awarded")),
    }));
  // Rows the assessor fills in before scoring: tier, window, assessors, the standing rules.
  const context = lines
    .slice(1)
    .filter((r) => at(r, "kind") === "context")
    .map((r) => ({ lineId: at(r, "line_id"), line: at(r, "line"), measure: at(r, "measure"), note: at(r, "note") }));
  return {
    present: Boolean(dir),
    dir,
    status: NOT_RUN,
    reason: charterStatus["day-60"]?.status ?? NOT_RUN,
    runDate: null,
    datasetVersion: null,
    harnessVersion: null,
    scoresheet: "day-60/scoresheet.csv",
    rubricDoc: "day-60/rubric.md",
    selfAssessment: "day-60/self-assessment.md",
    scriptedIncidents: "day-60/scripted-incidents.md",
    rubric,
    totals,
    context,
    columns: [
      { key: "system", label: "Deployment", type: "text", sortable: true },
      { key: "tier", label: "Exercise tier", type: "text", sortable: true },
      { key: "score", label: "Day-60 score", type: "number", sortable: true },
      { key: "runs", label: "Exercises", type: "number", sortable: true },
    ],
    rows: [],
  };
}

/** RFC 4180 enough for the two CSVs in this folder. */
function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (c === '"') {
        quoted = false;
      } else {
        cell += c;
      }
      continue;
    }
    if (c === '"') quoted = true;
    else if (c === ",") {
      row.push(cell);
      cell = "";
    } else if (c === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (c !== "\r") cell += c;
  }
  if (cell !== "" || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows.filter((r) => r.some((c) => c.trim() !== ""));
}

/* ---------------------------------------------------------------- assembly */

const SUITES = [
  {
    slug: "messy-scan",
    dataset: datasetMessyScan(),
    results: (dir) => resultsMessyScan(dir),
    reproduceFallback: [
      { path: "datasets/messy-scan/README.md", label: "Rebuild the dataset", take: 3 },
      { path: "harness/README.md", label: "Run the suite", take: 6 },
    ],
    documents: ["datasets/messy-scan/README.md", "datasets/messy-scan/datasheet.md", "harness/README.md"],
  },
  {
    slug: "honest-containment",
    dataset: datasetHonestContainment(),
    results: (dir) => resultsHonestContainment(dir),
    reproduceFallback: [{ path: "datasets/honest-containment/README.md", label: "Rebuild the dataset" }],
    documents: ["datasets/honest-containment/README.md", "datasets/honest-containment/datasheet.md"],
  },
  {
    slug: "exception-economics",
    dataset: datasetExceptionEconomics(),
    results: (dir) => resultsExceptionEconomics(dir),
    reproduceFallback: [{ path: "datasets/exception-economics/README.md", label: "Rebuild the dataset" }],
    documents: ["datasets/exception-economics/README.md", "datasets/exception-economics/datasheet.md"],
  },
  {
    slug: "day-60",
    dataset: {
      present: false,
      unit: "deployment",
      unitPlural: "deployments",
      // The tier describes the exercise run against a deployment, not an item in a dataset,
      // so the options come from charter 4.5 and carry no count: none has been exercised.
      cross: {
        total: null,
        tiers: (findTable(tierBlocks["4.5"]?.blocks ?? [], (h) => h[0] === "Tier")?.rows ?? []).map((r) => ({
          key: (r[0] ?? "").trim(),
          label: (r[0] ?? "").trim(),
          count: null,
        })),
        languages: [],
        cells: {},
      },
    },
    results: (dir) => resultsDay60(dir),
    reproduceFallback: [],
    documents: ["day-60/rubric.md", "day-60/scripted-incidents.md", "day-60/self-assessment.md"],
  },
];

const suites = SUITES.map((s) => {
  const dir = resultsDirFor(s.slug);
  const results = s.results(dir);
  return {
    slug: s.slug,
    ...suiteFacts[s.slug],
    charterStatus: charterStatus[s.slug] ?? null,
    tier: tierBlocks[tierSectionBySuite[s.slug]] ?? null,
    tierSection: tierSectionBySuite[s.slug],
    dataset: s.dataset,
    results,
    reproduce: reproduceFor(dir, s.reproduceFallback, s.documents ?? []),
    metrics: metrics.filter((m) => m.suite === s.slug),
  };
});

const out = {
  generatedAt: new Date().toISOString().slice(0, 10),
  root: relative(SITE, ROOT).split("\\").join("/"),
  charter: {
    version: charterVersion,
    written: charterWritten,
    path: CHARTER_PATH,
    sections: charterSections,
    preamble: charterPreamble,
    frontMatter: charterFrontMatter,
    noRunStatement,
    firstRunNeeds,
    statusTable: statusTable ?? null,
  },
  clauses: {
    version: clausesVersion,
    path: CLAUSES_PATH,
    index:
      findTable(toBlocks(clausesFull ?? ""), (h) => h[0] === "Clause" && h.includes("Metric"))?.rows.map((r) => ({
        clause: r[0],
        metric: r[1],
        insertion: r[2],
      })) ?? [],
  },
  harness,
  suites,
  metrics,
  sources: sources.sort((a, b) => a.path.localeCompare(b.path)),
};

mkdirSync(join(SITE, "data"), { recursive: true });
writeFileSync(join(SITE, "data", "benchmarks.json"), `${JSON.stringify(out, null, 2)}\n`);

const runRows = suites.flatMap((s) => s.results.rows ?? []);
const ran = runRows.filter((r) => r.status !== NOT_RUN).length;
console.log(
  `build-data: ${sources.length} source files read, ${suites.length} suites, ${runRows.length} leaderboard rows, ${ran} of them run.`,
);
