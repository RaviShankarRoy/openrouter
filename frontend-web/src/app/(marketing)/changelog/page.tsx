import type { Metadata } from "next";

import { formatDate } from "@/shared/lib/format";
import { Badge } from "@/shared/ui/badge";

export const metadata: Metadata = {
  title: "Changelog",
};

// Placeholder content; production builds source from MDX files in /content/changelog.
const entries = [
  {
    date: "2026-04-26",
    version: "0.1.0",
    tag: "scaffold",
    items: ["Initial monorepo scaffold", "Go gateway + Python backend stubs", "Next.js 15 dashboard"],
  },
];

export default function ChangelogPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="mb-8 text-3xl font-semibold tracking-tight">Changelog</h1>
      <div className="space-y-10">
        {entries.map((e) => (
          <article key={e.version} className="border-l-2 border-border pl-6">
            <header className="flex flex-wrap items-baseline gap-3">
              <h2 className="text-xl font-semibold">v{e.version}</h2>
              <Badge variant="outline">{e.tag}</Badge>
              <time dateTime={e.date} className="text-sm text-muted-foreground">
                {formatDate(e.date)}
              </time>
            </header>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {e.items.map((it) => (
                <li key={it}>{it}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </main>
  );
}
