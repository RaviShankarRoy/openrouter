import type { Metadata } from "next";

import { Chat } from "@/features/playground/chat/Chat";

export const metadata: Metadata = { title: "Playground" };

// FE-003 + FE-007: streaming playground with code snippet generator.
export default function PlaygroundPage() {
  return (
    <div className="space-y-4 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Playground</h1>
        <p className="text-sm text-muted-foreground">
          Test any model from the browser. Streaming output, copyable snippets.
        </p>
      </div>
      <Chat />
    </div>
  );
}
