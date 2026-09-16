"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { label: "Setups", href: "/setups" },
  { label: "Experiments", href: "/experiments" },
  { label: "Analytics", href: "/analytics" },
] as const;

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="topbar">
      <Link className="brand" href="/" aria-label="Agent Studio home">
        <span className="brand-mark" aria-hidden="true">
          AS
        </span>
        <span>Agent Studio</span>
      </Link>
      <nav aria-label="Primary navigation">
        {navigation.map((item) => (
          <Link
            className={pathname.startsWith(item.href) ? "nav-link nav-link-active" : "nav-link"}
            href={item.href}
            key={item.href}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="environment" aria-label="Current environment">
        <span className="environment-dot" aria-hidden="true" />
        Local
      </div>
    </header>
  );
}
