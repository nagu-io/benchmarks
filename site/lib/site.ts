import type { Metadata } from "next";

export const SITE_NAME = "Entailment Labs benchmarks";
export const SITE_SHORT = "Entailment Labs";
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://bench.entailmentlabs.com").replace(/\/$/, "");
export const MAIN_SITE_URL = "https://entailmentlabs.com";
export const REPO = "nagu-io/benchmarks";
export const REPO_URL = `https://github.com/${REPO}`;
export const REPO_PUBLISHED = true;

export const EMAILS = {
  hello: "hello@entailmentlabs.com",
  security: "security@entailmentlabs.com",
} as const;

export const DEFAULT_DESCRIPTION =
  "Four benchmark suites for document, voice, back-office and AI-operations systems, with the definitions written so a BPO can put them in a contract.";

export const SUITE_LINKS = [
  { label: "Messy Scan", href: "/messy-scan" },
  { label: "Honest Containment", href: "/honest-containment" },
  { label: "Exception Economics", href: "/exception-economics" },
  { label: "Day-60", href: "/day-60" },
] as const;

export const NAV = [
  { label: "Messy Scan", href: "/messy-scan" },
  { label: "Honest Containment", href: "/honest-containment" },
  { label: "Exception Economics", href: "/exception-economics" },
  { label: "Day-60", href: "/day-60" },
  { label: "Methodology", href: "/methodology" },
  { label: "Run it yourself", href: "/run-it-yourself" },
  { label: "Changelog", href: "/changelog" },
  { label: "Disputes", href: "/disputes" },
] as const;

/** A path inside the public repository, and the same path inside this working tree. */
export function repoPath(path: string): string {
  return `${REPO_URL}/tree/main/${path}`;
}

export function pageMeta(opts: { title: string; description: string; path: string }): Metadata {
  const url = `${SITE_URL}${opts.path === "/" ? "" : opts.path}`;
  const title = opts.path === "/" ? SITE_NAME : `${opts.title} — ${SITE_NAME}`;
  return {
    title: { absolute: title },
    description: opts.description,
    alternates: { canonical: url },
    openGraph: { title, description: opts.description, url, siteName: SITE_NAME, type: "website", locale: "en_GB" },
    twitter: { card: "summary", title, description: opts.description },
  };
}
