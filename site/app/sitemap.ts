import type { MetadataRoute } from "next";
import { NAV, SITE_URL } from "@/lib/site";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ["/", ...NAV.map((n) => n.href)];
  return paths.map((path) => ({
    url: `${SITE_URL}${path === "/" ? "/" : `${path}/`}`,
    changeFrequency: "monthly" as const,
    priority: path === "/" ? 1 : 0.7,
  }));
}
