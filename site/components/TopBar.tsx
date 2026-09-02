"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/site";

export function TopBar() {
  const pathname = usePathname();
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="wordmark">
          Entailment Labs <span className="qualifier">benchmarks</span>
        </Link>
        <nav aria-label="Site">
          <ul className="nav-links">
            {NAV.map((item) => {
              const current = pathname === item.href || pathname === `${item.href}/`;
              return (
                <li key={item.href}>
                  <Link href={item.href} aria-current={current ? "page" : undefined} data-current={current ? "true" : undefined}>
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
