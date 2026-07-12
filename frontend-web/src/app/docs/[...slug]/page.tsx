import { MDXRemote } from "next-mdx-remote/rsc";
import { notFound } from "next/navigation";
import { promises as fs } from "node:fs";
import path from "node:path";

// Placeholder MDX renderer. Production wires a content layer (e.g. Velite or
// Contentlayer) plus syntax highlighting via Shiki. We resolve markdown files
// from /content/docs at request time so the route still functions during
// scaffold review when no static content exists yet.
type Params = { slug: string[] };

async function loadMarkdown(slug: string[]): Promise<string | null> {
  const safe = slug.map((s) => s.replace(/[^a-zA-Z0-9_-]/g, ""));
  const filePath = path.join(process.cwd(), "content", "docs", ...safe.slice(0, -1), `${safe[safe.length - 1]}.mdx`);
  try {
    return await fs.readFile(filePath, "utf-8");
  } catch {
    return null;
  }
}

export default async function DocsSlugPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const source = await loadMarkdown(slug);
  if (!source) {
    return (
      <main className="prose prose-neutral mx-auto max-w-3xl px-6 py-16 dark:prose-invert">
        <h1>{slug.join(" / ")}</h1>
        <p className="text-muted-foreground">
          This page hasn&apos;t been written yet. Add{" "}
          <code>content/docs/{slug.join("/")}.mdx</code> to populate it.
        </p>
      </main>
    );
  }

  return (
    <main className="prose prose-neutral mx-auto max-w-3xl px-6 py-16 dark:prose-invert">
      <MDXRemote source={source} />
    </main>
  );
}

export async function generateStaticParams(): Promise<Params[]> {
  // Discover MDX files at build time when present.
  try {
    const root = path.join(process.cwd(), "content", "docs");
    const files = await fs.readdir(root, { recursive: true });
    return files
      .filter((f): f is string => typeof f === "string" && f.endsWith(".mdx"))
      .map((f) => ({ slug: f.replace(/\.mdx$/, "").split(path.sep) }));
  } catch {
    return [];
  }
}

// Defensive 404 helper used by other routes that may import this module.
export const dynamic = "force-static";
export const revalidate = 3600;
export { notFound };
