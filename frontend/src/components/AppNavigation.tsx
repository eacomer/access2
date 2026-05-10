"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/patients", label: "Patients" },
  { href: "/audit-readiness", label: "Reviewer Queue" },
  { href: "/audit-bundle-verify", label: "Verify Bundle" },
  { href: "/demo-guide", label: "Demo Guide" },
  { href: "/demo/release-summary", label: "Release Summary" },
];

export default function AppNavigation() {
  const pathname = usePathname();

  if (pathname?.startsWith("/login")) {
    return null;
  }

  return (
    <header className="app-nav" aria-label="Primary navigation">
      <Link className="app-nav-brand" href="/patients">
        ACCESS2
      </Link>
      <nav className="app-nav-links">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          return (
            <Link
              aria-current={isActive ? "page" : undefined}
              className={isActive ? "app-nav-link app-nav-link--active" : "app-nav-link"}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
