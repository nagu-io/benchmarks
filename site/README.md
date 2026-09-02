# bench.entailmentlabs.com

The benchmark site: the source of the pages at bench.entailmentlabs.com. Next.js 15,
TypeScript strict, Tailwind v4 on the Entailment Labs brand tokens, IBM Plex through
`@fontsource` at the versions the marketing site pins. Static export: nothing on the site
needs a server.

It sits inside this repository, one directory below the data it reads, so that the claim the
next section makes can be checked rather than taken on trust.

## The rule this site is built around

**No figure on any page is typed by hand.** `scripts/build-data.mjs` runs before every build,
reads the repository root — the charter and its parts, the dataset manifests and ground
truth, the harness registry, the results folders and the Day-60 scoresheet — and writes
`data/benchmarks.json`. Every page is prerendered from that one file, and `lib/data.ts` is
the only way into it. The generated file names every source it read, with a byte count and a
hash prefix, and `/methodology` prints that list.

A value that no source file carries is emitted as `null` and rendered as `not run` with the
reason its source gives, per charter 3.1.8. Charts with nothing to plot render an explicit
empty state, never example bars. The charter's arithmetic examples are shown on
`/methodology`, where they sit in context and carry their own warning, and are left out of
the suite pages, where beside a table of `not run` they would read as results.

If you want to check that, the fastest route is `grep` for a digit in `app/` and
`components/`: what you will find is column widths, font sizes and charter section numbers.

## Commands

```bash
pnpm install
pnpm data        # rebuild data/benchmarks.json from the repository root
pnpm dev         # http://localhost:3000
pnpm build       # prebuild runs pnpm data, then next build; static export into out/
pnpm typecheck
bash scripts/_serve.sh 3100     # serve out/ for QA
node scripts/_shot.mjs / /messy-scan/   # 1440px screenshots into qa/
```

`BENCH_ROOT` overrides where the data script reads from. It defaults to the parent
directory, which is the repository root.

## Layout

```
app/                 one route per page; the four suite routes are thin wrappers
components/          Section, TableWrap, SortableTable, Leaderboard, BarChart, Markdown,
                     Definitions, Provenance, Reproduce, ReferencePolicy, Day60Rubric
lib/data.ts          the typed read of data/benchmarks.json
lib/site.ts          names, navigation, the public repository
scripts/build-data.mjs  the only place a number enters this site
data/benchmarks.json    generated; never edited by hand; not committed
qa/                  1440px screenshots; not committed
```

## Tables and charts

`SortableTable` is the one table component: a button inside each sortable `th`, `aria-sort`
on the header, a polite live region announcing the change, and the cycle ascending →
descending → unsorted. No library. A value that was never produced sorts last in both
directions, because it is not a low score.

`BarChart` draws the three marks: a yellow fill for the share the machine carried, a 2px red
stroke under the share a person had to touch, rule-grey hairlines for the frame. Review red
is a mark and never a fill under the Entailment Labs brand rules, so the reviewed share is an
underline rather than a block of colour.

## Deployment

Static export, so the whole site is `out/`. It sets no response headers of its own.
`public/_headers` carries the set to apply at the CDN (Cloudflare Pages and Netlify read that
file directly; on another host, copy the values into its header configuration).

The site is deployed from this directory on every push to `main`, with the project's root
directory set to `site`. The build runs `pnpm build`, which regenerates the data first, so a
deployed page can never be older than the results files in this repository.

The `bench.entailmentlabs.com` name is not connected yet: DNS and the certificate are open
items, and until they are done the site answers on its Vercel address. `lib/site.ts` names
the eventual host, and `NEXT_PUBLIC_SITE_URL` overrides it.

## What is still missing

Two results folders do not exist: `results/messy-scan-v1.0` and a Day-60 results folder. The
pages for those suites say so, and their leaderboards are built from the harness model
registry and the Day-60 scoresheet instead. When the runs happen and the folders appear, the
data script picks them up with no change to any page.
