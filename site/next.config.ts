import type { NextConfig } from "next";

/**
 * bench.entailmentlabs.com is a static site. Nothing on it needs a server: every
 * figure is read from the repository root by `scripts/build-data.mjs` before the
 * build, and every page is prerendered from that one file. So `output: export`.
 *
 * Static export cannot set response headers. The header set this site needs sits in
 * `public/_headers` and in README.md, to be applied at the CDN.
 */
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  reactStrictMode: true,
  poweredByHeader: false,
  images: { unoptimized: true },
};

export default nextConfig;
