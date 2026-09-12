import Link from "next/link";

import { ThemeToggle } from "@/api/components/theme/ThemeToggle";

const items = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/keys", label: "API keys" },
  { href: "/dashboard/usage", label: "Usage" },
  { href: "/dashboard/billing", label: "Billing" },
  { href: "/playground", label: "Playground" },
  { href: "/models", label: "Models" },
];

export function Sidebar() {
  return (
    <aside className="flex flex-col border-r bg-muted/30 px-4 py-6">
      <Link href="/" className="mb-6 px-2 text-base font-semibold">
        OpenRouter
      </Link>
      <nav className="flex flex-1 flex-col gap-1">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto pt-4">
        <ThemeToggle />
      </div>
    </aside>
  );
}
