import Link from "next/link";
import { Reading, Section } from "@/components/Section";
import { NAV } from "@/lib/site";

export default function NotFound() {
  return (
    <Section hero>
      <Reading>
        <h1 className="page-title">Not found</h1>
        <p className="body" style={{ marginTop: 24 }}>
          There is no page at this address.
        </p>
        <ul className="prose-list" style={{ marginTop: 24 }}>
          <li>
            <Link href="/">The four suites</Link>
          </li>
          {NAV.map((n) => (
            <li key={n.href}>
              <Link href={n.href}>{n.label}</Link>
            </li>
          ))}
        </ul>
      </Reading>
    </Section>
  );
}
