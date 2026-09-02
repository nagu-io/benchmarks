/**
 * The build-time read of `data/benchmarks.json`, which `scripts/build-data.mjs` writes
 * from the repository root. Every figure on this site comes through here. Nothing in the
 * page components holds a number of its own.
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

export type Block =
  | { t: "h"; level: number; text: string; id: string }
  | { t: "p"; text: string }
  | { t: "ul"; items: string[] }
  | { t: "ol"; items: string[] }
  | { t: "table"; head: string[]; rows: string[][] }
  | { t: "code"; lang: string; code: string }
  | { t: "quote"; blocks: Block[] }
  | { t: "hr" };

export type Column = { key: string; label: string; type: "text" | "number"; sortable: boolean };

export type Row = {
  id: string;
  system: string;
  provider: string;
  kind: string;
  modelVersion: string | null;
  runs: number;
  status: string;
  reason: string;
  /** The reason exactly as the source file writes it, where the cell carries a shorter form. */
  reasonFull?: string[];
  cells: Record<string, number | string | null>;
};

export type Dimension = { key: string; label: string; count: number | null };

export type Dataset = {
  present: boolean;
  version?: string | null;
  seed?: number | string | null;
  unit?: string;
  unitPlural?: string;
  path?: string;
  samplePath?: string;
  sampleCount?: number | null;
  privateCount?: number | null;
  audio?: number | null;
  groundTruthSha?: string | null;
  populations?: Record<string, number> | null;
  lifecycle?: Record<string, number> | null;
  splits?: { key: string; count: number }[];
  types?: { key: string; count: number }[];
  cross?: {
    total: number | null;
    tiers: Dimension[];
    languages: Dimension[];
    cells: Record<string, number>;
  };
};

export type ReferenceThreshold = {
  threshold: number | null;
  counts: { items_received?: number; items_admitted?: number; automated?: number; automated_wrong?: number; exceptions?: number } | null;
  rates: {
    automation_rate?: number;
    exception_rate?: number;
    wrong_automation_rate_of_automated?: number;
    identity_holds?: boolean;
  } | null;
  cost: {
    net_cost_per_item_inr?: number;
    net_cost_per_item_usd?: number;
    rate_status?: string;
    reviewer_rate_inr_per_hour?: number;
    reviewer_rate_usd_per_hour?: number;
    machine_cost_inr?: number;
    machine_cost_usd?: number;
    basis?: string;
  } | null;
  rework: {
    minutesPer1000Automated: number | null;
    minutesTotal: number | null;
    openExposureItems: number | null;
    openExposureByClass: Record<string, number> | null;
  } | null;
  reviewer: {
    meanPerException: number | null;
    medianPerException: number | null;
    per1000ItemsAdmitted: number | null;
    total: number | null;
  } | null;
  auditMinutes: number | null;
  manualHandlingMinutes: number | null;
  byTier: {
    tier: string;
    admitted: number | null;
    automationRate: number | null;
    automatedWrong: number | null;
    wrongShare: number | null;
    reviewerMinutes: number | null;
    reworkMinutes: number | null;
    openExposure: number | null;
  }[];
};

export type Reference = {
  note: string | null;
  isModelRun: boolean;
  labourStatus: Record<string, string | number> | null;
  population: string | null;
  thresholds: ReferenceThreshold[];
  sweepBest: Record<string, number> | null;
  sweepMinimising: number | null;
  sweepPoints: Record<string, number>[];
};

export type RubricLine = {
  section: string;
  lineId: string;
  line: string;
  kind: string;
  maxPoints: number | null;
  measure: string;
  unit: string;
  observed: string | null;
  awarded: number | null;
};

export type Results = {
  present: boolean;
  dir: string | null;
  status: string;
  reason: string;
  runDate: string | null;
  datasetVersion: string | null;
  harnessVersion: string | null;
  harnessCommit?: string | null;
  scorerVersion?: string | null;
  groundTruthSha?: string | null;
  datasetManifestSha?: string | null;
  promptHashes?: Record<string, string> | null;
  scenarios?: number | null;
  columns: Column[];
  rows: Row[];
  reference?: Reference | null;
  rubric?: RubricLine[];
  totals?: { lineId: string; line: string; kind: string; maxPoints: number | null; awarded: number | null }[];
  context?: { lineId: string; line: string; measure: string; note: string }[];
  scoresheet?: string;
  rubricDoc?: string;
  selfAssessment?: string;
  scriptedIncidents?: string;
};

export type Suite = {
  slug: string;
  name: string;
  line: string;
  measures: string;
  unit: string;
  headline: string;
  builtFrom: string;
  charterStatus: { dataset: string; harness: string; runs: string; status: string } | null;
  tierSection: string;
  tier: { title: string; id: string; blocks: Block[] } | null;
  dataset: Dataset;
  results: Results;
  reproduce: {
    source: string;
    present: boolean;
    commands: { heading: string | null; lang: string; code: string }[];
    documents: { path: string; title: string; headings: string[] }[];
  };
  metrics: Metric[];
};

export type Metric = {
  name: string;
  suite: string | null;
  section: string;
  clause: string;
  title: string;
  anchor: string | null;
  blocks: Block[];
};

export type Benchmarks = {
  generatedAt: string;
  root: string;
  charter: {
    version: string | null;
    written: string | null;
    path: string;
    sections: { number: string | null; title: string; id: string; blocks: Block[] }[];
    preamble: Block[];
    frontMatter: string[];
    noRunStatement: string | null;
    firstRunNeeds: string | null;
    statusTable: { t: "table"; head: string[]; rows: string[][] } | null;
  };
  clauses: { version: string | null; path: string; index: { clause: string; metric: string; insertion: string }[] };
  harness: {
    version: string | null;
    models: { name: string; provider?: string; kind?: string; env_vars?: string[] }[];
    readmePath: string;
    readme: Block[];
    licence: string | null;
  };
  suites: Suite[];
  metrics: Metric[];
  sources: { path: string; bytes: number; sha256: string }[];
};

const FILE = join(process.cwd(), "data", "benchmarks.json");

function load(): Benchmarks {
  if (!existsSync(FILE)) {
    throw new Error(
      "data/benchmarks.json is missing. Run `pnpm data` (it reads the repository root and writes the file the pages are built from).",
    );
  }
  return JSON.parse(readFileSync(FILE, "utf8")) as Benchmarks;
}

export const benchmarks: Benchmarks = load();

export function suite(slug: string): Suite {
  const found = benchmarks.suites.find((s) => s.slug === slug);
  if (!found) throw new Error(`No suite '${slug}' in data/benchmarks.json.`);
  return found;
}

export const SUITE_SLUGS = ["messy-scan", "honest-containment", "exception-economics", "day-60"] as const;

export function charterSection(number: string) {
  return benchmarks.charter.sections.find((s) => s.number === number) ?? null;
}

/** Drop the leading clause number the charter puts at the front of each paragraph. */
export function stripNumber(text: string): string {
  return text.replace(/^\d+(\.\d+)*\s+/, "");
}

/** The label the charter opens a numbered paragraph with, e.g. "Formula." */
export function paragraphLabel(text: string): { label: string | null; rest: string } {
  const body = stripNumber(text);
  const m = /^([A-Z][^.]{0,60}?)\.\s+(.*)$/.exec(body);
  if (!m) return { label: null, rest: body };
  return { label: m[1] ?? null, rest: m[2] ?? "" };
}

export function fmtInt(n: number | null | undefined): string {
  return n === null || n === undefined ? "not run" : n.toLocaleString("en-GB");
}

export function fmtRate(n: number | null | undefined): string {
  return n === null || n === undefined ? "not run" : `${(n * 100).toFixed(1)}`;
}

export function fmtMinutes(n: number | null | undefined): string {
  return n === null || n === undefined ? "not run" : n.toLocaleString("en-GB", { maximumFractionDigits: 1 });
}
